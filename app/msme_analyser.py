import json
import re
import subprocess
import sys
import tempfile
from functools import lru_cache
from pathlib import Path

from app.config import (
    MSME_ANALYSER_FLAGS,
    MSME_ANALYSER_TIMEOUT,
    MSME_BUSINESS_TYPE,
    MSME_NATURE,
    MSME_PROFIT_MARGIN,
    MSME_SKILL_PATH,
)
from app.msme_workbook import validate_workbook

FENCE = re.compile(r"```python\n(.*?)\n```", re.S)
SCRIPT_NAME = "cam_income.py"
REPORT_NAME = "report.xlsx"
OUTPUT_NAME = "draft.json"


class AnalyserError(Exception):
    pass


class AnalyserTimeout(AnalyserError):
    pass


@lru_cache(maxsize=1)
def analyser_source() -> str:
    if not MSME_SKILL_PATH.is_file():
        raise AnalyserError("MSME skill file is missing.")
    match = FENCE.search(MSME_SKILL_PATH.read_text(encoding="utf-8"))
    if match is None:
        raise AnalyserError("MSME analyser script not found in the skill file.")
    return match.group(1)


def _command(report: Path, script: Path, output: Path) -> list[str]:
    return [
        sys.executable,
        *MSME_ANALYSER_FLAGS,
        str(script),
        str(report),
        "--type",
        MSME_BUSINESS_TYPE,
        "--nature",
        MSME_NATURE,
        "--profit",
        str(MSME_PROFIT_MARGIN),
        "--out",
        str(output),
    ]


def _run(report: Path, script: Path, output: Path) -> None:
    try:
        process = subprocess.run(
            _command(report, script, output),
            capture_output=True,
            text=True,
            timeout=MSME_ANALYSER_TIMEOUT,
        )
    except subprocess.TimeoutExpired as exc:
        raise AnalyserTimeout(
            "MSME analyser exceeded the execution time limit."
        ) from exc
    if process.returncode != 0:
        detail = (process.stderr or process.stdout or "").strip()[-500:]
        raise AnalyserError(f"MSME analyser failed: {detail}")


def analyse(data: bytes, filename: str = "") -> dict:
    validate_workbook(data)
    source = analyser_source()

    with tempfile.TemporaryDirectory(prefix="msme-") as tmp:
        root = Path(tmp)
        report = root / REPORT_NAME
        script = root / SCRIPT_NAME
        output = root / OUTPUT_NAME

        report.write_bytes(data)
        script.write_text(source, encoding="utf-8")
        _run(report, script, output)

        if not output.is_file():
            raise AnalyserError("MSME analyser produced no output.")
        try:
            draft = json.loads(output.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise AnalyserError("MSME analyser returned invalid JSON.") from exc

    if not isinstance(draft, dict):
        raise AnalyserError("MSME analyser output must be a JSON object.")
    if filename:
        draft.setdefault("inputs", {})["report_file"] = filename
    return draft

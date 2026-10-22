from datetime import date, datetime
from io import BytesIO
from typing import Any

from openpyxl import load_workbook

from app.config import MAX_TEXT_CHARS


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, float):
        return str(round(value, 4))
    return str(value).replace("\n", " ").strip()


def to_text(data: bytes) -> str:
    try:
        book = load_workbook(BytesIO(data), read_only=True, data_only=True)
    except Exception as exc:
        raise ValueError("Upload a valid .xlsx workbook.") from exc

    parts = []
    used = 0
    truncated = False
    try:
        for sheet in book.worksheets:
            header = f"\n### SHEET: {sheet.title} | rows={sheet.max_row} | columns={sheet.max_column}\n"
            if used + len(header) > MAX_TEXT_CHARS:
                truncated = True
                break
            parts.append(header)
            used += len(header)
            for row in sheet.iter_rows(values_only=True):
                values = [_cell(value) for value in row]
                if not any(values):
                    continue
                line = " | ".join(values) + "\n"
                if used + len(line) > MAX_TEXT_CHARS:
                    parts.append("\n[TRUNCATED: workbook text limit reached. Relevant rows may be missing.]\n")
                    truncated = True
                    break
                parts.append(line)
                used += len(line)
            if truncated:
                break
    finally:
        book.close()

    return "".join(parts)

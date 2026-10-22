from functools import lru_cache

from app.config import ROOT


@lru_cache(maxsize=1)
def system_prompt() -> str:
    prompt_path = ROOT / "prompts" / "salary_system_prompt.md"
    skill_path = ROOT / "skills" / "salary_extraction" / "SKILL.md"
    if not prompt_path.is_file() or not skill_path.is_file():
        raise RuntimeError("Salary prompt or skill file is missing.")
    return "\n\n".join((
        prompt_path.read_text(encoding="utf-8"),
        "--- APPROVED SALARY EXTRACTION SKILL ---",
        skill_path.read_text(encoding="utf-8"),
    ))

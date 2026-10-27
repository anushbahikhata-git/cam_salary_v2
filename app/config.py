import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
MAX_FILE_BYTES = int(os.getenv("MAX_FILE_BYTES", "15000000"))
MAX_TEXT_CHARS = int(os.getenv("MAX_WORKBOOK_TEXT_CHARS", "100000"))
TIMEOUT = float(os.getenv("LLM_TIMEOUT", "90"))

FRONTEND_ORIGINS = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", "*").split(",")
    if origin.strip()
]

MSME_SKILL_PATH = ROOT / "skills" / "msme_extraction" / "SKILL.md"
MSME_BUSINESS_TYPE = os.getenv("MSME_BUSINESS_TYPE", "services")
MSME_NATURE = os.getenv("MSME_NATURE", "")
MSME_PROFIT_MARGIN = float(os.getenv("MSME_PROFIT_MARGIN", "20"))
MSME_ANALYSER_TIMEOUT = float(os.getenv("MSME_ANALYSER_TIMEOUT", "120"))
MSME_ANALYSER_FLAGS = tuple(
    flag for flag in os.getenv("MSME_ANALYSER_FLAGS", "-I -W ignore").split() if flag
)

REASONING_EFFORT = os.getenv("LLM_REASONING_EFFORT", "off")

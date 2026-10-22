import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-flash")
MAX_FILE_BYTES = int(os.getenv("MAX_FILE_BYTES", "15000000"))
MAX_TEXT_CHARS = int(os.getenv("MAX_WORKBOOK_TEXT_CHARS", "100000"))
TIMEOUT = float(os.getenv("LLM_TIMEOUT", "90"))

from functools import lru_cache

from openai import OpenAI

from app.config import API_KEY, BASE_URL, TIMEOUT


@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    if not API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY is not configured.")
    return OpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
        timeout=TIMEOUT,
        max_retries=2,
    )

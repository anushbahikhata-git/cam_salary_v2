import json

from app.config import MODEL
from app.llm.client import get_client
from app.llm.prompts import system_prompt


def _parse(text: str) -> dict:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Model returned invalid JSON.") from exc
    if not isinstance(data, dict):
        raise ValueError("Model response must be a JSON object.")
    return data


def extract(workbook_text: str) -> dict:
    response = get_client().chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt()},
            {
                "role": "user",
                "content": (
                    "Analyze this CAM workbook using the system instructions. "
                    "Use only workbook evidence and return the exact JSON contract.\n\n"
                    "<CAM_WORKBOOK>\n"
                    f"{workbook_text}\n"
                    "</CAM_WORKBOOK>"
                ),
            },
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    content = response.choices[0].message.content
    if not content:
        raise ValueError("Model returned an empty response.")
    return _parse(content)

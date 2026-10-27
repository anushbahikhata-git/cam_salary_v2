import json

from app.config import MODEL, REASONING_EFFORT
from app.llm.client import get_client
from app.llm.prompts import msme_system_prompt

INSTRUCTION = (
    "The analyser output below has already computed the evidence for this CAM report. "
    "Return the exact JSON contract from the approved skill, copying every numeric value "
    "verbatim from that output. Read the profit margin from inputs.profit_margin_pct and the "
    "income from income_computation.yearly_income_at_profit_margin: never apply the skill's "
    "default margin table, never recompute turnover, and never round, rescale, or invent a figure. "
    "Apply the skill's review, cashflow-match and irregularity rules to the evidence supplied, "
    "and keep notes to six short points. "
    "Use only the supplied evidence. Return one JSON object only, with no Markdown or commentary."
)


def _parse(text: str) -> dict:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Model returned invalid JSON.") from exc

    if not isinstance(data, dict):
        raise ValueError("Model response must be a JSON object.")

    return data


def extract(draft: dict) -> dict:
    request: dict = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": msme_system_prompt()},
            {
                "role": "user",
                "content": (
                    f"{INSTRUCTION}\n\n"
                    "<ANALYSER_OUTPUT>\n"
                    f"{json.dumps(draft, ensure_ascii=False)}\n"
                    "</ANALYSER_OUTPUT>"
                ),
            },
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1,
    }

    if REASONING_EFFORT:
        request["reasoning_effort"] = REASONING_EFFORT

    response = get_client().chat.completions.create(**request)

    if not response.choices:
        raise ValueError("Model returned no choices.")

    content = response.choices[0].message.content

    if not content:
        raise ValueError("Model returned an empty response.")

    return _parse(content)

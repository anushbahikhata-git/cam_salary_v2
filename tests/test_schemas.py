import pytest
from pydantic import ValidationError

from app.schemas import FailureResult, Result


def salary_result():
    return {
        "success": True,
        "request_type": "cam_only",
        "agent": {"detected": True, "reason": "Recurring monthly salary credits found."},
        "Income": {
            "type": "salary",
            "company": "Example Ltd",
            "confidence_score": 100,
            "Payouts": [
                ["2026-01-05", 25000, "NEFT"],
                ["2026-02-05", 25200, "NEFT"],
                ["2026-03-06", 24900, "NEFT"],
            ],
        },
        "monthly_average_balance": None,
    }


def test_valid_salary_result():
    result = Result.model_validate(salary_result())
    assert result.agent.detected is True
    assert result.model_dump(mode="json")["Income"]["Payouts"][0][0] == "2026-01-05"


def test_negative_result_has_null_income():
    payload = {
        "success": True,
        "request_type": "cam_only",
        "agent": {"detected": False, "reason": "No candidate passed the salary gates."},
        "Income": None,
        "monthly_average_balance": None,
    }
    assert Result.model_validate(payload).Income is None


def test_failure_result_matches_skill_contract():
    result = FailureResult.model_validate(
        {"success": False, "error": "Transaction date/Credit column not found"}
    )
    assert result.model_dump(mode="json") == {
        "success": False,
        "error": "Transaction date/Credit column not found",
    }


@pytest.mark.parametrize(
    "change",
    [
        lambda data: data.update({"Income": None}),
        lambda data: data["Income"].update({"confidence_score": 89}),
        lambda data: data["Income"].update({"confidence_score": 93}),
        lambda data: data["Income"].update({"Payouts": [["2026-01-05", 25000, "NEFT"]]}),
        lambda data: data["Income"].update(
            {
                "Payouts": [
                    ["2026-01-05", 25000, "NEFT"],
                    ["2026-02-05", 25200, "UPI"],
                    ["2026-03-06", 24900, "NEFT"],
                ]
            }
        ),
    ],
)
def test_invalid_salary_result_is_rejected(change):
    payload = salary_result()
    change(payload)
    with pytest.raises(ValidationError):
        Result.model_validate(payload)


def test_unexpected_fields_are_rejected():
    payload = salary_result()
    payload["unexpected"] = True
    with pytest.raises(ValidationError):
        Result.model_validate(payload)


def test_skill_confidence_formula_is_accepted():
    payload = salary_result()
    payload["Income"]["Payouts"] = [
        ["2026-01-05", 17900, "NEFT"],
        ["2026-02-05", 20000, "NEFT"],
        ["2026-03-06", 20050, "NEFT"],
        ["2026-04-05", 18400, "NEFT"],
        ["2026-05-05", 20600, "NEFT"],
    ]
    payload["Income"]["confidence_score"] = 93
    assert Result.model_validate(payload).Income.confidence_score == 93

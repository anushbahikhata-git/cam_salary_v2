import pytest
from pydantic import ValidationError

from app.schemas import Result


def test_valid_salary_result():
    result = Result.model_validate({
        "success": True,
        "request_type": "cam_only",
        "agent": {"detected": True, "reason": "Recurring salary credits found."},
        "Income": {
            "type": "salary",
            "company": "Example Ltd",
            "confidence_score": 90,
            "Payouts": [["2026-01-05", 25000, "NEFT"]],
        },
        "monthly_average_balance": None,
    })
    assert result.agent.detected is True
    assert result.model_dump(mode="json")["Income"]["Payouts"][0][0] == "2026-01-05"


def test_negative_result_has_null_income():
    result = Result.model_validate({
        "success": True,
        "request_type": "cam_only",
        "agent": {"detected": False, "reason": "No candidate passed the salary gates."},
        "Income": None,
        "monthly_average_balance": None,
    })
    assert result.Income is None


def test_detected_salary_requires_income():
    with pytest.raises(ValidationError):
        Result.model_validate({
            "success": True,
            "request_type": "cam_only",
            "agent": {"detected": True, "reason": "Salary found."},
            "Income": None,
        })

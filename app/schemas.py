from datetime import date
from statistics import median
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Agent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detected: bool
    reason: str = Field(min_length=1)


class IncomeInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["salary"] = "salary"
    company: str | None = None
    confidence_score: float = Field(ge=90, le=100)
    Payouts: list[tuple[date, float, str]] = Field(min_length=3)

    @model_validator(mode="after")
    def validate_payouts(self):
        payouts = self.Payouts
        dates = [payout[0] for payout in payouts]
        amounts = [payout[1] for payout in payouts]
        modes = [payout[2].strip().upper() for payout in payouts]

        if dates != sorted(dates):
            raise ValueError("Payouts must be ordered by date.")
        gaps = [(later - earlier).days for earlier, later in zip(dates, dates[1:])]
        if any(gap < 25 or gap > 40 for gap in gaps):
            raise ValueError("Payout gaps must be between 25 and 40 days.")
        if any(amount < 3000 for amount in amounts):
            raise ValueError("Salary payouts must be at least 3000.")
        if any(not mode for mode in modes):
            raise ValueError("Every payout must include a payment mode.")
        if any(any(term in mode for term in ("UPI", "ATM", "CASH")) for mode in modes):
            raise ValueError("UPI, ATM, and cash payouts are not eligible salary evidence.")

        center = median(amounts)
        deviations = [abs(amount - center) / center for amount in amounts] if center > 0 else []
        if center <= 0 or any(deviation > 0.2 for deviation in deviations):
            raise ValueError("Payout amounts exceed the allowed stability tolerance.")

        high_deviations = sum(value > 0.1 for value in deviations)
        medium_deviations = sum(0.05 < value <= 0.1 for value in deviations)
        score = max(0, min(100, 100 - 5 * high_deviations - 2 * medium_deviations))
        if round(score, 1) != round(self.confidence_score, 1):
            raise ValueError("Confidence score does not match the payout evidence.")
        return self


class Result(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: Literal[True]
    request_type: Literal["cam_only"]
    agent: Agent
    Income: IncomeInfo | None = None
    monthly_average_balance: float | None = None

    @model_validator(mode="after")
    def check_income(self):
        if self.agent.detected != (self.Income is not None):
            raise ValueError("Income must be present only when salary is detected.")
        return self


class FailureResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: Literal[False]
    error: str = Field(min_length=1)

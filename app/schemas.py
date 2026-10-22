from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Agent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detected: bool
    reason: str


class IncomeInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["salary"] = "salary"
    company: str | None = None
    confidence_score: float = Field(ge=0, le=100)
    Payouts: list[tuple[date, float, str]]


class Result(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: bool
    request_type: Literal["cam_only"]
    agent: Agent
    Income: IncomeInfo | None = None
    monthly_average_balance: float | None = None

    @model_validator(mode="after")
    def check_income(self):
        if not self.success:
            raise ValueError("success must be true when analysis completes")
        if self.agent.detected != (self.Income is not None):
            raise ValueError("Income must be present only when salary is detected")
        return self

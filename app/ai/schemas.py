from pydantic import BaseModel, field_validator
from typing import Literal


class FindingSchema(BaseModel):
    title: str
    description: str
    severity: Literal["high", "medium", "low"]
    estimated_hours_month: str
    recommended_tool: str
    category: str


class AnalysisResult(BaseModel):
    score: int
    score_label: str
    summary: str
    findings: list[FindingSchema]
    quick_win: str

    @field_validator("score")
    @classmethod
    def score_in_range(cls, v: int) -> int:
        return max(0, min(100, v))

    @field_validator("findings")
    @classmethod
    def findings_count(cls, v: list) -> list:
        return v[:6]

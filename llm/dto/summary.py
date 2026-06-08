from pydantic import BaseModel, Field


class Summary(BaseModel):
    """Summary model."""

    district: str
    problem_count: int = Field(..., alias="problemCount")
    top_issues: str = Field(..., alias="topIssues")
    summary: str

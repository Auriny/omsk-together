from pydantic import BaseModel


class Incident(BaseModel):
    """Incident model."""

    id: int
    district: str
    text: str

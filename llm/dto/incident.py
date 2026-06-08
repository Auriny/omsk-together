from pydantic import BaseModel


class Incident(BaseModel):
    """Incident model."""

    district: str
    topic: str
    text: str

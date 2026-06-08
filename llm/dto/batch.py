from pydantic import BaseModel, Field

from dto.incident import Incident  # noqa: TC001


class Batch(BaseModel):
    """Batch model."""

    is_last_batch: bool = Field(..., alias="isLastBatch")
    items: list[Incident | None]

from typing import TYPE_CHECKING

from dto import AreaProblem
from models.classifier import MDeBERTa

if TYPE_CHECKING:
    from dto import Batch

class MDeBERTaClassifier:
    """Pipeline classifier-interface implementation."""

    _model: MDeBERTa = None

    def __init__(self) -> None:
        self._model = MDeBERTa.get_instance()

    async def classify(self, items: Batch) -> dict[str, AreaProblem]:
        result = await self._model.filter([i.text for i in items.items])
        return {
            item.district: AreaProblem(
                topic=item.topic,
                problem=item.text
            )
            for item, label in zip(items.items, result, strict=False)
            if label == "проблема"
        }


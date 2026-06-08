import logging
from typing import TYPE_CHECKING

from dto import AreaProblem
from models.classifier import MDeBERTa

if TYPE_CHECKING:
    from dto import Batch


logger = logging.getLogger(__name__)
class MDeBERTaClassifier:
    """Pipeline classifier-interface implementation."""

    _model: MDeBERTa = None

    def __init__(self) -> None:
        self._model = MDeBERTa.get_instance()

    async def classify(self, items: "Batch") -> list[AreaProblem]:
        logging.info("Start to classify by mDeBERTa pipeline")
        result = await self._model.filter([i.text for i in items.items])
        return [
            AreaProblem(
                district=item.district,
                topic=item.topic,
                problem=item.text
            )
            for item, label in zip(items.items, result, strict=False)
            if label == "проблема"
        ]


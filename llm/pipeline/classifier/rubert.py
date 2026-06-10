import logging
from typing import TYPE_CHECKING

from enums import LabelsEnum
from models.classifier import RuBERT

if TYPE_CHECKING:
    from dto import Batch


logger = logging.getLogger(__name__)


class RuBERTClassifier:
    """Pipeline classifier-interface implementation."""

    _model: RuBERT = None

    def __init__(self) -> None:
        self._model = RuBERT.get_instance()

    async def classify(self, items: "Batch") -> list[dict[str, str | int]]:
        logger.info("Start to classify by mDeBERTa pipeline")
        result = await self._model.filter([i.text for i in items.items])
        return [
            {
                "district": item.district,
                "topic": item.topic,
                "difficult": label,
                "problem": item.text
            }
            for item, label in zip(items.items, result, strict=False)
            if label != LabelsEnum.NOT_PROBLEM
        ]

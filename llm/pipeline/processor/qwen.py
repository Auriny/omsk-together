import logging

from dto import AreaProblems, Summary
from models.processor import Qwen


logger = logging.getLogger(__name__)
class QwenProcessor:
    """Pipeline processor-interface implementation."""

    _model: Qwen = None

    def __init__(self) -> None:
        self._model = Qwen.get_instance()

    async def process(
        self, items: list[tuple[str, AreaProblems]]
    ) -> list[Summary]:
        logger.info("Start to process by QwenProcessor")
        result = []
        for i in items:
            logger.debug("Trying to get summary")
            summary = await self._model.summarize(i[1].problems[:25])
            result.append(Summary(
                district=i[0],
                problemCount=i[1].problem_count,
                topIssues=", ".join(i[1].topics[:3]),
                summary=summary
            ))
        return result

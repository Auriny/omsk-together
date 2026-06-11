import logging
from asyncio import Future, Queue, get_event_loop, to_thread
from typing import ClassVar

import torch
from transformers import TextClassificationPipeline, pipeline

from enums import LabelsEnum
from settings import Settings

logger = logging.getLogger(__name__)

type PipelineOut = list[dict[str, str | float]]


class RuBERT:
    """RuBERT classifier-interface implementation."""

    _model: ClassVar[TextClassificationPipeline] = None
    _labels = LabelsEnum
    _instance: ClassVar["RuBERT"] = None
    _queue: Queue[tuple[list[str], Future[PipelineOut]]]

    def __init__(self) -> None:
        self._queue = Queue()
        self._init_model()

    @classmethod
    def _init_model(cls) -> None:
        if cls._model is None:
            logger.info("Initializing RuBERT model with optimizations")
            cls._model = pipeline(
                "text-classification",
                model=Settings.get().RUBERT_PATH,
                tokenizer=Settings.get().RUBERT_PATH,
                device=0,
                dtype=torch.float16
            )

    @classmethod
    def get_instance(cls) -> "RuBERT":
        logger.debug("Getting RuBERT instance")
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def run_inference_loop(self) -> None:
        while True:
            logger.info("Trying to get future from queue")
            batch: list[str] = []
            futures: list[tuple[int, Future]] = []
            items, future = await self._queue.get()
            logger.debug("Item and future were gotten")
            batch.extend(items)
            futures.append((len(items), future))
            while not self._queue.empty():
                items, future = self._queue.get_nowait()
                batch.extend(items)
                futures.append((len(items), future))
            msg = f"Count of tasks: {len(futures)}"
            logger.info(msg)
            try:
                logger.info("Starting mDeBERTa model by asyncio.to_thread()")
                with torch.no_grad():
                    result: PipelineOut = await to_thread(
                        lambda: self._model(batch, batch_size=16)  # noqa: B023
                    )
                idx = 0
                for size, future in futures:
                    logger.debug("Set result to future")
                    future.set_result(result[idx : idx + size])
                    idx += size
            except Exception as e:
                msg = f"!!! ERROR:\n{e}"
                logger.exception(msg)
                for _, future in futures:
                    future.set_exception(e)

    async def filter(self, items: list[str]) -> list[int]:
        logger.info("Start filtering by mDeBERTa")
        future: Future[PipelineOut] = get_event_loop().create_future()
        await self._queue.put((items, future))
        logger.debug("Await future")
        output = await future
        return [int(i["label"].replace("LABEL_", "")) for i in output]

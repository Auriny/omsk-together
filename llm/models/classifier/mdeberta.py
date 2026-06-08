import logging
from asyncio import Future, Queue, get_event_loop, to_thread
from typing import ClassVar

import torch
from transformers import ZeroShotClassificationPipeline, pipeline

from settings import Settings

logger = logging.getLogger(__name__)

type PipelineOut = list[dict[str, str | list[str] | list[float]]]

class MDeBERTa:
    """mDeBERTa classifier-interface implementation."""

    _model: ClassVar[ZeroShotClassificationPipeline] = pipeline(
            "zero-shot-classification",
            model=Settings.get().MDEBERTA_PATH,
            device=0
        )
    _labels = ("проблема", "не проблема")
    _instance: ClassVar["MDeBERTa"] = None
    _queue: Queue[tuple[
        list[str],
        Future[PipelineOut]
    ]]

    def __init__(self) -> None:
        self._queue = Queue()

    @classmethod
    def get_instance(cls) -> "MDeBERTa":
        logger.debug("Getting mDeBERTa instance")
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def run_inference_loop(self) -> None:
        while True:
            logger.debug("Trying to get future from queue")
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
            logger.debug(f"Count of tasks: {len(futures)}")
            try:
                logger.debug("Starting mDeBERTa model by asyncio.to_thread()")
                # result = self._model(batch, self._labels, multi_label=False, batch_size=16)
                result: PipelineOut = await to_thread(
                    lambda: self._model(batch, self._labels, multi_label=False, batch_size=16) # noqa:B023
                )
                idx = 0
                for size, future in futures:
                    logger.debug(f"Set result to future: {future}")
                    future.set_result(result[idx:idx+size])
                    idx += size
            except Exception as e: # noqa: BLE001
                logger.debug(f"ERROR: {e}")
                for _, future in futures:
                    future.set_exception(e)

    async def filter(self, items: list[str]) -> list[str]:
        logger.debug("Start filtering by mDeBERTa")
        future: Future[PipelineOut] = get_event_loop().create_future()
        await self._queue.put((items, future))
        logger.debug("Await future")
        output = await future
        return [i["labels"][0] for i in output]

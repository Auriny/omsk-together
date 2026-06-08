from asyncio import Future, Queue, get_event_loop, to_thread
from typing import ClassVar

import torch
from transformers import ZeroShotClassificationPipeline, pipeline

from settings import Settings

type PipelineOut = list[dict[str, str | list[str] | list[float]]]

class MDeBERTa:
    """mDeBERTa classifier-interface implementation."""

    _model: ClassVar[ZeroShotClassificationPipeline] = pipeline(
            "zero-shot-classification",
            model=Settings.get().MDEBERTA_PATH,
            device="cuda" if torch.cuda.is_available() else "cpu"
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
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def run_inference_loop(self) -> None:
        while True:
            batch: list[str] = []
            futures: list[tuple[int, Future]] = []
            items, future = await self._queue.get()
            batch.extend(items)
            futures.append((len(items), future))
            while not self._queue.empty():
                items, future = self._queue.get_nowait()
                batch.extend(items)
                futures.append((len(items), future))
            try:
                result: PipelineOut = await to_thread(
                    lambda: self._model(batch, self._labels, multi_label=False) # noqa:B023
                )
                idx = 0
                for size, future in futures:
                    future.set_result(result[idx:idx+size])
                    idx += size
            except Exception as e: # noqa: BLE001
                for _, future in futures:
                    future.set_exception(e)

    async def filter(self, items: list[str]) -> list[str]:
        future: Future[PipelineOut] = get_event_loop().create_future()
        await self._queue.put((items, future))
        output = await future
        return [i["labels"][0] for i in output]

import asyncio
import logging
from collections import defaultdict
from typing import TYPE_CHECKING, cast

import torch

from dto import AreaProblems
from models.classifier import MDeBERTa
from pipeline.classifier import MDeBERTaClassifier
from pipeline.processor import QwenProcessor
from queue_client.redis import RedisQueue

if TYPE_CHECKING:
    from dto import AreaProblem, Batch, Summary
    from pipeline.classifier import ClassifierPipelineInterface
    from pipeline.processor import ProcessorPipelineInterface
    from queue_client.interface import QueueInterface

logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger()

N_WORKERS = 1

async def worker(  # noqa: PLR0913
    queue: "QueueInterface[Batch, list[Summary]]",
    classifier_pipe: "ClassifierPipelineInterface[Batch, list[AreaProblem]]",  # noqa: E501
    processor_pipe: "ProcessorPipelineInterface[list[tuple[str, AreaProblems]], list[Summary]]",  # noqa: E501
    storage: dict[str, AreaProblems],
    barrier: asyncio.Barrier,
    done_flag: asyncio.Event,
) -> None:
    while True:
        data = await queue.pop()
        if not data.is_last_batch:
            classified = await classifier_pipe.classify(data)
            for item in classified:
                if item.district not in storage:
                    storage[item.district] = AreaProblems()
                storage[item.district].problem_count += 1
                if item.topic not in storage[item.district].topics:
                    storage[item.district].topics.append(item.topic)
                storage[item.district].problems.append(item.problem)
        else:
            await barrier.wait()
            if not done_flag.is_set():
                done_flag.set()
                sorted_data_list = sorted(
                    storage.items(),
                    key=lambda x: x[1].problem_count,
                    reverse=True
                )[:10]
                summary_list = await processor_pipe.process(sorted_data_list)
                await queue.push(summary_list)



async def main() -> None:
    logger.debug(f"Device in use: {"cuda" if torch.cuda.is_available() else "cpu"}")
    barrier = asyncio.Barrier(N_WORKERS)
    storage: dict[str, AreaProblems] = defaultdict()
    done_flag = asyncio.Event()
    inference_loop = asyncio.create_task(
        MDeBERTa.get_instance().run_inference_loop()
    )
    workers = [
        worker(
            RedisQueue(),
            MDeBERTaClassifier(),
            QwenProcessor(),
            storage,
            barrier,
            done_flag
        )
        for _ in range(N_WORKERS)
    ]
    await asyncio.gather(
        inference_loop, *workers,
        return_exceptions=True
    )

if __name__ == "__main__":
    asyncio.run(main())

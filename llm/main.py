import asyncio
import logging
from collections import defaultdict
from typing import TYPE_CHECKING

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

N_WORKERS = 20

async def worker(  # noqa: PLR0913
    queue: "QueueInterface[Batch, list[Summary]]",
    classifier_pipe: "ClassifierPipelineInterface[Batch, list[AreaProblem]]",
    processor_pipe: "ProcessorPipelineInterface[list[tuple[str, AreaProblems]], list[Summary]]",  # noqa: E501
    storage: dict[str, AreaProblems],
    condition: asyncio.Condition,
    active_tasks: list[int]
) -> None:
    while True:
        data = await queue.pop()
        msg = f"Is last batch: {data.is_last_batch}"
        logger.debug(msg)
        if not data.is_last_batch:
            async with condition:
                active_tasks[0] += 1
            logger.debug("Trying to classify")
            try:
                classified = await classifier_pipe.classify(data)
                for item in classified:
                    if item.district not in storage:
                        storage[item.district] = AreaProblems()
                    storage[item.district].problem_count += 1
                    if item.topic not in storage[item.district].topics:
                        storage[item.district].topics.append(item.topic)
                    storage[item.district].problems.append(item.problem)
            finally:
                async with condition:
                    active_tasks[0] -= 1
                    condition.notify_all()
        else:
            logger.debug("Last batch was received")
            async with condition:
                await condition.wait_for(lambda: active_tasks[0] == 0)
            sorted_data_list = sorted(
                storage.items(),
                key=lambda x: x[1].problem_count,
                reverse=True
            )[:10]
            storage.clear()
            summary_list = await processor_pipe.process(sorted_data_list)
            await queue.push(summary_list)



async def main() -> None:
    condition = asyncio.Condition()
    storage: dict[str, AreaProblems] = defaultdict()
    active_tasks = [0]
    inference_loop = asyncio.create_task(
        MDeBERTa.get_instance().run_inference_loop()
    )
    workers = [
        worker(
            RedisQueue(),
            MDeBERTaClassifier(),
            QwenProcessor(),
            storage,
            condition,
            active_tasks
        )
        for _ in range(N_WORKERS)
    ]
    await asyncio.gather(
        inference_loop, *workers
    )

if __name__ == "__main__":
    asyncio.run(main())

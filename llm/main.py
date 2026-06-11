import asyncio
import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from dto import AreaProblems, Topic
from models.classifier import RuBERT
from pipeline.classifier import RuBERTClassifier
from pipeline.processor import QwenProcessor
from queue_client.redis import RedisQueue

if TYPE_CHECKING:
    from dto import Batch, Summary
    from pipeline.classifier import ClassifierPipelineInterface
    from pipeline.processor import ProcessorPipelineInterface
    from queue_client.interface import QueueInterface

logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger()

N_WORKERS = 10

async def worker(  # noqa: PLR0913
    queue: "QueueInterface[Batch, list[Summary], str]",
    classifier_pipe: "ClassifierPipelineInterface[Batch, list[dict[str, str | int]]]",  # noqa: E501
    processor_pipe: "ProcessorPipelineInterface[list[tuple[str, AreaProblems]], list[Summary], str]",  # noqa: E501
    storage: dict[str, AreaProblems],
    condition: asyncio.Condition,
    active_tasks: list[int],
    tasks_complited: list[int],
) -> None:
    while True:
        data = await queue.pop()
        msg = (
            f"Is last batch: {data.is_last_batch}\n"
            f"Tasks Complited: {tasks_complited[0]}"
        )
        logger.info(msg)
        if not data.is_last_batch:
            async with condition:
                active_tasks[0] += 1
            logger.debug("Trying to classify")
            try:
                classified = await classifier_pipe.classify(data)
                for item in classified:
                    if item["district"] not in storage:
                        storage[item["district"]] = AreaProblems()
                    storage[item["district"]].problem_count += 1
                    if (
                        item["topic"]
                        not in storage[item["district"]].problems
                    ):
                        storage[item["district"]] \
                            .problems[item["topic"]] = Topic()
                    if (
                        item["difficult"]
                        not in storage[item["district"]] \
                            .problems[item["topic"]] \
                                .problems
                    ):
                        storage[item["district"]] \
                            .problems[item["topic"]] \
                                .problems[item["difficult"]] = []
                    storage[item["district"]] \
                        .problems[item["topic"]].count += 1
                    storage[item["district"]] \
                        .problems[item["topic"]] \
                            .problems[item["difficult"]] \
                                .append(item["problem"])
            finally:
                async with condition:
                    active_tasks[0] -= 1
                    tasks_complited[0] += 1
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
            summary_of_summary = await processor_pipe.summarize_by_summary(
                summary_list
            )
            await queue.push(summary_list)
            await queue.summary_push(summary_of_summary)
            tasks_complited[0] = 0



async def main() -> None:
    condition = asyncio.Condition()
    storage: dict[str, AreaProblems] = defaultdict()
    active_tasks = [0]
    tasks_complited = [0]
    inference_loop = asyncio.create_task(
        RuBERT.get_instance().run_inference_loop()
    )
    workers = [
        worker(
            RedisQueue(),
            RuBERTClassifier(),
            QwenProcessor(),
            storage,
            condition,
            active_tasks,
            tasks_complited
        )
        for _ in range(N_WORKERS)
    ]
    await asyncio.gather(
        inference_loop, *workers
    )

if __name__ == "__main__":
    asyncio.run(main())

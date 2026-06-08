import asyncio
from collections import defaultdict
from typing import TYPE_CHECKING, cast

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


N_WORKERS = 10

async def worker(  # noqa: PLR0913
    queue: QueueInterface[Batch, list[Summary]],
    classifier_pipe: ClassifierPipelineInterface[
        Batch, dict[str, AreaProblem]
    ],
    processor_pipe: ProcessorPipelineInterface[
        list[tuple[str, AreaProblems]], list[Summary]
    ],
    storage: dict[str, AreaProblems],
    barrier: asyncio.Barrier,
    done_flag: asyncio.Event,
) -> None:
    while True:
        data = await queue.pop()
        if not data.is_last_batch:
            classified = cast(
                "dict[str, AreaProblem]",
                await classifier_pipe.classify(data)
            )
            for item_dist, item in classified.items():
                if item_dist not in storage:
                    storage[item_dist] = AreaProblems()
                storage[item_dist].problem_count += 1
                if item.topic not in storage[item_dist].topics:
                    storage[item_dist].topics.append(item.topic)
                storage[item_dist].problems.append(item.problem)
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
    barrier = asyncio.Barrier(N_WORKERS)
    storage: dict[str, AreaProblems] = defaultdict()
    done_flag = asyncio.Event()
    asyncio.gather(
        MDeBERTa.get_instance().run_inference_loop(),
        *[
            asyncio.create_task(
                worker(
                    RedisQueue(),
                    MDeBERTaClassifier(),
                    QwenProcessor(),
                    storage,
                    barrier,
                    done_flag
                )
            )
            for _ in range(N_WORKERS)
        ]
    )

if __name__ == "__main__":
    asyncio.run(main())

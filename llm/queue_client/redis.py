from typing import TYPE_CHECKING

from redis.asyncio import Redis

from dto import Batch
from settings import Settings

if TYPE_CHECKING:
    from dto import Summary


class RedisQueue:
    """Redis implementation of the QueueInterface."""

    async def push(self, items: list[Summary]) -> None:
        async with Redis(
            host=Settings.get().REDIS_HOST,
            port=Settings.get().REDIS_PORT
        ) as redis:
            await redis.lpush(
                "queue:analyze:results",
                f"{[i.json(by_alias=True) for i in items]}"
            )

    async def pop(self) -> Batch:
        async with Redis(
            host=Settings.get().REDIS_HOST,
            port=Settings.get().REDIS_PORT
        ) as redis:
            item = await redis.brpop("queue:analyze:tasks")
            return Batch.parse_raw(item[1])

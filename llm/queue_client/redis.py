import json
from typing import TYPE_CHECKING

from redis.asyncio import Redis

from dto.batch import Batch
from settings import Settings

if TYPE_CHECKING:

    from dto.summary import Summary

class RedisQueue:
    """Redis implementation of the QueueInterface."""

    async def push(self, items: "list[Summary]") -> None:
        async with Redis(
            host=Settings.get().REDIS_HOST,
            port=Settings.get().REDIS_PORT
        ) as redis:
            payload = json.dumps([i.dict(by_alias=True) for i in items])
            await redis.lpush("queue:analyze:results", payload)

    async def pop(self) -> Batch:
        async with Redis(
            host=Settings.get().REDIS_HOST,
            port=Settings.get().REDIS_PORT
        ) as redis:
            while True:
                item = await redis.brpop(
                    "queue:analyze:tasks",
                    timeout=30
                )
                if item is not None:
                    return Batch.parse_raw(item[1])

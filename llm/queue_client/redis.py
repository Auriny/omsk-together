import json
from typing import TYPE_CHECKING
from redis.asyncio import Redis

from dto.batch import Batch
from settings import Settings

if TYPE_CHECKING:
    from dto.summary import Summary

class RedisQueue:
    """Redis implementation of the QueueInterface."""

    def __init__(self):
        self.redis = Redis(
            host=Settings.get().REDIS_HOST,
            port=Settings.get().REDIS_PORT,
            health_check_interval=30,
            decode_responses=True
        )

    async def push(self, items: list['Summary']) -> None:
        payload = json.dumps([i.dict(by_alias=True) for i in items])
        await self.redis.lpush("queue:analyze:results", payload)

    async def pop(self) -> Batch:
            while True:
                item = await self.redis.brpop("queue:analyze:tasks", timeout=30)
                if item is not None:
                    return Batch.parse_raw(item[1])
    
    async def close(self):
        await self.redis.aclose()

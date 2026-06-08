import json
import logging
from typing import TYPE_CHECKING

from redis.asyncio import Redis

from dto.batch import Batch
from settings import Settings

if TYPE_CHECKING:
    from dto.summary import Summary


logger = logging.getLogger(__name__)
class RedisQueue:
    """Redis implementation of the QueueInterface."""

    _redis: Redis = None

    def __init__(self) -> None:
        self._redis = Redis(
            host=Settings.get().REDIS_HOST,
            port=Settings.get().REDIS_PORT,
            health_check_interval=30,
            decode_responses=True
        )

    async def push(self, items: "list[Summary]") -> None:
            payload = json.dumps([i.dict(by_alias=True) for i in items])
            await self._redis.lpush("queue:analyze:results", payload)

    async def pop(self) -> Batch:
            while True:
                logger.debug("Redis client try to get batch by brpop")
                item = await self._redis.brpop(
                    "queue:analyze:tasks",
                    timeout=30
                )
                logger.debug("Looks like redis client get some entitie. Trying to validate")
                if item is not None:
                    return Batch.model_validate_json(item[1])

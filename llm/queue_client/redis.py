import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import TYPE_CHECKING, TypeVar

from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from dto.batch import Batch
from settings import Settings

if TYPE_CHECKING:
    from dto.summary import Summary

logger = logging.getLogger(__name__)

T = TypeVar("T")

_RETRY_DELAYS = [1, 2, 5, 10, 30, 60]


class RedisQueue:
    """Redis implementation of the QueueInterface."""

    _redis: Redis = None

    def __init__(self) -> None:
        self._redis = self._make_client()

    def _make_client(self) -> Redis:
        return Redis(
            host=Settings.get().REDIS_HOST,
            port=Settings.get().REDIS_PORT,
            health_check_interval=30,
            decode_responses=True,
            socket_keepalive=True,
            socket_timeout=60,
            retry_on_timeout=True,
        )

    async def _reconnect(self) -> None:
        """Retry reconnection indefinitely with exponential-ish backoff."""
        attempt = 0
        while True:
            delay = _RETRY_DELAYS[min(attempt, len(_RETRY_DELAYS) - 1)]
            logger.info(
                "Reconnect attempt %d, waiting %ds...", attempt + 1, delay
            )
            await asyncio.sleep(delay)
            with suppress(Exception):
                await self._redis.aclose()
            try:
                self._redis = self._make_client()
                await self._redis.ping()
            except Exception:
                logger.exception(
                    "Reconnect attempt %d failed: ", attempt + 1
                )
                attempt += 1
            else:
                logger.info("Reconnected to Redis successfully")
                return

    async def _execute_with_retry(
        self,
        coro_fn: Callable[..., Awaitable[T]],
        *args: any,
        **kwargs: any
    ) -> Awaitable[None, None, T]:
        """Execute an async Redis operation, reconnecting on connection errors.""" # noqa: E501
        while True:
            try:
                return await coro_fn(*args, **kwargs)
            except (RedisConnectionError, RedisTimeoutError):
                logger.exception(
                    "Redis connection error during operation: "
                )
                await self._reconnect()

    async def push(self, items: "list[Summary]") -> None:
        logger.info("Pushing summaries to Redis")
        payload = json.dumps([i.dict(by_alias=True) for i in items])
        await self._execute_with_retry(
            self._redis.lpush, "queue:analyze:results", payload
        )

    async def summary_push(self, item: str) -> None:
        logger.info("Pushing summary-of-summary to Redis")
        await self._execute_with_retry(
            self._redis.lpush, "queue:analyze:summary", json.dumps(item)
        )

    async def pop(self) -> Batch:
        while True:
            result = await self._execute_with_retry(
                self._redis.brpop, "queue:analyze:tasks", timeout=30
            )
            if result is not None:
                logger.debug("Received item from Redis, validating...")
                return Batch.model_validate_json(result[1])
            logger.debug("brpop timed out (empty queue), polling again...")

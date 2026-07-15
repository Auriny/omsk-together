import json, pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dto.summary import Summary
from dto.batch import Batch
from dto.incident import Incident
from queue_client.redis import RedisQueue
from redis.exceptions import ConnectionError as RedisConnectionError
from settings import Settings


@pytest.mark.asyncio
async def test_push_serializes_summaries_and_calls_lpush():
    with patch("queue_client.redis.Redis") as mock_redis_cls:
        redis_mock = AsyncMock()
        mock_redis_cls.return_value = redis_mock

        queue = RedisQueue()

        items = [
            Summary(
                district="d1",
                problemCount=1,
                topIssues="a",
                difficultIssues="b",
                summary="s1",
            ),
            Summary(
                district="d2",
                problemCount=2,
                topIssues="c",
                difficultIssues="d",
                summary="s2",
            ),
        ]

        await queue.push(items)

        payload = json.dumps([i.dict(by_alias=True) for i in items])
        redis_mock.lpush.assert_awaited_once_with(
            "queue:analyze:results", payload
        )


@pytest.mark.asyncio
async def test_summary_push_serializes_string_and_calls_lpush():
    with patch("queue_client.redis.Redis") as mock_redis_cls:
        redis_mock = AsyncMock()
        mock_redis_cls.return_value = redis_mock

        queue = RedisQueue()

        summary = "global summary"

        await queue.summary_push(summary)

        redis_mock.lpush.assert_awaited_once_with(
            "queue:analyze:summary", json.dumps(summary)
        )


@pytest.mark.asyncio
async def test_pop_validates_batch_from_json():
    with patch("queue_client.redis.Redis") as mock_redis_cls:
        redis_mock = AsyncMock()
        mock_redis_cls.return_value = redis_mock

        batch = Batch(
            isLastBatch=False,
            items=[
                Incident(district="d1", topic="t1", text="problem 1"),
                Incident(district="d2", topic="t2", text="problem 2"),
            ],
        )

        batch_json = batch.model_dump_json(by_alias=True)

        redis_mock.brpop = AsyncMock(
            return_value=("queue:analyze:tasks", batch_json)
        )

        queue = RedisQueue()

        result = await queue.pop()

        assert isinstance(result, Batch)
        assert result.is_last_batch is False
        assert len(result.items) == 2
        assert result.items[0].district == "d1"
        assert result.items[0].topic == "t1"
        assert result.items[0].text == "problem 1"

        redis_mock.brpop.assert_awaited_once_with(
            "queue:analyze:tasks", timeout=30
        )



@pytest.mark.asyncio
async def test_execute_with_retry_reconnects_on_connection_error():
    with patch("queue_client.redis.Redis") as mock_redis_cls:
        redis_mock = AsyncMock()
        mock_redis_cls.return_value = redis_mock

        queue = RedisQueue()

        calls = {"n": 0}

        async def failing_then_success(*args, **kwargs):
            if calls["n"] == 0:
                calls["n"] += 1
                raise RedisConnectionError("test")
            return "ok"

        coro_fn = AsyncMock(side_effect=failing_then_success)

        queue._reconnect = AsyncMock()

        result = await queue._execute_with_retry(coro_fn, 1, 2, key="value")

        assert result == "ok"
        assert calls["n"] == 1
        queue._reconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_reconnect_tries_until_ping_success():
    with patch("queue_client.redis.Redis") as mock_redis_cls:
        redis_mock = AsyncMock()
        redis_mock.ping = AsyncMock(side_effect=[RedisConnectionError("fail"), "PONG"])
        mock_redis_cls.return_value = redis_mock

        queue = RedisQueue()

        import queue_client.redis as redis_module
        redis_module._RETRY_DELAYS = [0, 0]

        queue._redis.aclose = AsyncMock(return_value=None)

        await queue._reconnect()

        assert redis_mock.ping.await_count >= 2
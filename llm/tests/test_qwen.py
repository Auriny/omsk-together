import pytest

from unittest.mock import AsyncMock, MagicMock, patch
from dto import AreaProblems, Summary
from pipeline.processor.qwen import QwenProcessor
from collections import defaultdict


class FakeTopic:
    def __init__(self, problems, count=0, difficult=0):
        self._problems = problems
        self.count = count
        self.difficult = difficult

    def get_problems(self):
        return self._problems


def make_area() -> AreaProblems:
    area = AreaProblems()
    area.problem_count = 7
    area.problems = {
        "water": FakeTopic(["a", "b", "c"], count=4, difficult=2),
        "road": FakeTopic(["d", "e"], count=3, difficult=1),
    }
    return area


@pytest.mark.asyncio
async def test_process_builds_summaries():
    with patch("pipeline.processor.qwen.Qwen") as mock_qwen_cls:
        mock_model = MagicMock()
        mock_model.summarize = AsyncMock(side_effect=["sum1", "sum2"])
        mock_qwen_cls.get_instance.return_value = mock_model

        processor = QwenProcessor()

        area1 = make_area()
        area2 = make_area()

        items = [("district-1", area1), ("district-2", area2)]

        result = await processor.process(items)

        assert len(result) == 2
        assert result[0].district == "district-1"
        assert result[0].problem_count == 7
        assert result[0].top_issues == "water (4), road (3)"
        assert result[0].difficult_issues == "road (1), water (2)"
        assert result[0].summary == "sum1"

        assert result[1].district == "district-2"
        assert result[1].summary == "sum2"

        mock_model.summarize.assert_any_await(["a", "b", "c", "d", "e"])
        assert mock_model.summarize.await_count == 2


@pytest.mark.asyncio
async def test_summarize_by_summary_joins_texts():
    with patch("pipeline.processor.qwen.Qwen") as mock_qwen_cls:
        mock_model = MagicMock()
        mock_model.summarize_summary = AsyncMock(return_value="final summary")
        mock_qwen_cls.get_instance.return_value = mock_model

        processor = QwenProcessor()

        items = [
            Summary(
                district="d1",
                problemCount=1,
                topIssues="a",
                difficultIssues="b",
                summary="first",
            ),
            Summary(
                district="d2",
                problemCount=2,
                topIssues="c",
                difficultIssues="d",
                summary="second",
            ),
        ]

        result = await processor.summarize_by_summary(items)

        assert result == "final summary"
        mock_model.summarize_summary.assert_awaited_once_with("first\n\nsecond")


def test_get_problems_stops_at_25():
    area = AreaProblems()
    area.problems = defaultdict(
        FakeTopic,
        {
            "t1": FakeTopic([f"p1_{i}" for i in range(10)]),
            "t2": FakeTopic([f"p2_{i}" for i in range(10)]),
            "t3": FakeTopic([f"p3_{i}" for i in range(10)]),
            "t4": FakeTopic([f"p4_{i}" for i in range(10)]),
            "t5": FakeTopic([f"p5_{i}" for i in range(10)]),
        },
    )

    result = area.get_problems()

    assert len(result) == 30
    assert result[:6] == [f"p1_{i}" for i in range(6)]
    assert result[6:12] == [f"p2_{i}" for i in range(6)]
    assert result[12:18] == [f"p3_{i}" for i in range(6)]
    assert result[18:24] == [f"p4_{i}" for i in range(6)]
    assert result[24:30] == [f"p5_{i}" for i in range(6)]


@pytest.mark.asyncio
async def test_process_with_empty_items_returns_empty_list():
    with patch("pipeline.processor.qwen.Qwen") as mock_qwen_cls:
        mock_model = MagicMock()
        mock_model.summarize = AsyncMock()
        mock_qwen_cls.get_instance.return_value = mock_model

        processor = QwenProcessor()

        result = await processor.process([])

        assert result == []
        mock_model.summarize.assert_not_called()


@pytest.mark.asyncio
async def test_summarize_by_summary_with_empty_list():
    with patch("pipeline.processor.qwen.Qwen") as mock_qwen_cls:
        mock_model = MagicMock()
        mock_model.summarize_summary = AsyncMock(return_value="final")
        mock_qwen_cls.get_instance.return_value = mock_model

        processor = QwenProcessor()

        result = await processor.summarize_by_summary([])

        assert result == "final"
        mock_model.summarize_summary.assert_awaited_once_with("")


def test_topics_by_count_with_less_than_three_topics():
    area = AreaProblems()
    area.problems = defaultdict(
        FakeTopic,
        {
            "road": FakeTopic([], count=7, difficult=2),
            "water": FakeTopic([], count=3, difficult=1),
        },
    )

    assert area.topics_by_count == ["road (7)", "water (3)"]


def test_topics_by_difficult_with_less_than_three_topics():
    area = AreaProblems()
    area.problems = defaultdict(
        FakeTopic,
        {
            "road": FakeTopic([], count=7, difficult=2),
            "water": FakeTopic([], count=3, difficult=1),
        },
    )

    assert area.topics_by_difficult == ["water (1)", "road (2)"]
import pytest
from collections import defaultdict
from dataclasses import dataclass, field
from dto import AreaProblems, Topic


class TestTopic:
    def test_difficult_returns_key_with_most_items(self):
        topic = Topic(
            problems={
                1: ["a", "b"],
                2: ["c"],
                5: ["d", "e", "f"],
            }
        )

        assert topic.difficult == 5

    def test_get_problems_returns_desc_by_difficult(self):
        topic = Topic(
            problems={
                1: ["a", "b"],
                2: ["c"],
                5: ["d", "e", "f"],
            }
        )

        assert topic.get_problems() == ["d", "e", "f", "c", "a", "b"]

    def test_get_problems_with_single_group(self):
        topic = Topic(problems={3: ["x", "y"]})

        assert topic.get_problems() == ["x", "y"]


class TestAreaProblems:
    def test_get_problems_takes_max_six_from_each_topic(self):
        area = AreaProblems()
        area.problems = defaultdict(
            Topic,
            {
                "t1": Topic(problems={1: [f"t1_{i}" for i in range(10)]}),
                "t2": Topic(problems={1: [f"t2_{i}" for i in range(10)]}),
                "t3": Topic(problems={1: [f"t3_{i}" for i in range(10)]}),
                "t4": Topic(problems={1: [f"t4_{i}" for i in range(10)]}),
            },
        )

        result = area.get_problems()

        assert len(result) == 24
        assert result[:6] == [f"t1_{i}" for i in range(6)]
        assert result[6:12] == [f"t2_{i}" for i in range(6)]
        assert result[12:18] == [f"t3_{i}" for i in range(6)]
        assert result[18:24] == [f"t4_{i}" for i in range(6)]

    def test_topics_by_count_returns_top_three_desc(self):
        area = AreaProblems()
        area.problems = defaultdict(
            Topic,
            {
                "road": Topic(count=7, problems={1: ["a"]}),
                "water": Topic(count=12, problems={1: ["b"]}),
                "heat": Topic(count=3, problems={1: ["c"]}),
                "trash": Topic(count=9, problems={1: ["d"]}),
            },
        )

        assert area.topics_by_count == ["water (12)", "trash (9)", "road (7)"]

    def test_topics_by_count_with_less_than_three_topics(self):
        area = AreaProblems()
        area.problems = defaultdict(
            Topic,
            {
                "road": Topic(count=7, problems={1: ["a"]}),
                "water": Topic(count=12, problems={1: ["b"]}),
            },
        )

        assert area.topics_by_count == ["water (12)", "road (7)"]

    def test_topics_by_difficult_returns_top_three_asc(self):
        area = AreaProblems()
        area.problems = defaultdict(
            Topic,
            {
                "road": Topic(problems={5: ["a"], 2: ["b", "c"]}),
                "water": Topic(problems={1: ["d"], 3: ["e", "f"]}),
                "heat": Topic(problems={4: ["g"]}),
                "trash": Topic(problems={2: ["h", "i"], 6: ["j"]}),
            },
        )

        assert area.topics_by_difficult == ["road (2)", "trash (2)", "water (3)"]

    def test_topics_by_difficult_with_less_than_three_topics(self):
        area = AreaProblems()
        area.problems = defaultdict(
            Topic,
            {
                "road": Topic(problems={5: ["a"], 2: ["b", "c"]}),
                "water": Topic(problems={1: ["d"], 3: ["e", "f"]}),
            },
        )

        assert area.topics_by_difficult == ["road (2)", "water (3)"]
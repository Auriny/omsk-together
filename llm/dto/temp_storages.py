from collections import defaultdict
from dataclasses import dataclass, field

from sympy.logic import true


@dataclass
class Topic:
    """Topic class."""

    count: int = 0
    problems: dict[int, list[str]] = field(default_factory=defaultdict)

    @property
    def difficult(self) -> int:
        return max(
            [
                (difficult, len(items))
                for difficult, items in self.problems.items()
            ],
            key=lambda x: x[1],
        )[0]

    def get_problems(self) -> list[str]:
        result = []
        for i in sorted(
            self.problems.items(),
            key=lambda x: x[0],
            reverse=true
        ):
            result.extend(i[1])
        return result

@dataclass
class AreaProblems:
    """Temporary storage for problems in an area."""

    problem_count: int = 0
    problems: dict[str, Topic] = field(default_factory=defaultdict)

    def get_problems(self) -> list[str]:
        result = []
        for topic in self.problems:
            result.extend(self.problems[topic].get_problems())
        return result[:25]

    @property
    def topics_by_count(self) -> list[str]:
        topics = [
            (topic, item.count)
            for topic, item in self.problems.items()
        ]
        return [
            f"{i[0]} ({i[1]})"
            for i in sorted(
                topics,
                key=lambda x: x[1],
                reverse=True
            )[:3]
        ]

    @property
    def topics_by_difficult(self) -> list[str]:
        topics = [
            (topic, item.difficult)
            for topic, item in self.problems.items()
        ]
        return [
            f"{i[0]} ({i[1]})"
            for i in sorted(
                topics,
                key=lambda x: x[1]
            )[:3]
        ]


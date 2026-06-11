from dataclasses import dataclass, field


@dataclass
class Topic:
    """Topic class."""

    count: int = 0
    problems: dict[int, list[str]] = field(default_factory=dict)

    @property
    def difficult(self) -> int:
        return max(
            *[
                (difficult, len(items))
                for difficult, items in self.problems.items()
            ],
            key=lambda x: x[1],
        )[0]

@dataclass
class AreaProblems:
    """Temporary storage for problems in an area."""

    problem_count: int = 0
    problems: dict[str, Topic] = field(default_factory=dict)

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


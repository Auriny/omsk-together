from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class AreaProblems:
    """Temporary storage for problems in an area."""

    problem_count: int = 0
    topics: dict[str, int] = field(default_factory=defaultdict)
    problems: list[str] = field(default_factory=list)

@dataclass
class AreaProblem:
    """Temporary storage for a problem in an area."""

    district: str
    topic: str
    problem: str

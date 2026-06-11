from enum import IntEnum


class LabelsEnum(IntEnum):
    """Labels enum."""

    EMERGENCY = 5
    CRITICAL = 4
    SERIOUS = 3
    MODERATE = 2
    SMALL = 1
    NOT_PROBLEM = 0

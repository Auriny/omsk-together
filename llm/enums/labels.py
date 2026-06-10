from enum import StrEnum


class LabelsEnum(StrEnum):
    """Labels enum."""

    EMERGENCY = "чрезвычайная ситуация"
    CRITICAL = "критическая проблема"
    SERIOUS = "серьёзная проблема"
    MODERATE = "умеренная проблема"
    SMALL = "маленькая проблема"
    NOT_PROBLEM = "не проблема"

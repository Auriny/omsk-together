from typing import Protocol, TypeVar, runtime_checkable

T = TypeVar("T")
V = TypeVar("V")

@runtime_checkable
class ClassifierModelInterface(Protocol[T, V]): # type: ignore[misc]
    """Interface for a classifier model."""

    def filter(self, item: T) -> V:
        """Filter an item and return the result."""

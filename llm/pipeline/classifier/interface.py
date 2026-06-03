from typing import Protocol, TypeVar, runtime_checkable

T = TypeVar("T")
V = TypeVar("V")

@runtime_checkable
class ClassifierInterface(Protocol[T, V]): # type: ignore[misc]
    """Interface for a classifier usage."""

    def classify(self, item: T) -> V:
        """Classify an item and return its class."""

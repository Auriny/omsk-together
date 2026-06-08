from typing import Protocol, TypeVar, runtime_checkable

T = TypeVar("T")
V = TypeVar("V")

@runtime_checkable
class ClassifierPipelineInterface(Protocol[T, V]): # type: ignore[misc]
    """Interface for a classifier usage."""

    async def classify(self, items: T) -> V:
        """Classify an item and return its class."""

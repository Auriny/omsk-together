from typing import Protocol, TypeVar, runtime_checkable

T = TypeVar("T")
V = TypeVar("V")

@runtime_checkable
class ProcessorModelInterface(Protocol[T, V]): # type: ignore[misc]
    """Interface for a processor model."""

    def summarize(self, item: T) -> V:
        """Summarize an item and return the result."""

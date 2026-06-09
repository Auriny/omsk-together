from typing import Protocol, TypeVar, runtime_checkable

T = TypeVar("T")
V = TypeVar("V")
R = TypeVar["R"]

@runtime_checkable
class ProcessorModelInterface(Protocol[T, V, R]): # type: ignore[misc]
    """Interface for a processor model."""

    async def summarize(self, items: T) -> V:
        """Summarize an item and return the result."""

    async def summarize_summary(self, item: R) -> R:
        """Summarize by summary."""

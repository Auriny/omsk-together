from typing import Protocol, TypeVar, runtime_checkable

T = TypeVar("T")
V = TypeVar("V")
R = TypeVar("R")

@runtime_checkable
class ProcessorPipelineInterface(Protocol[T, V, R]): # type: ignore[misc]
    """Interface for processing items in a pipeline."""

    async def process(self, items: T) -> V:
        """Process an item and return the result."""

    async def summarize_by_summary(self, items: V) -> R:
        """Process summary of summary."""

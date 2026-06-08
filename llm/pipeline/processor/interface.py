from typing import Protocol, TypeVar, runtime_checkable

T = TypeVar("T")
V = TypeVar("V")

@runtime_checkable
class ProcessorPipelineInterface(Protocol[T, V]): # type: ignore[misc]
    """Interface for processing items in a pipeline."""

    async def process(self, items: T) -> V:
        """Process an item and return the result."""

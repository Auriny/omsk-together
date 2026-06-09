from typing import Protocol, TypeVar, runtime_checkable

T = TypeVar("T")
V = TypeVar("V")
R = TypeVar["R"]

@runtime_checkable
class QueueInterface(Protocol[T, V, R]): # type: ignore[misc]
    """Interface for a queue usage."""

    async def push(self, item: V) -> None:
        """Push an item to the queue."""

    async def summary_push(self, item: R) -> None:
        """Push an item to the summary queue."""

    async def pop(self) -> T:
        """Pop an item from the queue."""

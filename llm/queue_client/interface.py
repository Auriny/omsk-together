from typing import Protocol, TypeVar, runtime_checkable

T = TypeVar("T")
V = TypeVar("V")

@runtime_checkable
class QueueInterface(Protocol[T, V]): # type: ignore[misc]
    """Interface for a queue usage."""

    def push(self, item: V) -> None:
        """Push an item to the queue."""

    def pop(self) -> T:
        """Pop an item from the queue."""

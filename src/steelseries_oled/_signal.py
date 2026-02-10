"""Signal handling utilities for graceful shutdown."""

import signal
import sys
import threading
from contextlib import contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator


class InterruptibleState:
    """Signal-aware state that supports interruptible waits.

    Callable: returns True while running, False after interrupt.
    Also provides wait() for interruptible sleeps.
    """

    __slots__ = ("_event",)

    def __init__(self) -> None:
        self._event = threading.Event()

    def __call__(self) -> bool:
        """Return True if still running, False if interrupted."""
        return not self._event.is_set()

    def stop(self) -> None:
        """Signal that execution should stop."""
        self._event.set()

    def wait(self, timeout: float) -> None:
        """Sleep for up to *timeout* seconds, returning early if interrupted."""
        self._event.wait(timeout)


@contextmanager
def interruptible() -> Generator[InterruptibleState]:
    """Context manager for handling interrupt signals gracefully.

    Yields an InterruptibleState that is callable (returns True while
    running) and supports interruptible waits via .wait(timeout).

    Example:
        with interruptible() as is_running:
            while is_running():
                do_work()
                is_running.wait(1.0)  # sleeps up to 1s, returns early on Ctrl+C

    Yields:
        InterruptibleState instance.
    """
    state = InterruptibleState()

    def handler(signum: int, frame: object) -> None:
        state.stop()

    # Install handlers, saving old ones
    old_sigint = signal.signal(signal.SIGINT, handler)
    old_sigterm = None
    if sys.platform != "win32":
        old_sigterm = signal.signal(signal.SIGTERM, handler)

    try:
        yield state
    finally:
        # Restore original handlers
        signal.signal(signal.SIGINT, old_sigint)
        if sys.platform != "win32" and old_sigterm is not None:
            signal.signal(signal.SIGTERM, old_sigterm)

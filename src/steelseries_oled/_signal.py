"""Signal handling utilities for graceful shutdown."""

import signal
import sys
from contextlib import contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Generator


@contextmanager
def interruptible() -> Generator[Callable[[], bool]]:
    """Context manager for handling interrupt signals gracefully.

    Yields a callable that returns True while the process should continue
    running, and False after SIGINT or SIGTERM is received.

    Example:
        with interruptible() as is_running:
            while is_running():
                do_work()

    Yields:
        A callable returning True if still running, False if interrupted.
    """
    state = {"running": True}

    def handler(signum: int, frame: object) -> None:
        state["running"] = False

    # Install handlers, saving old ones
    old_sigint = signal.signal(signal.SIGINT, handler)
    old_sigterm = None
    if sys.platform != "win32":
        old_sigterm = signal.signal(signal.SIGTERM, handler)

    try:
        yield lambda: state["running"]
    finally:
        # Restore original handlers
        signal.signal(signal.SIGINT, old_sigint)
        if sys.platform != "win32" and old_sigterm is not None:
            signal.signal(signal.SIGTERM, old_sigterm)

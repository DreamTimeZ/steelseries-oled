"""Tests for signal handling utilities."""

import threading
import time

from steelseries_oled._signal import InterruptibleState, interruptible


class TestInterruptibleState:
    """Tests for InterruptibleState class."""

    def test_initially_running(self) -> None:
        """State should report running before stop is called."""
        state = InterruptibleState()
        assert state() is True

    def test_stop_sets_not_running(self) -> None:
        """State should report not running after stop."""
        state = InterruptibleState()
        state.stop()
        assert state() is False

    def test_wait_returns_early_on_stop(self) -> None:
        """wait() should return well before timeout when stop() is called."""
        state = InterruptibleState()

        def stop_after_delay() -> None:
            time.sleep(0.05)
            state.stop()

        t = threading.Thread(target=stop_after_delay)
        t.start()

        start = time.monotonic()
        state.wait(10.0)  # Would take 10s without early return
        elapsed = time.monotonic() - start

        t.join()
        assert elapsed < 1.0  # Generous bound; real elapsed ~0.05s
        assert state() is False

    def test_wait_respects_timeout(self) -> None:
        """wait() should return after timeout if not stopped."""
        state = InterruptibleState()

        start = time.monotonic()
        state.wait(0.05)
        elapsed = time.monotonic() - start

        assert elapsed >= 0.04  # Allow small timing variance
        assert state() is True  # Still running — not stopped


class TestInterruptible:
    """Tests for interruptible context manager."""

    def test_yields_running_state(self) -> None:
        """Should yield a callable returning True."""
        with interruptible() as is_running:
            assert is_running() is True

    def test_has_wait_method(self) -> None:
        """Yielded object should have a wait method."""
        with interruptible() as is_running:
            assert hasattr(is_running, "wait")

"""Abstract base for stats display backends."""

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self

from steelseries_oled.models import SystemStats


class StatsBackend(ABC):
    """Abstract base class for stats display backends.

    Backends handle the actual communication with the keyboard's
    OLED display, whether through direct HID or GameSense API.

    Usage:
        with backend:
            while running:
                backend.update_stats(stats)
    """

    @abstractmethod
    def __enter__(self) -> Self:
        """Initialize the backend connection."""
        ...

    @abstractmethod
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Clean up the backend connection."""
        ...

    @abstractmethod
    def update_stats(self, stats: SystemStats) -> None:
        """Update the OLED display with current stats.

        Args:
            stats: System statistics to display. Contains CPU, memory,
                network, and optionally GPU and temperature data.
                Backends should render available data and gracefully
                handle missing optional fields.
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the backend name for display purposes."""
        ...

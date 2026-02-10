"""Stats display backends for SteelSeries OLED.

This module provides different backends for displaying stats on the
keyboard's OLED screen:

- GameSenseBackend: Uses SteelSeries GG HTTP API (works on all keyboards)
- HIDBitmapBackend: Uses direct HID communication (legacy keyboards only)
- HIDGen3Backend: Uses direct HID communication (Gen3 keyboards, no GG required)

Usage:
    from steelseries_oled.backends import create_backend, BackendType
    from steelseries_oled.models import SystemStats

    # Auto-detect best backend
    backend = create_backend()

    # Or specify explicitly
    backend = create_backend(BackendType.GAMESENSE)

    with backend:
        stats = SystemStats(
            cpu_percent=50.0,
            mem_used_gb=12.0, mem_total_gb=32.0,
            net_up_bytes=1000.0, net_down_bytes=5000.0,
        )
        backend.update_stats(stats)
"""

from enum import Enum
from pathlib import Path

from steelseries_oled.backends.base import StatsBackend
from steelseries_oled.backends.gamesense import (
    GameSenseBackend,
    is_gamesense_available,
)
from steelseries_oled.backends.hid import HIDBitmapBackend
from steelseries_oled.backends.hid_gen3 import HIDGen3Backend
from steelseries_oled.device import is_gen3_device


class BackendType(Enum):
    """Available backend types for stats display."""

    AUTO = "auto"
    GAMESENSE = "gamesense"
    HID = "hid"
    HID_GEN3 = "hid_gen3"


def detect_best_backend() -> BackendType:
    """Detect the best available backend.

    For Gen3 keyboards: returns HID_GEN3 (no GG required).
    For legacy keyboards: prefers GameSense if available, otherwise HID.

    Returns:
        The recommended backend type.
    """
    # Gen3 keyboards: prefer direct HID (no GG required)
    if is_gen3_device():
        return BackendType.HID_GEN3

    # Legacy keyboards: prefer GameSense if available
    if is_gamesense_available():
        return BackendType.GAMESENSE
    return BackendType.HID


def create_backend(
    backend_type: BackendType = BackendType.AUTO,
    font_path: Path | None = None,
    update_interval: float = 1.0,
) -> StatsBackend:
    """Create a stats display backend.

    Args:
        backend_type: Type of backend to create. AUTO will detect
            the best available option.
        font_path: Path to custom font (HID backends only).
        update_interval: Seconds between updates (used by GameSense timer).

    Returns:
        A StatsBackend instance ready for use as a context manager.

    Raises:
        ValueError: If an invalid backend type is specified.

    Example:
        backend = create_backend()
        with backend:
            stats = SystemStats(...)  # See module docstring
            backend.update_stats(stats)
    """
    if backend_type == BackendType.AUTO:
        backend_type = detect_best_backend()

    if backend_type == BackendType.GAMESENSE:
        return GameSenseBackend(update_interval=update_interval)
    if backend_type == BackendType.HID:
        return HIDBitmapBackend(font_path=font_path)
    if backend_type == BackendType.HID_GEN3:
        return HIDGen3Backend(font_path=font_path)

    msg = f"Unknown backend type: {backend_type}"
    raise ValueError(msg)


__all__ = [
    "BackendType",
    "GameSenseBackend",
    "HIDBitmapBackend",
    "HIDGen3Backend",
    "StatsBackend",
    "create_backend",
    "detect_best_backend",
    "is_gamesense_available",
    "is_gen3_device",
]

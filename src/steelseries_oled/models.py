"""Data models for steelseries-oled."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SystemStats:
    """System statistics for OLED display.

    All fields are optional except cpu_percent and memory.
    Backends should render what's available and skip unavailable metrics.
    """

    # CPU (always available)
    cpu_percent: float
    cpu_max_core: float  # Highest single core usage (bottleneck detection)

    # Memory (always available)
    mem_used_gb: float
    mem_total_gb: float

    # Network (always available)
    net_up_bytes: float  # Bytes per second
    net_down_bytes: float  # Bytes per second

    # CPU temperature (platform-dependent)
    cpu_temp: float | None = None

    # GPU (NVIDIA only via NVML)
    gpu_percent: float | None = None
    gpu_temp: float | None = None

    @property
    def mem_percent(self) -> float:
        """Calculate memory usage percentage."""
        if self.mem_total_gb <= 0:
            return 0.0
        return (self.mem_used_gb / self.mem_total_gb) * 100


def format_rate(bytes_per_sec: float) -> str:
    """Format network rate for compact display (B/K/M).

    Thresholds account for rounding to prevent overflow (e.g., "1000K" → "1.0M").
    """
    # Use 999_500 threshold: 999500/1M = 0.9995 → rounds to "1.0M"
    if bytes_per_sec >= 999_500:
        return f"{bytes_per_sec / 1_000_000:.1f}M"
    # Use 999.5 threshold: 999.5/1K = 0.9995 → rounds to "1K"
    if bytes_per_sec >= 999.5:
        return f"{bytes_per_sec / 1_000:.0f}K"
    return f"{bytes_per_sec:.0f}B"

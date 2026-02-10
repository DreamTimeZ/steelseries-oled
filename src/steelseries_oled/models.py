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


def build_stats_lines(stats: SystemStats) -> tuple[str, str, str]:
    """Build the three display lines from system stats.

    Returns:
        (line1, line2, line3) ready for rendering or sending to GameSense.
    """
    # Line 1: CPU + GPU (adaptive)
    line1_parts = [f"C:{stats.cpu_percent:3.0f}%"]
    if stats.cpu_temp is not None:
        line1_parts.append(f"{stats.cpu_temp:.0f}C")
    if stats.gpu_percent is not None:
        line1_parts.append(f"G:{stats.gpu_percent:.0f}%")
        if stats.gpu_temp is not None:
            line1_parts.append(f"{stats.gpu_temp:.0f}C")
    line1 = " ".join(line1_parts)

    # Line 2: RAM
    line2 = f"RAM:{stats.mem_used_gb:.1f}/{stats.mem_total_gb:.0f}GB"

    # Line 3: Network (download first - users care more about it)
    up = format_rate(stats.net_up_bytes)
    down = format_rate(stats.net_down_bytes)
    line3 = f"D:{down} U:{up}"

    return line1, line2, line3


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

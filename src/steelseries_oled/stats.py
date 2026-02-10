"""System statistics display on OLED.

Supports multiple backends:
- GameSense: Uses SteelSeries GG text mode (works on ALL keyboards including Gen3)
- HID: Uses direct bitmap rendering (legacy keyboards only)
- HID-Gen3: Uses direct bitmap rendering (Gen3 keyboards, no GG required)

The backend is auto-detected based on hardware and SteelSeries GG availability.
"""

import logging
import time
from pathlib import Path

import psutil

from steelseries_oled._signal import interruptible
from steelseries_oled.backends import BackendType, create_backend
from steelseries_oled.exceptions import DeviceCommunicationError
from steelseries_oled.models import SystemStats

logger = logging.getLogger(__name__)

# Maximum consecutive failures before exiting
MAX_CONSECUTIVE_FAILURES = 5


class _NetworkRateTracker:
    """Track network I/O rates over time."""

    def __init__(self) -> None:
        self._prev = psutil.net_io_counters()  # Can be None if no network interfaces
        self._prev_time = time.monotonic()
        self._first_call = True

    def get_rates(self) -> tuple[float, float]:
        """Get current upload/download rates in bytes per second.

        Returns 0.0 on the first call since we need two samples to calculate rate.
        Also returns 0.0 if no network interfaces are available.
        """
        now = time.monotonic()
        current = psutil.net_io_counters()  # Can be None if no network interfaces
        elapsed = now - self._prev_time

        # No network interfaces available (containers, isolated systems)
        if current is None or self._prev is None:
            self._prev = current
            self._prev_time = now
            self._first_call = False
            return 0.0, 0.0

        # First call: just establish baseline, return zeros
        if self._first_call:
            self._first_call = False
            self._prev = current
            self._prev_time = now
            return 0.0, 0.0

        if elapsed <= 0:
            return 0.0, 0.0

        up_rate = (current.bytes_sent - self._prev.bytes_sent) / elapsed
        down_rate = (current.bytes_recv - self._prev.bytes_recv) / elapsed

        self._prev = current
        self._prev_time = now

        return up_rate, down_rate


class _NvmlSession:
    """Manage a single NVML session across the stats loop lifetime.

    Keeps the NVIDIA driver connection open instead of calling
    nvmlInit/nvmlShutdown on every iteration, which causes hangs.
    """

    def __init__(self) -> None:
        self._available = False
        self._handle: object = None

        try:
            from pynvml import (  # noqa: PLC0415
                NVMLError,
                nvmlDeviceGetCount,
                nvmlDeviceGetHandleByIndex,
                nvmlInit,
            )
        except ImportError:
            return

        try:
            nvmlInit()
            if nvmlDeviceGetCount() > 0:
                self._handle = nvmlDeviceGetHandleByIndex(0)
                self._available = True
        except NVMLError:
            pass

    @property
    def available(self) -> bool:
        return self._available

    def get_stats(self) -> tuple[float, float] | None:
        """Get GPU utilization % and temperature. Returns None on failure."""
        if not self._available:
            return None

        try:
            from pynvml import (  # noqa: PLC0415
                NVML_TEMPERATURE_GPU,
                NVMLError,
                nvmlDeviceGetTemperature,
                nvmlDeviceGetUtilizationRates,
            )
        except ImportError:
            return None

        try:
            util = nvmlDeviceGetUtilizationRates(self._handle)
            temp = nvmlDeviceGetTemperature(self._handle, NVML_TEMPERATURE_GPU)
            return float(util.gpu), float(temp)
        except NVMLError as e:
            logger.debug("GPU stats unavailable: %s", e)
            return None

    def close(self) -> None:
        if self._available:
            try:
                from pynvml import nvmlShutdown  # noqa: PLC0415

                nvmlShutdown()
            except Exception:
                pass
            self._available = False
            self._handle = None


class _Capabilities:
    """Detected system capabilities."""

    def __init__(self) -> None:
        self.has_cpu_temp = self._detect_cpu_temp()

    def _detect_cpu_temp(self) -> bool:
        """Check if CPU temperature sensors are available."""
        try:
            temps = psutil.sensors_temperatures()
            return bool(temps)
        except (AttributeError, OSError):
            return False


def _get_cpu_temp() -> float | None:
    """Extract CPU temperature from available sensors."""
    try:
        temps = psutil.sensors_temperatures()
    except (AttributeError, OSError):
        return None
    if not temps:
        return None
    # Try common sensor names in priority order
    for name in ["coretemp", "k10temp", "cpu_thermal", "acpitz"]:
        if temps.get(name):
            return float(temps[name][0].current)
    # Fallback: first available sensor
    first_sensor = next(iter(temps.values()), None)
    if first_sensor:
        temp: float = first_sensor[0].current
        return temp
    return None


def _gather_stats(
    caps: _Capabilities,
    net_tracker: _NetworkRateTracker,
    nvml: _NvmlSession,
) -> SystemStats:
    """Gather all available system statistics."""
    # CPU
    per_core = psutil.cpu_percent(percpu=True)
    cpu_avg = sum(per_core) / len(per_core) if per_core else 0.0

    # Memory
    mem = psutil.virtual_memory()
    mem_used_gb = mem.used / (1024**3)
    mem_total_gb = mem.total / (1024**3)

    # Network
    net_up, net_down = net_tracker.get_rates()

    # Optional: CPU temp
    cpu_temp = _get_cpu_temp() if caps.has_cpu_temp else None

    # Optional: GPU (uses persistent NVML session)
    gpu_percent = None
    gpu_temp = None
    gpu_stats = nvml.get_stats()
    if gpu_stats:
        gpu_percent, gpu_temp = gpu_stats

    return SystemStats(
        cpu_percent=cpu_avg,
        mem_used_gb=mem_used_gb,
        mem_total_gb=mem_total_gb,
        net_up_bytes=net_up,
        net_down_bytes=net_down,
        cpu_temp=cpu_temp,
        gpu_percent=gpu_percent,
        gpu_temp=gpu_temp,
    )


def display_stats(
    font_path: Path | None = None,
    update_interval: float = 1.0,
    backend: BackendType = BackendType.AUTO,
) -> bool:
    """Display live system statistics on the OLED.

    Shows adaptive stats based on detected hardware:
    - CPU usage and temperature (if available)
    - RAM used/total
    - GPU usage and temperature (if NVIDIA GPU present)
    - Network upload/download rates

    Updates continuously until interrupted with Ctrl+C.

    Args:
        font_path: Path to TrueType font file (HID backends only).
        update_interval: Seconds between updates.
        backend: Which backend to use. AUTO will detect best option.

    Returns:
        True if exited normally (e.g., Ctrl+C), False if device became
        unresponsive after MAX_CONSECUTIVE_FAILURES.

    Raises:
        DeviceNotFoundError: If no compatible device is found and
            SteelSeries GG is not running.
    """
    stats_backend = create_backend(
        backend, font_path=font_path, update_interval=update_interval
    )

    # Detect capabilities and initialize trackers
    caps = _Capabilities()
    net_tracker = _NetworkRateTracker()
    nvml = _NvmlSession()

    try:
        print(f"Using {stats_backend.name} backend.")
        if nvml.available:
            print("GPU detected (NVIDIA).")
        if caps.has_cpu_temp:
            print("CPU temperature sensors detected.")
        print("Press Ctrl+C to exit.")

        # Prime the CPU percent measurement (first call always returns 0)
        psutil.cpu_percent(percpu=True)

        consecutive_failures = 0

        with interruptible() as is_running, stats_backend:
            while is_running():
                try:
                    stats = _gather_stats(caps, net_tracker, nvml)
                    stats_backend.update_stats(stats)
                    consecutive_failures = 0
                except DeviceCommunicationError as e:
                    consecutive_failures += 1
                    logger.warning(
                        "Update failed (%d/%d): %s",
                        consecutive_failures,
                        MAX_CONSECUTIVE_FAILURES,
                        e,
                    )
                    if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                        print(
                            f"Device unresponsive after {MAX_CONSECUTIVE_FAILURES} "
                            "consecutive failures. Exiting.",
                        )
                        return False
                is_running.wait(update_interval)
    finally:
        nvml.close()

    print()
    return True

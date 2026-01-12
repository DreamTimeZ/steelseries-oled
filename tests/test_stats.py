"""Tests for stats module."""

from collections import namedtuple
from unittest.mock import MagicMock, patch

from steelseries_oled.stats import (
    _Capabilities,
    _gather_stats,
    _get_cpu_temp,
    _NetworkRateTracker,
)

# Mock for psutil.net_io_counters return type
MockNetIO = namedtuple("MockNetIO", ["bytes_sent", "bytes_recv"])


class TestNetworkRateTracker:
    """Tests for _NetworkRateTracker class."""

    # === Fix 2 verification: None handling ===

    def test_init_with_none_counters(self) -> None:
        """Tracker should handle None from net_io_counters() in __init__."""
        with patch("steelseries_oled.stats.psutil.net_io_counters", return_value=None):
            # Should not raise
            tracker = _NetworkRateTracker()
            assert tracker._prev is None

    def test_get_rates_returns_zero_when_no_interfaces(self) -> None:
        """get_rates should return (0.0, 0.0) when no network interfaces."""
        with patch("steelseries_oled.stats.psutil.net_io_counters", return_value=None):
            tracker = _NetworkRateTracker()
            up, down = tracker.get_rates()
            assert up == 0.0
            assert down == 0.0

    def test_get_rates_handles_none_after_init(self) -> None:
        """get_rates should handle net_io_counters returning None mid-run."""
        initial = MockNetIO(bytes_sent=1000, bytes_recv=2000)

        with patch(
            "steelseries_oled.stats.psutil.net_io_counters", return_value=initial
        ):
            tracker = _NetworkRateTracker()

        # Network goes away mid-run
        with patch("steelseries_oled.stats.psutil.net_io_counters", return_value=None):
            up, down = tracker.get_rates()
            assert up == 0.0
            assert down == 0.0

    def test_get_rates_recovers_when_interfaces_appear(self) -> None:
        """Tracker should recover when network interfaces become available."""
        with patch("steelseries_oled.stats.psutil.net_io_counters", return_value=None):
            tracker = _NetworkRateTracker()
            # First call with None
            up, down = tracker.get_rates()
            assert up == 0.0
            assert down == 0.0

        # Network comes up
        counters = MockNetIO(bytes_sent=1000, bytes_recv=2000)
        with patch(
            "steelseries_oled.stats.psutil.net_io_counters", return_value=counters
        ):
            # Second call establishes baseline
            up, down = tracker.get_rates()
            assert up == 0.0  # Still zero (need two valid samples)
            assert down == 0.0

    # === Normal operation tests ===

    def test_first_call_returns_zero(self) -> None:
        """First call should return zeros (no rate calculation possible)."""
        counters = MockNetIO(bytes_sent=1000, bytes_recv=2000)
        with patch(
            "steelseries_oled.stats.psutil.net_io_counters", return_value=counters
        ):
            tracker = _NetworkRateTracker()
            up, down = tracker.get_rates()
            assert up == 0.0
            assert down == 0.0

    def test_rate_calculation(self) -> None:
        """Should calculate correct rates between samples."""
        initial = MockNetIO(bytes_sent=1000, bytes_recv=2000)
        with patch(
            "steelseries_oled.stats.psutil.net_io_counters", return_value=initial
        ):
            tracker = _NetworkRateTracker()
            tracker.get_rates()  # First call (baseline)

        # Simulate 1 second elapsed, 100 bytes sent, 200 received
        later = MockNetIO(bytes_sent=1100, bytes_recv=2200)
        with (
            patch("steelseries_oled.stats.psutil.net_io_counters", return_value=later),
            patch("steelseries_oled.stats.time.monotonic", return_value=1.0),
        ):
            # Need to also patch the initial time
            tracker._prev_time = 0.0
            up, down = tracker.get_rates()
            assert up == 100.0  # 100 bytes / 1 second
            assert down == 200.0  # 200 bytes / 1 second

    def test_zero_elapsed_time(self) -> None:
        """Should return zeros if no time elapsed (avoid division by zero)."""
        counters = MockNetIO(bytes_sent=1000, bytes_recv=2000)
        with patch(
            "steelseries_oled.stats.psutil.net_io_counters", return_value=counters
        ):
            tracker = _NetworkRateTracker()
            tracker._first_call = False  # Skip first-call logic
            tracker._prev = counters

        with (
            patch(
                "steelseries_oled.stats.psutil.net_io_counters", return_value=counters
            ),
            patch(
                "steelseries_oled.stats.time.monotonic",
                return_value=tracker._prev_time,
            ),
        ):
            up, down = tracker.get_rates()
            assert up == 0.0
            assert down == 0.0


class TestGetCpuTemp:
    """Tests for _get_cpu_temp function."""

    def test_priority_coretemp_first(self) -> None:
        """Should prefer coretemp sensor (Intel) over others."""
        mock_temps = {
            "acpitz": [MagicMock(current=50.0)],
            "coretemp": [MagicMock(current=65.0)],
            "k10temp": [MagicMock(current=70.0)],
        }
        with patch(
            "steelseries_oled.stats.psutil.sensors_temperatures",
            return_value=mock_temps,
            create=True,  # sensors_temperatures doesn't exist on Windows
        ):
            result = _get_cpu_temp()
            assert result == 65.0  # coretemp, not others

    def test_fallback_to_first_available(self) -> None:
        """Should fall back to first available sensor if no known names match."""
        mock_temps = {
            "unknown_sensor": [MagicMock(current=55.0)],
        }
        with patch(
            "steelseries_oled.stats.psutil.sensors_temperatures",
            return_value=mock_temps,
            create=True,  # sensors_temperatures doesn't exist on Windows
        ):
            result = _get_cpu_temp()
            assert result == 55.0

    def test_returns_none_when_no_sensors(self) -> None:
        """Should return None when no temperature sensors available."""
        with patch(
            "steelseries_oled.stats.psutil.sensors_temperatures",
            return_value={},
            create=True,  # sensors_temperatures doesn't exist on Windows
        ):
            result = _get_cpu_temp()
            assert result is None


class TestGatherStats:
    """Tests for _gather_stats function."""

    def test_handles_empty_cpu_cores(self) -> None:
        """Should handle empty cpu_percent list without ZeroDivisionError."""
        mock_caps = MagicMock(spec=_Capabilities)
        mock_caps.has_cpu_temp = False
        mock_caps.has_gpu = False

        mock_net_tracker = MagicMock()
        mock_net_tracker.get_rates.return_value = (0.0, 0.0)

        mock_mem = MagicMock()
        mock_mem.used = 8 * 1024**3
        mock_mem.total = 16 * 1024**3

        with (
            patch(
                "steelseries_oled.stats.psutil.cpu_percent",
                return_value=[],  # Empty list
            ),
            patch(
                "steelseries_oled.stats.psutil.virtual_memory",
                return_value=mock_mem,
            ),
        ):
            # Should not raise ZeroDivisionError
            stats = _gather_stats(mock_caps, mock_net_tracker)
            assert stats.cpu_percent == 0.0
            assert stats.cpu_max_core == 0.0

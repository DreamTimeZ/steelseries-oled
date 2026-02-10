"""Tests for models module."""

import pytest

from steelseries_oled.models import SystemStats, format_rate


class TestFormatRate:
    """Tests for format_rate function."""

    # === Boundary tests (Fix 4 verification) ===

    def test_boundary_below_k_threshold(self) -> None:
        """Values below 999.5 should display as bytes."""
        assert format_rate(999.4) == "999B"
        assert format_rate(999.0) == "999B"
        assert format_rate(0.0) == "0B"

    def test_boundary_at_k_threshold(self) -> None:
        """Values at 999.5 should transition to K (prevents '1000B')."""
        # 999.5 / 1000 = 0.9995 → rounds to 1
        assert format_rate(999.5) == "1K"

    def test_boundary_below_m_threshold(self) -> None:
        """Values below 999_500 should display as K."""
        assert format_rate(999_499) == "999K"
        assert format_rate(500_000) == "500K"

    def test_boundary_at_m_threshold(self) -> None:
        """Values at 999_500 should transition to M (prevents '1000K')."""
        # 999_500 / 1_000_000 = 0.9995 → rounds to 1.0
        assert format_rate(999_500) == "1.0M"

    # === Normal range tests ===

    def test_bytes_range(self) -> None:
        """Test byte-range formatting."""
        assert format_rate(0) == "0B"
        assert format_rate(1) == "1B"
        assert format_rate(500) == "500B"
        assert format_rate(999) == "999B"

    def test_kilobytes_range(self) -> None:
        """Test kilobyte-range formatting."""
        assert format_rate(1_000) == "1K"
        assert format_rate(1_500) == "2K"  # Rounds up
        assert format_rate(50_000) == "50K"
        assert format_rate(999_000) == "999K"

    def test_megabytes_range(self) -> None:
        """Test megabyte-range formatting."""
        assert format_rate(1_000_000) == "1.0M"
        assert format_rate(1_500_000) == "1.5M"
        assert format_rate(10_000_000) == "10.0M"
        assert format_rate(999_000_000) == "999.0M"

    # === Edge cases ===

    def test_negative_value(self) -> None:
        """Negative values should format (though unusual for network rates)."""
        # Current behavior: formats as negative bytes
        result = format_rate(-100)
        assert result == "-100B"

    def test_very_large_value(self) -> None:
        """Very large values stay in M range."""
        # 1 GB/s - edge case for gigabit+ networks
        result = format_rate(1_000_000_000)
        assert result == "1000.0M"  # No G tier exists


class TestSystemStats:
    """Tests for SystemStats dataclass."""

    def test_frozen(self) -> None:
        """SystemStats should be immutable."""
        stats = SystemStats(
            cpu_percent=50.0,

            mem_used_gb=8.0,
            mem_total_gb=16.0,
            net_up_bytes=1000.0,
            net_down_bytes=2000.0,
        )
        with pytest.raises(AttributeError):
            stats.cpu_percent = 99.0  # type: ignore[misc]

    def test_mem_percent_calculation(self) -> None:
        """mem_percent should calculate usage percentage."""
        stats = SystemStats(
            cpu_percent=50.0,

            mem_used_gb=8.0,
            mem_total_gb=16.0,
            net_up_bytes=0.0,
            net_down_bytes=0.0,
        )
        assert stats.mem_percent == 50.0

    def test_mem_percent_zero_total(self) -> None:
        """mem_percent should return 0 if total is zero."""
        stats = SystemStats(
            cpu_percent=50.0,

            mem_used_gb=8.0,
            mem_total_gb=0.0,
            net_up_bytes=0.0,
            net_down_bytes=0.0,
        )
        assert stats.mem_percent == 0.0

    def test_mem_percent_negative_total(self) -> None:
        """mem_percent should return 0 if total is negative (corrupted data)."""
        stats = SystemStats(
            cpu_percent=50.0,

            mem_used_gb=8.0,
            mem_total_gb=-16.0,
            net_up_bytes=0.0,
            net_down_bytes=0.0,
        )
        assert stats.mem_percent == 0.0

    def test_optional_fields_default_none(self) -> None:
        """Optional fields should default to None."""
        stats = SystemStats(
            cpu_percent=50.0,

            mem_used_gb=8.0,
            mem_total_gb=16.0,
            net_up_bytes=0.0,
            net_down_bytes=0.0,
        )
        assert stats.cpu_temp is None
        assert stats.gpu_percent is None
        assert stats.gpu_temp is None

    def test_optional_fields_can_be_set(self) -> None:
        """Optional fields should accept values."""
        stats = SystemStats(
            cpu_percent=50.0,

            mem_used_gb=8.0,
            mem_total_gb=16.0,
            net_up_bytes=0.0,
            net_down_bytes=0.0,
            cpu_temp=65.0,
            gpu_percent=80.0,
            gpu_temp=70.0,
        )
        assert stats.cpu_temp == 65.0
        assert stats.gpu_percent == 80.0
        assert stats.gpu_temp == 70.0

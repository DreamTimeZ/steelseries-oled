"""Tests for constants module."""

from steelseries_oled.constants import (
    INTERFACE_ORDER,
    OLED_HEIGHT,
    OLED_IMAGE_BYTES,
    OLED_REPORT_SIZE,
    OLED_WIDTH,
    PROFILE_REPORT_SIZE,
    REPORT_ID_OLED,
    REPORT_ID_PROFILE,
    SUPPORTED_PIDS,
    VENDOR_ID,
)


def test_vendor_id() -> None:
    """Vendor ID should be SteelSeries."""
    assert VENDOR_ID == 0x1038


def test_supported_pids_not_empty() -> None:
    """Should have at least one supported device."""
    assert len(SUPPORTED_PIDS) > 0


def test_supported_pids_are_valid() -> None:
    """All PIDs should be valid 16-bit values."""
    for pid in SUPPORTED_PIDS:
        assert 0 < pid <= 0xFFFF


def test_interface_order() -> None:
    """Interface order should try legacy first, then Gen 3."""
    assert INTERFACE_ORDER == (1, 2, 0)


def test_oled_dimensions() -> None:
    """OLED should be 128x40 pixels."""
    assert OLED_WIDTH == 128
    assert OLED_HEIGHT == 40


def test_oled_image_bytes() -> None:
    """1-bit image should be 640 bytes."""
    expected = OLED_WIDTH * OLED_HEIGHT // 8
    assert expected == OLED_IMAGE_BYTES
    assert OLED_IMAGE_BYTES == 640


def test_oled_report_size() -> None:
    """OLED report should be 642 bytes."""
    # Report ID + Image + Padding
    expected = 1 + OLED_IMAGE_BYTES + 1
    assert expected == OLED_REPORT_SIZE
    assert OLED_REPORT_SIZE == 642


def test_profile_report_size() -> None:
    """Profile report should be 79 bytes."""
    # Report ID + 16-byte int + 62 padding
    assert PROFILE_REPORT_SIZE == 1 + 16 + 62
    assert PROFILE_REPORT_SIZE == 79


def test_report_ids() -> None:
    """Report IDs should be correct."""
    assert REPORT_ID_OLED == 0x61
    assert REPORT_ID_PROFILE == 0x89

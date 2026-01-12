"""Tests for device module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from steelseries_oled.constants import (
    OLED_IMAGE_BYTES,
    REPORT_ID_OLED,
    REPORT_ID_PROFILE,
)
from steelseries_oled.device import SteelSeriesDevice, find_device
from steelseries_oled.exceptions import DeviceCommunicationError, DeviceNotFoundError


class TestFindDevice:
    """Tests for find_device function."""

    def test_find_device_success(self, mock_device_info: dict) -> None:
        """Should return device info when found."""
        with patch(
            "steelseries_oled.device.hid.enumerate", return_value=[mock_device_info]
        ):
            result = find_device()
            assert result["product_id"] == 0x1612

    def test_find_device_not_found(self) -> None:
        """Should raise DeviceNotFoundError when no device."""
        with (
            patch("steelseries_oled.device.hid.enumerate", return_value=[]),
            pytest.raises(DeviceNotFoundError),
        ):
            find_device()

    def test_find_device_wrong_pid(self) -> None:
        """Should skip devices with unsupported PIDs."""
        wrong_device = {
            "product_id": 0x9999,
            "interface_number": 1,
            "path": b"test",
        }
        with (
            patch("steelseries_oled.device.hid.enumerate", return_value=[wrong_device]),
            pytest.raises(DeviceNotFoundError),
        ):
            find_device()


class TestSteelSeriesDevice:
    """Tests for SteelSeriesDevice class."""

    def test_context_manager_opens_device(
        self, mock_device_info: dict, mock_hid_device: MagicMock
    ) -> None:
        """Context manager should open device on enter."""
        with (
            patch(
                "steelseries_oled.device.hid.enumerate", return_value=[mock_device_info]
            ),
            patch("steelseries_oled.device.hid.device", return_value=mock_hid_device),
        ):
            with SteelSeriesDevice(blank_on_exit=False):
                mock_hid_device.open_path.assert_called_once_with(
                    mock_device_info["path"]
                )

    def test_context_manager_closes_device(
        self, mock_device_info: dict, mock_hid_device: MagicMock
    ) -> None:
        """Context manager should close device on exit."""
        with (
            patch(
                "steelseries_oled.device.hid.enumerate", return_value=[mock_device_info]
            ),
            patch("steelseries_oled.device.hid.device", return_value=mock_hid_device),
        ):
            with SteelSeriesDevice(blank_on_exit=False):
                pass
            mock_hid_device.close.assert_called_once()

    def test_blank_on_exit(
        self, mock_device_info: dict, mock_hid_device: MagicMock
    ) -> None:
        """Should blank screen when blank_on_exit is True."""
        with (
            patch(
                "steelseries_oled.device.hid.enumerate", return_value=[mock_device_info]
            ),
            patch("steelseries_oled.device.hid.device", return_value=mock_hid_device),
        ):
            with SteelSeriesDevice(blank_on_exit=True):
                pass

            # Verify blank screen was sent
            calls = mock_hid_device.send_feature_report.call_args_list
            assert len(calls) == 1
            report = calls[0][0][0]
            assert report[0] == REPORT_ID_OLED
            assert all(b == 0 for b in report[1:])

    def test_send_image_valid(
        self, mock_device_info: dict, mock_hid_device: MagicMock
    ) -> None:
        """Should send valid image data."""
        image_data = bytes([0xFF] * OLED_IMAGE_BYTES)

        with (
            patch(
                "steelseries_oled.device.hid.enumerate", return_value=[mock_device_info]
            ),
            patch("steelseries_oled.device.hid.device", return_value=mock_hid_device),
        ):
            with SteelSeriesDevice(blank_on_exit=False) as device:
                device.send_image(image_data)

            calls = mock_hid_device.send_feature_report.call_args_list
            assert len(calls) == 1
            report = calls[0][0][0]
            assert report[0] == REPORT_ID_OLED
            assert bytes(report[1:-1]) == image_data
            assert report[-1] == 0x00

    def test_send_image_wrong_size(
        self, mock_device_info: dict, mock_hid_device: MagicMock
    ) -> None:
        """Should raise ValueError for wrong image size."""
        with (
            patch(
                "steelseries_oled.device.hid.enumerate", return_value=[mock_device_info]
            ),
            patch("steelseries_oled.device.hid.device", return_value=mock_hid_device),
        ):
            with SteelSeriesDevice(blank_on_exit=False) as device:
                with pytest.raises(ValueError, match="exactly 640 bytes"):
                    device.send_image(bytes([0xFF] * 100))

    def test_set_profile(
        self, mock_device_info: dict, mock_hid_device: MagicMock
    ) -> None:
        """Should send profile switch command."""
        with (
            patch(
                "steelseries_oled.device.hid.enumerate", return_value=[mock_device_info]
            ),
            patch("steelseries_oled.device.hid.device", return_value=mock_hid_device),
        ):
            with SteelSeriesDevice(blank_on_exit=False) as device:
                device.set_profile(3)

            calls = mock_hid_device.send_feature_report.call_args_list
            assert len(calls) == 1
            report = calls[0][0][0]
            assert report[0] == REPORT_ID_PROFILE
            assert len(report) == 79

    def test_set_profile_little_endian(
        self, mock_device_info: dict, mock_hid_device: MagicMock
    ) -> None:
        """Profile number should be encoded as little-endian (Fix 3 verification)."""
        with (
            patch(
                "steelseries_oled.device.hid.enumerate", return_value=[mock_device_info]
            ),
            patch("steelseries_oled.device.hid.device", return_value=mock_hid_device),
        ):
            with SteelSeriesDevice(blank_on_exit=False) as device:
                device.set_profile(0x0102)  # Use multi-byte value to verify endianness

            calls = mock_hid_device.send_feature_report.call_args_list
            report = calls[0][0][0]
            # Bytes 1-16 contain the profile number as 16-byte little-endian
            profile_bytes = bytes(report[1:17])
            # Little-endian: least significant byte first
            # 0x0102 as 16-byte little-endian: 02 01 00 ... (14 zero bytes)
            expected = (0x0102).to_bytes(16, "little")
            assert profile_bytes == expected

    def test_send_when_not_opened(self) -> None:
        """Should raise error when device not opened."""
        device = SteelSeriesDevice()
        with pytest.raises(DeviceCommunicationError, match="not opened"):
            device.send_image(bytes([0xFF] * OLED_IMAGE_BYTES))

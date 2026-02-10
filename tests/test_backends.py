"""Tests for backends module."""

from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from steelseries_oled.backends import BackendType, create_backend, detect_best_backend
from steelseries_oled.backends.hid_gen3 import HIDGen3Backend
from steelseries_oled.exceptions import DeviceCommunicationError
from steelseries_oled.models import SystemStats


class TestBackendFactory:
    """Tests for backend factory functions."""

    def test_detect_best_backend_gen3(self) -> None:
        """Should return HID_GEN3 for Gen3 keyboards."""
        with patch("steelseries_oled.backends.is_gen3_device", return_value=True):
            result = detect_best_backend()
            assert result == BackendType.HID_GEN3

    def test_detect_best_backend_legacy_with_gamesense(self) -> None:
        """Should return GAMESENSE for legacy keyboards when GG available."""
        with (
            patch("steelseries_oled.backends.is_gen3_device", return_value=False),
            patch(
                "steelseries_oled.backends.is_gamesense_available", return_value=True
            ),
        ):
            result = detect_best_backend()
            assert result == BackendType.GAMESENSE

    def test_detect_best_backend_legacy_no_gamesense(self) -> None:
        """Should return HID for legacy keyboards when GG not available."""
        with (
            patch("steelseries_oled.backends.is_gen3_device", return_value=False),
            patch(
                "steelseries_oled.backends.is_gamesense_available", return_value=False
            ),
        ):
            result = detect_best_backend()
            assert result == BackendType.HID

    def test_create_backend_gamesense(self) -> None:
        """Should create GameSenseBackend for GAMESENSE type."""
        from steelseries_oled.backends.gamesense import GameSenseBackend

        backend = create_backend(BackendType.GAMESENSE)
        assert isinstance(backend, GameSenseBackend)

    def test_create_backend_hid(self) -> None:
        """Should create HIDBitmapBackend for HID type."""
        from steelseries_oled.backends.hid import HIDBitmapBackend

        backend = create_backend(BackendType.HID)
        assert isinstance(backend, HIDBitmapBackend)

    def test_create_backend_hid_gen3(self) -> None:
        """Should create HIDGen3Backend for HID_GEN3 type."""
        backend = create_backend(BackendType.HID_GEN3)
        assert isinstance(backend, HIDGen3Backend)


class TestHIDGen3Backend:
    """Tests for HIDGen3Backend class."""

    @pytest.fixture
    def mock_gen3_device_info(self) -> dict:
        """Create mock Gen3 device info."""
        return {
            "product_id": 0x1642,  # Apex Pro TKL Gen 3
            "interface_number": 1,
            "path": b"\\\\?\\HID#VID_1038&PID_1642",
        }

    @pytest.fixture
    def mock_hid_device(self) -> MagicMock:
        """Create mock hid.device."""
        device = MagicMock()
        device.open_path = MagicMock()
        device.close = MagicMock()
        device.send_feature_report = MagicMock(return_value=645)  # Success
        return device

    @pytest.fixture
    def sample_stats(self) -> SystemStats:
        """Create sample SystemStats for testing."""
        return SystemStats(
            cpu_percent=50.0,
            mem_used_gb=8.0,
            mem_total_gb=16.0,
            net_up_bytes=1000.0,
            net_down_bytes=5000.0,
        )

    # === Fix 1 verification: Failure handling ===

    def test_update_stats_raises_on_send_failure(
        self,
        mock_gen3_device_info: dict,
        mock_hid_device: MagicMock,
        sample_stats: SystemStats,
    ) -> None:
        """update_stats should raise DeviceCommunicationError on send failure."""
        mock_hid_device.send_feature_report.return_value = -1  # Failure

        mock_hid_module = MagicMock()
        mock_hid_module.enumerate.return_value = [mock_gen3_device_info]
        mock_hid_module.device.return_value = mock_hid_device

        with patch.dict("sys.modules", {"hid": mock_hid_module}):
            backend = HIDGen3Backend()
            backend.__enter__()
            try:
                with pytest.raises(
                    DeviceCommunicationError, match="Failed to send bitmap"
                ):
                    backend.update_stats(sample_stats)
            finally:
                # Cleanup without raising (send_feature_report still returns -1)
                mock_hid_device.send_feature_report.return_value = 645
                backend.__exit__(None, None, None)

    def test_update_stats_raises_on_oserror(
        self,
        mock_gen3_device_info: dict,
        mock_hid_device: MagicMock,
        sample_stats: SystemStats,
    ) -> None:
        """update_stats should raise DeviceCommunicationError on OSError."""
        mock_hid_device.send_feature_report.side_effect = OSError("Device disconnected")

        mock_hid_module = MagicMock()
        mock_hid_module.enumerate.return_value = [mock_gen3_device_info]
        mock_hid_module.device.return_value = mock_hid_device

        with patch.dict("sys.modules", {"hid": mock_hid_module}):
            backend = HIDGen3Backend()
            backend.__enter__()
            try:
                with pytest.raises(
                    DeviceCommunicationError, match="Failed to send bitmap"
                ):
                    backend.update_stats(sample_stats)
            finally:
                mock_hid_device.send_feature_report.side_effect = None
                mock_hid_device.send_feature_report.return_value = 645
                backend.__exit__(None, None, None)

    def test_send_image_raises_on_failure(
        self,
        mock_gen3_device_info: dict,
        mock_hid_device: MagicMock,
    ) -> None:
        """send_image should raise DeviceCommunicationError on send failure."""
        mock_hid_device.send_feature_report.return_value = -1  # Failure
        test_image = Image.new("1", (128, 40), color=1)

        mock_hid_module = MagicMock()
        mock_hid_module.enumerate.return_value = [mock_gen3_device_info]
        mock_hid_module.device.return_value = mock_hid_device

        with patch.dict("sys.modules", {"hid": mock_hid_module}):
            backend = HIDGen3Backend()
            backend.__enter__()
            try:
                with pytest.raises(
                    DeviceCommunicationError, match="Failed to send bitmap"
                ):
                    backend.send_image(test_image)
            finally:
                mock_hid_device.send_feature_report.return_value = 645
                backend.__exit__(None, None, None)

    def test_update_stats_raises_when_not_initialized(
        self, sample_stats: SystemStats
    ) -> None:
        """update_stats should raise when backend not initialized."""
        backend = HIDGen3Backend()
        with pytest.raises(DeviceCommunicationError, match="not initialized"):
            backend.update_stats(sample_stats)

    # === Normal operation tests ===

    def test_update_stats_success(
        self,
        mock_gen3_device_info: dict,
        mock_hid_device: MagicMock,
        sample_stats: SystemStats,
    ) -> None:
        """update_stats should succeed when send works."""
        mock_hid_module = MagicMock()
        mock_hid_module.enumerate.return_value = [mock_gen3_device_info]
        mock_hid_module.device.return_value = mock_hid_device

        with patch.dict("sys.modules", {"hid": mock_hid_module}):
            with HIDGen3Backend() as backend:
                # Should not raise
                backend.update_stats(sample_stats)

            # Verify send was called (at least once for stats, once for clear on exit)
            assert mock_hid_device.send_feature_report.called

    def test_backend_name(self) -> None:
        """Backend should report correct name."""
        backend = HIDGen3Backend()
        assert backend.name == "HID-Gen3"


class TestHIDGen3BitmapConversion:
    """Tests for Gen3 bitmap format conversion."""

    def test_image_to_gen3_bitmap_size(self) -> None:
        """Converted bitmap should be exactly 640 bytes."""
        backend = HIDGen3Backend()
        image = Image.new("1", (128, 40), color=0)
        bitmap = backend._image_to_gen3_bitmap(image)
        assert len(bitmap) == 640

    def test_image_to_gen3_bitmap_all_black(self) -> None:
        """All-black image should produce all-zero bitmap."""
        backend = HIDGen3Backend()
        image = Image.new("1", (128, 40), color=0)
        bitmap = backend._image_to_gen3_bitmap(image)
        assert all(b == 0 for b in bitmap)

    def test_image_to_gen3_bitmap_all_white(self) -> None:
        """All-white image should produce all-0xFF bitmap."""
        backend = HIDGen3Backend()
        image = Image.new("1", (128, 40), color=1)
        bitmap = backend._image_to_gen3_bitmap(image)
        assert all(b == 0xFF for b in bitmap)

    def test_image_to_gen3_bitmap_top_left_pixel(self) -> None:
        """Single pixel at (0,0) should set bit 0 of byte 0."""
        backend = HIDGen3Backend()
        image = Image.new("1", (128, 40), color=0)
        image.putpixel((0, 0), 1)
        bitmap = backend._image_to_gen3_bitmap(image)
        assert bitmap[0] == 0x01  # Bit 0 set
        assert all(b == 0 for b in bitmap[1:])

    def test_image_to_gen3_bitmap_resizes_if_needed(self) -> None:
        """Should resize non-128x40 images."""
        backend = HIDGen3Backend()
        image = Image.new("1", (256, 80), color=1)  # 2x size
        bitmap = backend._image_to_gen3_bitmap(image)
        assert len(bitmap) == 640

    def test_image_to_gen3_bitmap_converts_mode(self) -> None:
        """Should convert non-1-bit images."""
        backend = HIDGen3Backend()
        image = Image.new("RGB", (128, 40), color=(255, 255, 255))
        bitmap = backend._image_to_gen3_bitmap(image)
        assert len(bitmap) == 640


class TestHIDBitmapBackend:
    """Tests for HIDBitmapBackend class."""

    def test_render_frame_returns_640_bytes(self) -> None:
        """Rendered frame should be exactly 640 bytes."""
        from steelseries_oled.backends.hid import HIDBitmapBackend

        backend = HIDBitmapBackend()
        # Load font manually for testing without device
        backend._font = backend._load_font()

        stats = SystemStats(
            cpu_percent=50.0,
            mem_used_gb=8.0,
            mem_total_gb=16.0,
            net_up_bytes=1000.0,
            net_down_bytes=5000.0,
        )

        frame = backend._render_frame(stats)
        assert len(frame) == 640

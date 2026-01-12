"""Tests for profile module."""

from unittest.mock import MagicMock, patch

import pytest

from steelseries_oled.constants import GEN3_PIDS
from steelseries_oled.exceptions import Gen3NotSupportedError
from steelseries_oled.profile import switch_profile


class TestSwitchProfile:
    """Tests for switch_profile function."""

    def test_success(self) -> None:
        """Should call device.set_profile with correct number."""
        mock_device = MagicMock()
        mock_device_info = {"product_id": 0x1612, "path": b"test"}

        with (
            patch(
                "steelseries_oled.profile.find_device", return_value=mock_device_info
            ),
            patch("steelseries_oled.profile.open_device") as mock_open,
        ):
            mock_open.return_value.__enter__ = MagicMock(return_value=mock_device)
            mock_open.return_value.__exit__ = MagicMock(return_value=False)

            switch_profile(3)

            mock_device.set_profile.assert_called_once_with(3)

    def test_rejects_gen3(self) -> None:
        """Should raise Gen3NotSupportedError for Gen3 keyboards."""
        gen3_pid = next(iter(GEN3_PIDS))
        mock_device_info = {"product_id": gen3_pid, "path": b"test"}

        with (
            patch(
                "steelseries_oled.profile.find_device", return_value=mock_device_info
            ),
            pytest.raises(Gen3NotSupportedError),
        ):
            switch_profile(1)

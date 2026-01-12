"""Pytest configuration and fixtures."""

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_device_info() -> dict:
    """Create mock device info dictionary (hidapi format)."""
    return {
        "product_id": 0x1612,  # Apex 7
        "interface_number": 1,
        "path": b"\\\\?\\HID#VID_1038&PID_1612",
        "product_string": "Apex 7",
    }


@pytest.fixture
def mock_hid_device() -> MagicMock:
    """Create a mock hid.device object."""
    device = MagicMock()
    device.open_path = MagicMock()
    device.close = MagicMock()
    device.send_feature_report = MagicMock(return_value=1)  # Any positive = success
    return device

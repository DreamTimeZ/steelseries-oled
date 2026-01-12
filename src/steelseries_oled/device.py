"""Device detection and management for SteelSeries keyboards."""

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Self

import hid

from steelseries_oled.constants import (
    GEN3_PIDS,
    INTERFACE_ORDER,
    OLED_IMAGE_BYTES,
    REPORT_ID_OLED,
    REPORT_ID_PROFILE,
    SUPPORTED_PIDS,
    VENDOR_ID,
)
from steelseries_oled.exceptions import DeviceCommunicationError, DeviceNotFoundError

if TYPE_CHECKING:
    from collections.abc import Generator


def enumerate_steelseries_devices() -> list[dict[str, Any]]:
    """Enumerate all SteelSeries HID devices.

    Returns:
        List of device info dictionaries from hidapi.
    """
    return [
        dev
        for dev in hid.enumerate(VENDOR_ID, 0)
        if dev["product_id"] in SUPPORTED_PIDS
    ]


def find_device_info() -> dict[str, Any]:
    """Find a compatible SteelSeries keyboard.

    Searches through USB HID devices to find a SteelSeries keyboard
    with an OLED display.

    Returns:
        Device info dictionary from hidapi.

    Raises:
        DeviceNotFoundError: If no compatible device is found.
    """
    for interface in INTERFACE_ORDER:
        devices: list[dict[str, Any]] = hid.enumerate(VENDOR_ID, 0)
        for dev_info in devices:
            if dev_info["product_id"] not in SUPPORTED_PIDS:
                continue
            if dev_info["interface_number"] != interface:
                continue
            return dev_info

    raise DeviceNotFoundError


# Backwards compatibility alias
def find_device() -> dict[str, Any]:
    """Find a compatible SteelSeries keyboard.

    Deprecated: Use find_device_info() instead.

    Returns:
        Device info dictionary from hidapi.

    Raises:
        DeviceNotFoundError: If no compatible device is found.
    """
    return find_device_info()


def is_gen3_device() -> bool:
    """Check if the connected keyboard is a Gen3 model.

    Gen3 keyboards do not support direct HID bitmap commands.
    Use GameSense text mode instead.

    Returns:
        True if a Gen3 keyboard is detected, False otherwise.
    """
    try:
        device_info = find_device_info()
        return device_info["product_id"] in GEN3_PIDS
    except DeviceNotFoundError:
        return False


def get_device_name(product_id: int) -> str:
    """Get the human-readable name for a device.

    Args:
        product_id: The USB product ID.

    Returns:
        The device name or "Unknown" if not recognized.
    """
    names = {
        0x1610: "Apex Pro",
        0x1612: "Apex 7",
        0x1614: "Apex Pro TKL",
        0x1618: "Apex 7 TKL",
        0x161C: "Apex 5",
        0x1628: "Apex Pro TKL (2023)",
        0x1642: "Apex Pro TKL Gen 3",
        0x1644: "Apex Pro TKL Wireless Gen 3",
    }
    return names.get(product_id, f"Unknown (0x{product_id:04X})")


class SteelSeriesDevice:
    """Context manager for SteelSeries keyboard communication.

    Handles device lifecycle including opening, closing, and
    blanking the screen on exit.

    Example:
        with SteelSeriesDevice() as device:
            device.send_image(image_bytes)
    """

    def __init__(self, blank_on_exit: bool = True) -> None:
        """Initialize the device wrapper.

        Args:
            blank_on_exit: Whether to blank the screen when closing.
        """
        self._device: hid.device | None = None
        self._device_info: dict[str, Any] | None = None
        self._blank_on_exit = blank_on_exit

    def __enter__(self) -> Self:
        """Open connection to the device."""
        self._device_info = find_device_info()
        self._device = hid.device()
        try:
            self._device.open_path(self._device_info["path"])
        except OSError as e:
            self._device = None
            msg = f"Failed to open device: {e}"
            raise DeviceCommunicationError(msg) from e
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Close connection and optionally blank screen."""
        if self._device is not None:
            try:
                if self._blank_on_exit:
                    self.blank_screen()
            finally:
                self._device.close()
                self._device = None

    @property
    def product_id(self) -> int | None:
        """Get the product ID of the connected device."""
        if self._device_info is None:
            return None
        return self._device_info.get("product_id")

    @property
    def product_name(self) -> str:
        """Get the product name of the connected device."""
        if self._device_info is None:
            return "Unknown"
        return get_device_name(self._device_info.get("product_id", 0))

    @property
    def is_gen3(self) -> bool:
        """Check if this is a Gen3 device."""
        pid = self.product_id
        return pid is not None and pid in GEN3_PIDS

    def send_image(self, image_data: bytes) -> None:
        """Send image data to the OLED display.

        Args:
            image_data: 640 bytes of 1-bit packed image data (128x40 pixels).

        Raises:
            DeviceCommunicationError: If sending fails.
            ValueError: If image_data is not exactly 640 bytes.
        """
        if len(image_data) != OLED_IMAGE_BYTES:
            msg = (
                f"Image data must be exactly {OLED_IMAGE_BYTES} bytes, "
                f"got {len(image_data)}"
            )
            raise ValueError(msg)

        report = bytes([REPORT_ID_OLED]) + image_data + bytes([0x00])
        self._send_feature_report(report)

    def blank_screen(self) -> None:
        """Clear the OLED display to black."""
        report = bytes([REPORT_ID_OLED]) + bytes(OLED_IMAGE_BYTES) + bytes([0x00])
        self._send_feature_report(report)

    def set_profile(self, profile_number: int) -> None:
        """Switch keyboard profile.

        Args:
            profile_number: The profile number to switch to.

        Raises:
            DeviceCommunicationError: If sending fails.
        """
        # USB HID convention is little-endian; use explicit endianness for portability
        profile_bytes = profile_number.to_bytes(16, "little")
        report = bytes([REPORT_ID_PROFILE]) + profile_bytes + bytes(62)
        self._send_feature_report(report)

    def _send_feature_report(self, data: bytes) -> None:
        """Send a feature report to the device.

        Args:
            data: The report data to send.

        Raises:
            DeviceCommunicationError: If sending fails or report is rejected.
        """
        if self._device is None:
            msg = "Device not opened"
            raise DeviceCommunicationError(msg)
        try:
            result = self._device.send_feature_report(data)
            if result < 0:
                msg = f"Feature report rejected by device (result={result})"
                raise DeviceCommunicationError(msg)
        except OSError as e:
            msg = f"Failed to send feature report: {e}"
            raise DeviceCommunicationError(msg) from e


@contextmanager
def open_device(blank_on_exit: bool = True) -> Generator[SteelSeriesDevice]:
    """Context manager for opening a SteelSeries device.

    Args:
        blank_on_exit: Whether to blank the screen when closing.

    Yields:
        An opened SteelSeriesDevice instance.

    Example:
        with open_device() as device:
            device.send_image(image_bytes)
    """
    device = SteelSeriesDevice(blank_on_exit=blank_on_exit)
    with device:
        yield device

"""Custom exceptions for SteelSeries OLED."""


class SteelSeriesError(Exception):
    """Base exception for SteelSeries OLED errors."""


class DeviceNotFoundError(SteelSeriesError):
    """Raised when no compatible SteelSeries device is found."""

    def __init__(self, message: str = "No compatible SteelSeries device found") -> None:
        super().__init__(message)


class DeviceCommunicationError(SteelSeriesError):
    """Raised when communication with the device fails."""


class ImageError(SteelSeriesError):
    """Raised when image processing fails."""


class Gen3NotSupportedError(SteelSeriesError):
    """Raised when attempting unsupported operations on Gen3 keyboards.

    Gen3 keyboards (Apex Pro Gen 3, Apex Pro TKL Gen 3) do not support
    direct HID bitmap commands. Use GameSense text mode for stats display.
    """

    def __init__(
        self,
        message: str = (
            "Gen3 keyboards do not support image/GIF display via HID. "
            "Use 'steelseries stats' for system stats display, which works on Gen3."
        ),
    ) -> None:
        super().__init__(message)

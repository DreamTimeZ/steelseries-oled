"""SteelSeries OLED - Display GIFs and stats on keyboard OLED screens.

This package provides tools for controlling the OLED display on
SteelSeries Apex series keyboards.

Example:
    from steelseries_oled import open_device

    with open_device() as device:
        device.send_image(image_bytes)
        device.blank_screen()
"""

from steelseries_oled.constants import (
    OLED_HEIGHT,
    OLED_WIDTH,
    SUPPORTED_PIDS,
    VENDOR_ID,
)
from steelseries_oled.device import (
    SteelSeriesDevice,
    find_device,
    open_device,
)
from steelseries_oled.display import display_image, load_frames
from steelseries_oled.exceptions import (
    DeviceCommunicationError,
    DeviceNotFoundError,
    Gen3NotSupportedError,
    ImageError,
    SteelSeriesError,
)
from steelseries_oled.profile import switch_profile
from steelseries_oled.stats import display_stats

__version__ = "1.0.0"

__all__ = [
    "OLED_HEIGHT",
    "OLED_WIDTH",
    "SUPPORTED_PIDS",
    "VENDOR_ID",
    "DeviceCommunicationError",
    "DeviceNotFoundError",
    "Gen3NotSupportedError",
    "ImageError",
    "SteelSeriesDevice",
    "SteelSeriesError",
    "__version__",
    "display_image",
    "display_stats",
    "find_device",
    "load_frames",
    "open_device",
    "switch_profile",
]

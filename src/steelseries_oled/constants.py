"""Constants for SteelSeries OLED communication."""

from typing import Final

# SteelSeries USB Vendor ID
VENDOR_ID: Final[int] = 0x1038

# Supported Product IDs for keyboards with 128x40 OLED displays
SUPPORTED_PIDS: Final[tuple[int, ...]] = (
    0x1610,  # Apex Pro
    0x1612,  # Apex 7
    0x1614,  # Apex Pro TKL
    0x1618,  # Apex 7 TKL
    0x161C,  # Apex 5
    0x1628,  # Apex Pro TKL (2023)
    0x1642,  # Apex Pro TKL Gen 3
    0x1644,  # Apex Pro TKL Wireless Gen 3
)

# Gen3 keyboards - use HIDGen3Backend (reverse-engineered protocol)
GEN3_PIDS: Final[tuple[int, ...]] = (
    0x1642,  # Apex Pro TKL Gen 3
    0x1644,  # Apex Pro TKL Wireless Gen 3
)

# HID interface order to try (legacy and Gen3 both use interface 1)
INTERFACE_ORDER: Final[tuple[int, ...]] = (1, 2, 0)

# OLED display dimensions
OLED_WIDTH: Final[int] = 128
OLED_HEIGHT: Final[int] = 40

# HID Report IDs
REPORT_ID_OLED: Final[int] = 0x61
REPORT_ID_PROFILE: Final[int] = 0x89

# Report sizes (in bytes)
OLED_IMAGE_BYTES: Final[int] = OLED_WIDTH * OLED_HEIGHT // 8  # 640 bytes
OLED_REPORT_SIZE: Final[int] = 1 + OLED_IMAGE_BYTES + 1  # 642 bytes
PROFILE_REPORT_SIZE: Final[int] = 1 + 16 + 62  # 79 bytes

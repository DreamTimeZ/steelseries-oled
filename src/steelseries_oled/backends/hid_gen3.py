"""Direct HID backend for Gen3 keyboards.

Reverse-engineered protocol for Apex Pro TKL Gen 3 and similar.
Works WITHOUT SteelSeries GG software running.

Protocol:
- Interface 1 (Usage Page 0xFFC0)
- Feature Report, Report ID 0x00
- Payload: 644 bytes
  - Header: 0x1f 0x81 (custom bitmap mode)
  - Bitmap: 640 bytes (SSD1306-style layout)
  - Padding: 2 bytes

Bitmap Layout (SSD1306-style):
- 128 columns x 40 rows = 5120 pixels
- 5 segment rows x 128 bytes = 640 bytes
- Each byte = 8 vertical pixels (bit 0 = top, bit 7 = bottom)
"""

import contextlib
import logging
from importlib.resources import as_file, files
from pathlib import Path
from types import TracebackType
from typing import Any, Self

from PIL import Image, ImageDraw, ImageFont
from PIL.ImageFont import FreeTypeFont

from steelseries_oled.backends.base import StatsBackend
from steelseries_oled.constants import GEN3_PIDS, OLED_HEIGHT, OLED_WIDTH, VENDOR_ID
from steelseries_oled.exceptions import DeviceCommunicationError, DeviceNotFoundError
from steelseries_oled.models import SystemStats, format_rate

logger = logging.getLogger(__name__)

# Gen3 protocol constants
GEN3_HEADER = bytes([0x1F, 0x81])  # Custom bitmap mode
GEN3_PAYLOAD_SIZE = 644
GEN3_BITMAP_SIZE = 640
REPORT_ID = 0x00


class HIDGen3Backend(StatsBackend):
    """Direct HID backend for Gen3 keyboards.

    Sends bitmap data directly via USB HID, bypassing SteelSeries GG.
    Uses reverse-engineered protocol discovered through USB capture analysis.
    """

    def __init__(
        self,
        font: FreeTypeFont | None = None,
        font_path: Path | None = None,
        font_size: int = 12,
    ) -> None:
        """Initialize the Gen3 HID backend.

        Args:
            font: Pre-loaded PIL font to use.
            font_path: Path to TrueType font file.
            font_size: Font size if loading from path.
        """
        self._device: Any = None
        self._font: FreeTypeFont | None = font
        self._font_path = font_path
        self._font_size = font_size

    @property
    def name(self) -> str:
        """Return the backend name."""
        return "HID-Gen3"

    def __enter__(self) -> Self:
        """Initialize HID device connection."""
        try:
            import hid  # noqa: PLC0415
        except ImportError as e:
            msg = "hidapi not installed. Run: pip install hidapi"
            raise ImportError(msg) from e

        # Load font if not provided
        if self._font is None:
            self._font = self._load_font()

        # Find Gen3 device
        devices = hid.enumerate(VENDOR_ID)
        target_path = None

        for d in devices:
            if d["product_id"] in GEN3_PIDS and d["interface_number"] == 1:
                target_path = d["path"]
                break

        if target_path is None:
            msg = "Gen3 keyboard not found"
            raise DeviceNotFoundError(msg)

        self._device = hid.device()
        try:
            self._device.open_path(target_path)
        except OSError as e:
            self._device.close()
            self._device = None
            msg = f"Failed to open Gen3 device: {e}"
            raise DeviceCommunicationError(msg) from e

        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Close HID device connection."""
        if self._device is not None:
            # Clear screen before closing
            self._send_bitmap(bytes(GEN3_BITMAP_SIZE))
            with contextlib.suppress(OSError):
                self._device.close()
            self._device = None

    def update_stats(self, stats: SystemStats) -> None:
        """Update the OLED display with rendered stats bitmap.

        Args:
            stats: System statistics to display.

        Raises:
            DeviceCommunicationError: If sending to device fails.
        """
        if self._device is None:
            msg = "Backend not initialized"
            raise DeviceCommunicationError(msg)

        # Render stats to PIL image
        image = self._render_stats(stats)

        # Convert to Gen3 bitmap format
        bitmap = self._image_to_gen3_bitmap(image)

        # Send to device
        if not self._send_bitmap(bitmap):
            msg = "Failed to send bitmap to device"
            raise DeviceCommunicationError(msg)

    def send_image(self, image: Image.Image) -> None:
        """Send a PIL Image to the OLED.

        Args:
            image: PIL Image (will be converted to 1-bit 128x40)

        Raises:
            DeviceCommunicationError: If sending to device fails.
        """
        if self._device is None:
            msg = "Backend not initialized"
            raise DeviceCommunicationError(msg)

        # Convert to correct format
        if image.size != (OLED_WIDTH, OLED_HEIGHT):
            image = image.resize((OLED_WIDTH, OLED_HEIGHT))
        if image.mode != "1":
            image = image.convert("1")

        bitmap = self._image_to_gen3_bitmap(image)
        if not self._send_bitmap(bitmap):
            msg = "Failed to send bitmap to device"
            raise DeviceCommunicationError(msg)

    def clear(self) -> None:
        """Clear the OLED display."""
        if self._device is None:
            return
        self._send_bitmap(bytes(GEN3_BITMAP_SIZE))

    def _send_bitmap(self, bitmap: bytes) -> bool:
        """Send bitmap data to the device.

        Args:
            bitmap: 640 bytes of bitmap data in SSD1306 format

        Returns:
            True if sent successfully
        """
        if self._device is None:
            return False

        # Ensure exactly 640 bytes
        if len(bitmap) < GEN3_BITMAP_SIZE:
            bitmap = bitmap + bytes(GEN3_BITMAP_SIZE - len(bitmap))
        elif len(bitmap) > GEN3_BITMAP_SIZE:
            bitmap = bitmap[:GEN3_BITMAP_SIZE]

        # Build payload: header + bitmap + padding
        payload = GEN3_HEADER + bitmap + bytes(2)  # 2 + 640 + 2 = 644

        # Build report: report_id + payload
        report = bytes([REPORT_ID]) + payload  # 1 + 644 = 645

        try:
            result: int = self._device.send_feature_report(report)
            return result > 0
        except OSError as e:
            logger.debug("Failed to send bitmap: %s", e)
            return False

    def _image_to_gen3_bitmap(self, image: Image.Image) -> bytes:
        """Convert PIL Image to Gen3 bitmap format.

        Gen3 uses SSD1306-style layout:
        - 5 segment rows x 128 bytes = 640 bytes
        - Each byte = 8 vertical pixels
        - Bit 0 = top of segment, Bit 7 = bottom

        Args:
            image: 128x40 1-bit PIL Image

        Returns:
            640 bytes in Gen3 format
        """
        # Ensure correct format
        if image.size != (OLED_WIDTH, OLED_HEIGHT):
            image = image.resize((OLED_WIDTH, OLED_HEIGHT))
        if image.mode != "1":
            image = image.convert("1")

        # Get pixel data
        pixels = image.load()
        if pixels is None:
            msg = "Failed to load image pixel data"
            raise DeviceCommunicationError(msg)

        # Build bitmap in SSD1306 format
        bitmap = bytearray(GEN3_BITMAP_SIZE)

        for segment_row in range(5):  # 5 segment rows (8 pixels each)
            for x in range(128):  # 128 columns
                byte_val = 0
                for bit in range(8):  # 8 pixels per byte
                    y = segment_row * 8 + bit
                    # Bit 0 = top of segment
                    if y < OLED_HEIGHT and pixels[x, y]:
                        byte_val |= 1 << bit

                byte_index = segment_row * 128 + x
                bitmap[byte_index] = byte_val

        return bytes(bitmap)

    def _render_stats(self, stats: SystemStats) -> Image.Image:
        """Render stats to a PIL Image with adaptive layout.

        Layout (3 lines, 128x40 pixels):
        - Line 1: CPU % [temp] | GPU % [temp]
        - Line 2: RAM used/total GB
        - Line 3: Net up/down rates

        Args:
            stats: System statistics to display.

        Returns:
            128x40 1-bit PIL Image
        """
        image = Image.new("1", (OLED_WIDTH, OLED_HEIGHT), color=0)
        draw = ImageDraw.Draw(image)

        # Line 1: CPU + GPU (adaptive)
        line1_parts = [f"C:{stats.cpu_percent:3.0f}%"]
        if stats.cpu_temp is not None:
            line1_parts.append(f"{stats.cpu_temp:.0f}C")
        if stats.gpu_percent is not None:
            line1_parts.append(f"G:{stats.gpu_percent:.0f}%")
            if stats.gpu_temp is not None:
                line1_parts.append(f"{stats.gpu_temp:.0f}C")
        line1 = " ".join(line1_parts)

        # Line 2: RAM
        line2 = f"RAM:{stats.mem_used_gb:.1f}/{stats.mem_total_gb:.0f}GB"

        # Line 3: Network (download first - users care more about it)
        up = format_rate(stats.net_up_bytes)
        down = format_rate(stats.net_down_bytes)
        line3 = f"D:{down} U:{up}"

        draw.text((0, 0), line1, font=self._font, fill=1)
        draw.text((0, 13), line2, font=self._font, fill=1)
        draw.text((0, 26), line3, font=self._font, fill=1)

        return image

    def _load_font(self) -> FreeTypeFont:
        """Load the font for rendering."""
        if self._font_path is not None:
            return ImageFont.truetype(str(self._font_path), self._font_size)

        # Use bundled font
        font_ref = files("steelseries_oled.assets").joinpath("OpenSans-Regular.ttf")
        with as_file(font_ref) as font_file:
            return ImageFont.truetype(str(font_file), self._font_size)

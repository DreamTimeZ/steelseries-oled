"""Direct HID backend for stats display.

Uses direct USB HID communication to display stats as bitmap.
Works with legacy keyboards (non-Gen3).
"""

from importlib.resources import as_file, files
from pathlib import Path
from types import TracebackType
from typing import Self

from PIL import Image, ImageDraw, ImageFont
from PIL.ImageFont import FreeTypeFont

from steelseries_oled.backends.base import StatsBackend
from steelseries_oled.constants import OLED_HEIGHT, OLED_WIDTH
from steelseries_oled.device import SteelSeriesDevice
from steelseries_oled.exceptions import DeviceCommunicationError
from steelseries_oled.models import SystemStats, build_stats_lines


class HIDBitmapBackend(StatsBackend):
    """Direct HID backend using bitmap rendering.

    Renders stats as a bitmap image and sends via USB HID.
    Only works with legacy keyboards (Apex Pro/7/5, non-Gen3).

    Note:
        Gen3 keyboards (Apex Pro Gen 3, Apex Pro TKL Gen 3) ignore
        HID bitmap commands. Use GameSenseBackend for Gen3.
    """

    def __init__(
        self,
        font: FreeTypeFont | None = None,
        font_path: Path | None = None,
        font_size: int = 12,
    ) -> None:
        """Initialize the HID bitmap backend.

        Args:
            font: Pre-loaded PIL font to use.
            font_path: Path to TrueType font file.
            font_size: Font size if loading from path.
        """
        self._device: SteelSeriesDevice | None = None
        self._font: FreeTypeFont | None = font
        self._font_path = font_path
        self._font_size = font_size

    @property
    def name(self) -> str:
        """Return the backend name."""
        return "HID"

    def __enter__(self) -> Self:
        """Initialize HID device connection."""
        # Load font if not provided
        if self._font is None:
            self._font = self._load_font()

        # Open device using proper context manager protocol
        self._device = SteelSeriesDevice(blank_on_exit=True)
        try:
            self._device.__enter__()
        except BaseException:
            self._device = None
            raise

        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Close HID device connection."""
        if self._device is not None:
            try:
                self._device.__exit__(exc_type, exc_val, exc_tb)
            finally:
                self._device = None

    def update_stats(self, stats: SystemStats) -> None:
        """Update the OLED display with rendered stats bitmap.

        Args:
            stats: System statistics to display.
        """
        if self._device is None:
            msg = "Backend not initialized"
            raise DeviceCommunicationError(msg)

        frame_data = self._render_frame(stats)
        self._device.send_image(frame_data)

    def _render_frame(self, stats: SystemStats) -> bytes:
        """Render stats to a bitmap frame with adaptive layout.

        Layout (3 lines, 128x40 pixels):
        - Line 1: CPU % [temp] | GPU % [temp]
        - Line 2: RAM used/total GB
        - Line 3: Net up/down rates

        Returns:
            640 bytes of 1-bit image data.
        """
        im = Image.new("1", (OLED_WIDTH, OLED_HEIGHT), color=0)
        draw = ImageDraw.Draw(im)

        line1, line2, line3 = build_stats_lines(stats)
        # Drop CPU temp (lowest priority) if line overflows display width
        font = self._font
        if (
            font is not None
            and font.getlength(line1) > OLED_WIDTH
            and stats.cpu_temp is not None
            and stats.gpu_percent is not None
        ):
            parts = [f"C:{stats.cpu_percent:3.0f}%", f"G:{stats.gpu_percent:.0f}%"]
            if stats.gpu_temp is not None:
                parts.append(f"{stats.gpu_temp:.0f}C")
            line1 = " ".join(parts)

        draw.text((0, 0), line1, font=self._font, fill=255)
        draw.text((0, 13), line2, font=self._font, fill=255)
        draw.text((0, 26), line3, font=self._font, fill=255)

        return im.tobytes()

    def _load_font(self) -> FreeTypeFont:
        """Load the font for rendering."""
        if self._font_path is not None:
            return ImageFont.truetype(str(self._font_path), self._font_size)

        # Use bundled font
        font_ref = files("steelseries_oled.assets").joinpath("OpenSans-Regular.ttf")
        with as_file(font_ref) as font_file:
            return ImageFont.truetype(str(font_file), self._font_size)

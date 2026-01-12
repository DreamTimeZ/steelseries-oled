"""Tests for display module."""

from pathlib import Path

from PIL import Image

from steelseries_oled.constants import OLED_HEIGHT, OLED_WIDTH
from steelseries_oled.display import load_frames


class TestLoadFrames:
    """Tests for load_frames function."""

    def test_resizes_to_oled_dimensions(self, tmp_path: Path) -> None:
        """Image should be resized to 128x40."""
        # Create oversized image
        img = Image.new("RGB", (256, 80), color=(255, 255, 255))
        img_path = tmp_path / "test.png"
        img.save(img_path)

        frames, _ = load_frames(img_path)

        assert len(frames) == 1
        # 128x40 @ 1-bit = 640 bytes
        assert len(frames[0]) == OLED_WIDTH * OLED_HEIGHT // 8

    def test_converts_to_1bit(self, tmp_path: Path) -> None:
        """Image should be converted to 1-bit monochrome."""
        # Create RGB image
        img = Image.new("RGB", (OLED_WIDTH, OLED_HEIGHT), color=(128, 128, 128))
        img_path = tmp_path / "test.png"
        img.save(img_path)

        frames, _ = load_frames(img_path)

        # Verify it's 1-bit packed (640 bytes for 128x40)
        assert len(frames[0]) == 640

    def test_gif_duration_minimum_cap(self, tmp_path: Path) -> None:
        """GIF with 0ms duration should be capped at 16ms minimum."""
        # Create GIF with 0ms duration
        img1 = Image.new("1", (OLED_WIDTH, OLED_HEIGHT), color=0)
        img2 = Image.new("1", (OLED_WIDTH, OLED_HEIGHT), color=1)
        gif_path = tmp_path / "test.gif"
        img1.save(
            gif_path,
            save_all=True,
            append_images=[img2],
            duration=0,  # 0ms - should be capped
        )

        _, sleep_time = load_frames(gif_path)

        # Should be capped at 16ms minimum
        assert sleep_time >= 0.016

    def test_static_image_uses_default_duration(self, tmp_path: Path) -> None:
        """Static image without duration info should use 1.0 second."""
        img = Image.new("1", (OLED_WIDTH, OLED_HEIGHT), color=0)
        img_path = tmp_path / "test.png"
        img.save(img_path)

        _, sleep_time = load_frames(img_path)

        assert sleep_time == 1.0

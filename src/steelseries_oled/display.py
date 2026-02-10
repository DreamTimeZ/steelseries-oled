"""OLED display functionality for images and GIFs.

Note:
    Image/GIF display is only supported on legacy keyboards (Apex Pro/7/5).
    Gen3 keyboards (Apex Pro Gen 3) do not support bitmap display via HID.
    Use 'steelseries-stats' for Gen3 keyboards.
"""

from typing import TYPE_CHECKING

from PIL import Image, ImageSequence

from steelseries_oled._signal import interruptible
from steelseries_oled.constants import OLED_HEIGHT, OLED_WIDTH
from steelseries_oled.device import is_gen3_device, open_device
from steelseries_oled.exceptions import Gen3NotSupportedError, ImageError

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


def load_frames(image_path: Path) -> tuple[list[bytes], float]:
    """Load and process image frames from a file.

    Args:
        image_path: Path to the image or GIF file.

    Returns:
        A tuple of (list of frame bytes, sleep time between frames).

    Raises:
        ImageError: If the image cannot be opened or processed.
    """
    try:
        with Image.open(image_path) as im:
            frames: list[bytes] = []

            for frame in ImageSequence.Iterator(im):
                # Resize to OLED dimensions
                resized = frame.resize((OLED_WIDTH, OLED_HEIGHT))
                # Convert to 1-bit monochrome
                mono = resized.convert("1")
                frames.append(mono.tobytes())

            # Get frame duration from the last frame
            if "duration" in im.info:
                # Minimum 16ms (~60fps) to prevent CPU spike on malformed GIFs
                sleep_time = max(im.info["duration"] / 1000.0, 0.016)
            else:
                # Static image: use 1 second refresh
                sleep_time = 1.0

            return frames, sleep_time
    except FileNotFoundError as e:
        msg = f"Image file not found: {image_path}"
        raise ImageError(msg) from e
    except Image.DecompressionBombError as e:
        msg = f"Image too large (potential decompression bomb): {image_path}"
        raise ImageError(msg) from e
    except OSError as e:
        msg = f"Failed to open image: {image_path}"
        raise ImageError(msg) from e


def display_image(image_path: Path) -> None:
    """Display an image or GIF on the OLED.

    Loops the image/animation until interrupted with Ctrl+C or SIGTERM.

    Note:
        This function only works on legacy keyboards (Apex Pro/7/5).
        Gen3 keyboards do not support bitmap display via HID.

    Args:
        image_path: Path to the image or GIF file.

    Raises:
        ImageError: If the image cannot be processed.
        DeviceNotFoundError: If no compatible device is found.
        Gen3NotSupportedError: If a Gen3 keyboard is detected.
    """
    # Check for Gen3 keyboard before loading images
    if is_gen3_device():
        raise Gen3NotSupportedError

    frames, sleep_time = load_frames(image_path)

    if not frames:
        msg = f"No frames found in image: {image_path}"
        raise ImageError(msg)

    print("Press Ctrl+C to exit.")

    with interruptible() as is_running, open_device(blank_on_exit=True) as device:
        while is_running():
            for frame_data in frames:
                if not is_running():
                    break
                device.send_image(frame_data)
                is_running.wait(sleep_time)

    print()  # Newline after Ctrl+C


def _display_frames(frames: Iterator[bytes], fps: float = 10.0) -> None:
    """Display a stream of frames on the OLED.

    Args:
        frames: Iterator yielding 640-byte frame data.
        fps: Target frames per second.
    """
    sleep_time = 1.0 / fps

    with interruptible() as is_running, open_device(blank_on_exit=True) as device:
        for frame_data in frames:
            if not is_running():
                break
            device.send_image(frame_data)
            is_running.wait(sleep_time)

    print()

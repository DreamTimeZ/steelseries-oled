#!/usr/bin/env python3
"""Generate high-quality application icon.

Creates a bar chart icon representing system statistics monitoring.
Uses supersampling (high-res render + LANCZOS downscale) for anti-aliased quality.
"""

from pathlib import Path

from PIL import Image, ImageDraw

# Icon sizes for Windows .ico (standard sizes for best compatibility)
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]

# Render at very high resolution for best quality supersampling
SUPERSAMPLE_SIZE = 2048


def draw_stats_icon(size: int) -> Image.Image:
    """Draw bar chart icon representing system statistics.

    Three vertical bars of varying heights - universal symbol for stats/metrics.
    Clean, modern design that scales well to all sizes.

    Args:
        size: Output size in pixels (square).

    Returns:
        PIL Image with the rendered icon.
    """
    # Colors - dark blue-gray background with white bars
    # IMPORTANT: Use solid background, not transparent. White-on-transparent icons
    # are invisible in Windows Explorer when using light theme (the default).
    bg_color = (45, 55, 72, 255)  # Dark blue-gray (#2D3748)
    bar_color = (255, 255, 255, 255)  # White

    # Create image with solid background
    img = Image.new("RGBA", (size, size), bg_color)
    draw = ImageDraw.Draw(img)

    # Layout parameters (relative to size)
    margin = size * 0.18  # Padding from edges
    bar_gap = size * 0.08  # Gap between bars
    corner_radius = size * 0.04  # Rounded corners

    # Calculate bar dimensions
    content_width = size - 2 * margin
    content_height = size - 2 * margin
    num_bars = 3
    total_gaps = bar_gap * (num_bars - 1)
    bar_width = (content_width - total_gaps) / num_bars

    # Bar heights as percentages of content height (ascending pattern)
    bar_heights = [0.45, 0.70, 1.0]  # Short, medium, tall

    # Draw each bar with rounded corners
    for i, height_pct in enumerate(bar_heights):
        x = margin + i * (bar_width + bar_gap)
        bar_height = content_height * height_pct
        y = margin + content_height - bar_height  # Align to bottom

        # Draw rounded rectangle
        draw.rounded_rectangle(
            [x, y, x + bar_width, margin + content_height],
            radius=corner_radius,
            fill=bar_color,
        )

    return img


def create_ico(output_path: Path) -> None:
    """Create multi-size ICO file using PIL's native ICO support.

    Args:
        output_path: Where to save the .ico file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Render at very high resolution for supersampling
    base_image = draw_stats_icon(SUPERSAMPLE_SIZE)

    # Create images at all sizes using high-quality downscaling
    images = []
    for size in ICO_SIZES:
        # Use LANCZOS for best quality downscaling (supersampling)
        resized = base_image.resize((size, size), Image.Resampling.LANCZOS)
        images.append(resized)

    # Use PIL's native ICO save - handles Windows format correctly
    # The largest image is saved first, with smaller sizes appended
    largest = images[-1]  # 256x256
    smaller = images[:-1]  # All smaller sizes

    largest.save(
        output_path,
        format="ICO",
        sizes=[(img.width, img.height) for img in images],
        append_images=smaller,
    )

    print(f"Generated: {output_path}")
    print(f"Sizes: {ICO_SIZES}")
    print(f"File size: {output_path.stat().st_size:,} bytes")


def main() -> None:
    """Generate icon to assets directory."""
    project_root = Path(__file__).parent.parent
    output_path = project_root / "src" / "steelseries_oled" / "assets" / "icon.ico"

    create_ico(output_path)


if __name__ == "__main__":
    main()

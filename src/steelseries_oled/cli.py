"""Command-line interface for SteelSeries OLED tools."""

import argparse
import logging
import sys
from pathlib import Path

from steelseries_oled import __version__
from steelseries_oled._windowless import is_windowless, redirect_streams
from steelseries_oled.backends import BackendType
from steelseries_oled.device import open_device
from steelseries_oled.display import display_image
from steelseries_oled.exceptions import (
    DeviceNotFoundError,
    Gen3NotSupportedError,
    ImageError,
    SteelSeriesError,
)
from steelseries_oled.profile import switch_profile
from steelseries_oled.stats import display_stats

# Epilog text for main parser
MAIN_EPILOG = """\
examples:
  steelseries oled logo.gif        Display animated GIF on OLED
  steelseries oled none            Blank the OLED screen
  steelseries stats                Show live CPU/memory/network stats
  steelseries stats --interval 0.5 Update stats twice per second
  steelseries profile 2            Switch to profile 2

supported keyboards:
  Legacy (full support): Apex Pro, Apex 7, Apex 5, and TKL variants
  Gen3 (stats only):     Apex Pro Gen 3, Apex Pro TKL Gen 3

Use -h with any command for detailed help.
"""

OLED_EPILOG = """\
examples:
  steelseries oled image.png       Display a static image
  steelseries oled animation.gif   Display an animated GIF (loops forever)
  steelseries oled none            Blank/clear the screen

supported formats:
  PNG, GIF, BMP, JPEG, and other PIL-supported formats.
  Images are automatically resized to 128x40 and converted to 1-bit.

note:
  This command is NOT supported on Gen3 keyboards (Apex Pro Gen 3, etc.).
  Use 'steelseries stats' instead, which works on all keyboards.

Press Ctrl+C to exit.
"""

STATS_EPILOG = """\
examples:
  steelseries stats                      Auto-detect backend, update every 1s
  steelseries stats --interval 0.5       Update twice per second
  steelseries stats --backend gamesense  Force GameSense (requires GG)
  steelseries stats --backend hid_gen3   Force Gen3 direct HID (no GG needed)
  steelseries stats --font mono.ttf      Use custom font (HID backends only)

displays:
  CPU: current usage % and hottest core %
  MEM: used / total in GB
  NET: upload/download speeds

Press Ctrl+C to exit.
"""

PROFILE_EPILOG = """\
examples:
  steelseries profile 1    Switch to profile 1
  steelseries profile 2    Switch to profile 2

note:
  This command is NOT supported on Gen3 keyboards.
  On Gen3, use SteelSeries key + F9 to switch profiles.
"""


def cmd_oled(args: argparse.Namespace) -> int:
    """Display images or GIFs on the OLED screen."""
    try:
        if args.image.lower() == "none":
            print("Blanking the screen...")
            with open_device(blank_on_exit=False) as device:
                device.blank_screen()
            return 0

        image_path = Path(args.image)
        if not image_path.exists():
            print(f"Error: File not found: {image_path}", file=sys.stderr)
            return 1

        display_image(image_path)
        return 0

    except DeviceNotFoundError:
        print("Error: No compatible SteelSeries device found.", file=sys.stderr)
        return 1
    except Gen3NotSupportedError:
        print(
            "Error: Gen3 keyboards do not support image/GIF display.",
            file=sys.stderr,
        )
        print(
            "Use 'steelseries stats' for system stats (works on Gen3).",
            file=sys.stderr,
        )
        return 1
    except ImageError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except SteelSeriesError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0


def cmd_stats(args: argparse.Namespace) -> int:
    """Display system statistics on the OLED screen."""
    if args.interval <= 0:
        print("Error: Interval must be positive.", file=sys.stderr)
        return 1

    if args.font is not None and not args.font.is_file():
        print(f"Error: Font file not found: {args.font}", file=sys.stderr)
        return 1

    # Map string to enum
    backend_map = {
        "auto": BackendType.AUTO,
        "gamesense": BackendType.GAMESENSE,
        "hid": BackendType.HID,
        "hid_gen3": BackendType.HID_GEN3,
    }
    backend = backend_map[args.backend]

    try:
        success = display_stats(
            font_path=args.font,
            update_interval=args.interval,
            backend=backend,
        )
        return 0 if success else 1

    except DeviceNotFoundError:
        print("Error: No compatible SteelSeries device found.", file=sys.stderr)
        if backend == BackendType.GAMESENSE:
            print("Ensure SteelSeries GG is running.", file=sys.stderr)
        return 1
    except SteelSeriesError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0


def cmd_profile(args: argparse.Namespace) -> int:
    """Switch keyboard profile."""
    try:
        if args.profile_number < 0:
            print("Error: Profile number cannot be negative.", file=sys.stderr)
            return 1

        switch_profile(args.profile_number)
        print(f"Switched to profile {args.profile_number}")
        return 0

    except DeviceNotFoundError:
        print("Error: No compatible SteelSeries device found.", file=sys.stderr)
        return 1
    except OverflowError:
        print("Error: Profile number too large.", file=sys.stderr)
        return 1
    except SteelSeriesError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0


def main() -> int:
    """Main entry point with subcommands."""
    redirect_streams()

    # Configure logging for warnings from library modules
    if is_windowless():
        logging.basicConfig(
            level=logging.WARNING,
            format="%(asctime)s %(levelname)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
        logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    # Use RawDescriptionHelpFormatter to preserve epilog formatting
    parser = argparse.ArgumentParser(
        prog="steelseries",
        description="SteelSeries keyboard OLED display tools.",
        epilog=MAIN_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        title="commands",
        metavar="<command>",
    )

    # oled subcommand
    oled_parser = subparsers.add_parser(
        "oled",
        help="display image/GIF on OLED (legacy keyboards only)",
        description=(
            "Display images or animated GIFs on the keyboard OLED screen.\n"
            "Images are resized to 128x40 pixels and converted to 1-bit monochrome."
        ),
        epilog=OLED_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    oled_parser.add_argument(
        "image",
        metavar="FILE",
        help="path to image/GIF file, or 'none' to blank the screen",
    )
    oled_parser.set_defaults(func=cmd_oled)

    # stats subcommand
    stats_parser = subparsers.add_parser(
        "stats",
        help="display live system statistics (all keyboards)",
        description=(
            "Display live system statistics on the OLED screen.\n"
            "Shows CPU usage, memory usage, and network throughput.\n"
            "Works on all supported keyboards including Gen3."
        ),
        epilog=STATS_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    stats_parser.add_argument(
        "--font",
        type=Path,
        metavar="FILE",
        default=None,
        help="custom TrueType font file (HID backends only)",
    )
    stats_parser.add_argument(
        "--interval",
        type=float,
        metavar="SEC",
        default=1.0,
        help="update interval in seconds (default: 1.0)",
    )
    stats_parser.add_argument(
        "--backend",
        choices=["auto", "gamesense", "hid", "hid_gen3"],
        default="auto",
        help=(
            "display backend: 'auto' selects hid_gen3 for Gen3, "
            "gamesense for legacy (falls back to hid if GG unavailable); "
            "'gamesense' uses SteelSeries GG; 'hid' direct USB (legacy); "
            "'hid_gen3' direct USB for Gen3 (default: auto)"
        ),
    )
    stats_parser.set_defaults(func=cmd_stats)

    # profile subcommand
    profile_parser = subparsers.add_parser(
        "profile",
        help="switch keyboard profile (legacy keyboards only)",
        description="Switch the keyboard to a different profile by number.",
        epilog=PROFILE_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    profile_parser.add_argument(
        "profile_number",
        type=int,
        metavar="N",
        help="profile number to switch to",
    )
    profile_parser.set_defaults(func=cmd_profile)

    args = parser.parse_args()
    result: int = args.func(args)
    return result


if __name__ == "__main__":
    sys.exit(main())

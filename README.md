# steelseries-oled

Python utility for displaying GIFs and system stats on SteelSeries keyboard OLED displays.

Supports SteelSeries Apex keyboards with 128x40 OLED screens:
- Apex Pro, Apex Pro TKL, Apex Pro TKL (2023), Apex Pro TKL Gen 3, Apex Pro TKL Wireless Gen 3
- Apex 7, Apex 7 TKL
- Apex 5

## Requirements

- Python 3.14+
- Windows, macOS, or Linux
- SteelSeries GG (optional - only needed for GameSense backend)

For Linux, install udev rules for non-root access: `sudo cp 99-steelseries.rules /etc/udev/rules.d/`

## Installation

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

## Usage

```bash
# Display live system stats (CPU, memory) - works on ALL keyboards
uv run steelseries stats
uv run steelseries stats --interval 0.5            # Faster updates
uv run steelseries stats --backend hid_gen3        # Force Gen3 direct HID
uv run steelseries stats --backend gamesense       # Force GameSense
uv run steelseries stats --backend hid             # Force HID (legacy only)

# Display a GIF or image on the OLED (legacy keyboards only)
uv run steelseries oled image.gif

# Blank the screen
uv run steelseries oled none

# Switch keyboard profile
uv run steelseries profile 2

# Show all available commands
uv run steelseries --help
```

## Gen3 Keyboard Support

Gen3 keyboards (Apex Pro Gen 3, Apex Pro TKL Gen 3) use a different protocol:

| Feature | Legacy Keyboards | Gen3 Keyboards |
|---------|-----------------|----------------|
| System stats (`steelseries stats`) | ✓ | ✓ (no GG required) |
| Image/GIF display (`steelseries oled`) | ✓ | ✗ Not supported |
| Profile switching (`steelseries profile`) | ✓ | ✓ |

Gen3 keyboards use a reverse-engineered HID protocol that works without SteelSeries GG.

## Documentation

- [Gen3 OLED Protocol Specification](docs/gen3-oled-protocol.md) - Reverse-engineered HID protocol for Gen3 keyboards

## Building Standalone Executables

```bash
# Install dev dependencies (includes PyInstaller)
uv sync --group dev

# Build single-file executable
uv run pyinstaller steelseries.spec

# Output: dist/steelseries (or dist/steelseries.exe on Windows)
```

**Automated releases:** Pushing a `v*` tag triggers GitHub Actions to build executables for Windows x64, macOS x64, macOS ARM64, and Linux x64. Download from [Releases](https://github.com/DreamTimeZ/steelseries-oled/releases).

## Development

```bash
# Install with dev dependencies
uv sync --group dev --group test

# Run tests
uv run pytest

# Lint and format
uv run ruff check --fix src/ tests/
uv run ruff format src/ tests/

# Type check
uv run mypy src/
```

## Adding New Keyboard Support

Add your keyboard's Product ID (PID) to `SUPPORTED_PIDS` in `src/steelseries_oled/constants.py`. The Vendor ID for all SteelSeries devices is `0x1038`.

## Troubleshooting

**GameSense timeout errors:** If `steelseries stats --backend gamesense` fails with a timeout error, restart SteelSeries GG completely. Check Task Manager (Windows) or Activity Monitor (macOS) for remaining SteelSeries processes and terminate them before restarting.

## License

MIT

---

This project is not affiliated with or endorsed by SteelSeries.

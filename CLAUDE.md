# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python 3.14+ package for displaying GIFs and system stats on SteelSeries keyboard OLED displays (128x40 pixels, 1-bit monochrome). Supports three backends:
- **GameSense**: HTTP API via SteelSeries GG (works on ALL keyboards including Gen3)
- **HID**: Direct USB HID feature reports (legacy keyboards only)
- **HID-Gen3**: Direct USB HID using reverse-engineered Gen3 protocol (no GG required)

## Development Commands

```bash
# Install all dependencies
uv sync --group dev --group test

# Run the tools (unified CLI with subcommands)
uv run steelseries oled <image.gif>    # Display image/GIF
uv run steelseries oled none           # Blank the screen
uv run steelseries stats               # Show CPU/memory stats
uv run steelseries stats --interval 0.5          # Faster updates
uv run steelseries stats --font /path/to/font.ttf  # Custom font
uv run steelseries stats --backend gamesense      # Force GameSense
uv run steelseries stats --backend hid            # Force HID (legacy only)
uv run steelseries stats --backend hid_gen3       # Force HID-Gen3 (Gen3 direct)
uv run steelseries profile <num>       # Switch profile
uv run steelseries --help              # Show available commands
uv run python -m steelseries_oled      # Alternative: run as module

# Linting and formatting
uv run ruff check src/ tests/          # Lint
uv run ruff check --fix src/ tests/    # Lint and auto-fix
uv run ruff format src/ tests/         # Format

# Type checking
uv run mypy src/

# Testing
uv run pytest                          # Run all tests
uv run pytest --cov                    # With coverage
uv run pytest -k "test_find"           # Run tests matching pattern
```

## Project Structure

```
steelseries-oled/
├── .python-version              # Python 3.14
├── pyproject.toml               # All configuration
├── uv.lock                      # Dependency lock (commit this)
├── src/steelseries_oled/
│   ├── __init__.py              # Package exports
│   ├── __main__.py              # python -m steelseries_oled
│   ├── py.typed                 # PEP 561 typed marker
│   ├── _signal.py               # Signal handling utilities
│   ├── _windowless.py           # Stream guard for windowless (no-console) builds
│   ├── constants.py             # VID, PIDs, GEN3_PIDS, dimensions
│   ├── exceptions.py            # Custom exceptions (incl. Gen3NotSupportedError)
│   ├── device.py                # Device detection, Gen3 detection
│   ├── display.py               # Image/GIF loading and display (legacy only)
│   ├── stats.py                 # System statistics display (uses backends)
│   ├── profile.py               # Profile switching
│   ├── cli.py                   # Unified CLI with subcommands (oled, stats, profile)
│   ├── backends/                # Stats display backends
│   │   ├── __init__.py          # Factory and auto-detection
│   │   ├── base.py              # StatsBackend abstract base
│   │   ├── gamesense.py         # GameSense HTTP API backend
│   │   ├── hid.py               # Direct HID bitmap backend (legacy)
│   │   └── hid_gen3.py          # Direct HID for Gen3 (no GG required)
│   └── assets/
│       ├── __init__.py          # Required for importlib.resources
│       └── OpenSans-Regular.ttf # Bundled font
└── tests/
    ├── conftest.py              # Fixtures
    └── test_*.py                # Tests
```

## Architecture

### Backend System (`backends/`)
Stats display uses a pluggable backend system:
- `StatsBackend` - Abstract base class defining the interface
- `GameSenseBackend` - HTTP JSON API via SteelSeries GG (all keyboards)
- `HIDBitmapBackend` - Direct HID with bitmap rendering (legacy only)
- `HIDGen3Backend` - Direct HID using reverse-engineered Gen3 protocol (no GG required)
- `create_backend()` - Factory with auto-detection (Gen3 prefers HID_GEN3)

```python
from steelseries_oled.backends import create_backend, BackendType
from steelseries_oled.models import SystemStats

# Auto-detect best backend (Gen3→HID_GEN3, legacy→GameSense)
backend = create_backend()

# Or specify explicitly
backend = create_backend(BackendType.GAMESENSE)

with backend:
    stats = SystemStats(
        cpu_percent=50.0,
        mem_used_gb=12.0, mem_total_gb=32.0,
        net_up_bytes=1000.0, net_down_bytes=5000.0,
    )
    backend.update_stats(stats)
```

### Device Layer (`device.py`)
- `find_device()` - Scans USB HID devices for compatible keyboards
- `is_gen3_device()` - Checks if connected keyboard is Gen3
- `SteelSeriesDevice` - Context manager for device lifecycle
- `open_device()` - Convenience context manager

### HID Protocol (Legacy Only)
**OLED Display (Report ID 0x61):** 642 bytes
- Byte 0: `0x61`, Bytes 1-640: image data, Byte 641: `0x00`
- **Note**: Gen3 keyboards ignore this report

**Profile Switch (Report ID 0x89):** 79 bytes
- Byte 0: `0x89`, Bytes 1-16: profile number, Bytes 17-78: `0x00`

### GameSense Protocol (Gen3 Compatible)
Uses SteelSeries GG HTTP API at `http://127.0.0.1:<port>/`:
- Port read from `C:\ProgramData\SteelSeries\SteelSeries Engine 3\coreProps.json`
- Endpoints: `/game_metadata`, `/bind_game_event`, `/game_event`, `/remove_game`
- Uses text mode with `screened-128x40` device type

## Supported Keyboards

VID `0x1038` (SteelSeries), PIDs in `constants.py`:
- **Legacy**: Apex Pro, Apex 7, Apex 5, TKL variants (full support)
- **Gen3**: Apex Pro Gen 3, Apex Pro TKL Gen 3 (stats only, no images)

## Gen3 Support

Gen3 keyboards use a different HID protocol for OLED bitmaps. The protocol was
reverse-engineered and documented in `docs/gen3-oled-protocol.md`. The `HIDGen3Backend`
implementation allows `steelseries stats` to work on Gen3 keyboards **without SteelSeries GG**.

Auto-detection prefers `HID_GEN3` for Gen3 keyboards (no GG dependency).

**Limitation**: Image/GIF display (`steelseries oled`) is not supported on Gen3.

## Adding New Keyboard Support

Add PID to `SUPPORTED_PIDS` in `src/steelseries_oled/constants.py`.
For Gen3 keyboards, also add to `GEN3_PIDS`.

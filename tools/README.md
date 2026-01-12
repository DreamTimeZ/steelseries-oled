# Development Tools

This directory contains development and debugging tools for working with SteelSeries keyboards.

## Files

| File | Purpose |
|------|---------|
| `diagnose.py` | Interactive diagnostic for device detection and interface testing |
| `gen3_bitmap_test.py` | Gen3 pixel layout verification tool |
| `generate_icon.py` | Generate application icon for PyInstaller builds |
| `USB_CAPTURE_GUIDE.md` | Guide for capturing USB traffic with Wireshark |

## Icon Generation

To regenerate the application icon:

```bash
uv run python tools/generate_icon.py
```

This creates `src/steelseries_oled/assets/icon.ico` with multiple sizes (16-256px).

### Windows Icon Cache

After rebuilding the exe with a new icon, Windows may still show the old icon due to aggressive caching. To fix:

**PowerShell:**
```powershell
taskkill /IM explorer.exe /F
Remove-Item "$env:LOCALAPPDATA\IconCache.db" -Force -ErrorAction SilentlyContinue
Remove-Item "$env:LOCALAPPDATA\Microsoft\Windows\Explorer\iconcache*" -Force -ErrorAction SilentlyContinue
Start-Process explorer.exe
```

**CMD:**
```cmd
taskkill /IM explorer.exe /F
del /A /Q "%localappdata%\IconCache.db"
del /A /F /Q "%localappdata%\Microsoft\Windows\Explorer\iconcache*"
start explorer.exe
```

Alternatively, copy the exe to a new folder—Windows fetches fresh icons for files in new locations.

## Quick Verification

To verify the OLED protocol is working correctly:

```bash
python gen3_bitmap_test.py
```

This runs interactive tests that display patterns at specific pixel positions.

## Documentation

For the complete protocol specification, see:
- [`../docs/gen3-oled-protocol.md`](../docs/gen3-oled-protocol.md)

The protocol documentation includes:
- Complete packet structure
- Bitmap format specification
- Command reference
- Reverse engineering methodology (Appendix D)

## Production Implementation

The production implementation is in:
```
src/steelseries_oled/backends/hid_gen3.py
```

## Dependencies

```bash
pip install hidapi
```

## Note

The original reverse engineering involved many intermediate test scripts that have been deleted. All findings from those scripts are documented in the protocol specification.

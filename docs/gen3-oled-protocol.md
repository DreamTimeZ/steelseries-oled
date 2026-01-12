# Gen3 OLED Protocol Specification

> **Reverse-engineered USB HID protocol for SteelSeries Apex Pro TKL Gen 3 OLED display**

---

## TL;DR - Quick Start

```python
import hid

# Open device (Interface 1)
dev = hid.device()
for d in hid.enumerate(0x1038, 0x1642):
    if d['interface_number'] == 1:
        dev.open_path(d['path'])
        break

# Send white screen
header = bytes([0x1F, 0x81])           # Custom bitmap command
bitmap = bytes([0xFF] * 640)           # 640 bytes, SSD1306 layout
padding = bytes([0x00, 0x00])          # 2 bytes padding
report = bytes([0x00]) + header + bitmap + padding  # 645 bytes total

dev.send_feature_report(report)
dev.close()
```

**Key Facts:**
- Interface 1, Report ID 0x00, Feature Report
- Header: `0x1F 0x81` for custom bitmap
- Bitmap: 640 bytes in SSD1306 row-of-segments format
- Total packet: 645 bytes (1 + 2 + 640 + 2)

---

## Table of Contents

1. [TL;DR - Quick Start](#tldr---quick-start)
2. [Glossary](#glossary)
3. [Scope](#scope)
4. [Device Information](#device-information)
5. [Protocol Specification](#protocol-specification)
6. [Command Reference](#command-reference)
7. [Bitmap Format](#bitmap-format)
8. [Implementation Guide](#implementation-guide)
9. [Test Environment](#test-environment)
10. [Known Limitations](#known-limitations)
11. [Troubleshooting](#troubleshooting)
12. [Safety Warnings](#safety-warnings)
13. [Reproduction Steps](#reproduction-steps)
14. [Tools Reference](#tools-reference)
15. [References](#references)
16. [Appendices](#appendices)

---

## Glossary

| Term | Definition |
|------|------------|
| **HID** | Human Interface Device - USB device class for keyboards, mice, etc. |
| **Feature Report** | HID report type for bidirectional configuration data (vs Input/Output reports) |
| **Report ID** | First byte of HID report identifying the report type |
| **SSD1306** | Common OLED controller IC; Gen3 uses compatible memory layout |
| **Segment Row** | Group of 8 pixel rows stored together (SSD1306 convention) |
| **Usage Page** | HID descriptor field defining device category (0xFFC0 = vendor-defined) |
| **VID/PID** | Vendor ID / Product ID - USB device identifiers |
| **LSB/MSB** | Least/Most Significant Bit - bit ordering within a byte |

---

## Scope

### In Scope
- Custom bitmap display on Gen3 OLED
- Protocol for `0x1F 0x81` (custom bitmap) command
- Bitmap memory layout and pixel addressing
- Basic protocol for other `0x1F` commands

### Out of Scope
- LED/RGB control protocol (uses different command structure)
- Profile management commands (partially discovered but not fully documented)
- Audio visualizer or other GG-specific features
- Wireless Gen3 variants (untested, may work with PID 0x1644)

---

## Device Information

### Hardware

| Property | Value |
|----------|-------|
| Manufacturer | SteelSeries |
| Product | Apex Pro TKL Gen 3 |
| Vendor ID (VID) | `0x1038` |
| Product ID (PID) | `0x1642` (wired), `0x1644` (wireless, untested) |
| OLED Resolution | 128 × 40 pixels |
| Color Depth | 1-bit (monochrome) |
| Bitmap Size | 640 bytes |

### USB Interfaces

| Interface | Usage Page | Purpose |
|-----------|------------|---------|
| 0 | 0x0001 (Generic Desktop) | Keyboard HID input |
| 1 | 0xFFC0 (Vendor-defined) | **OLED and LED control** |
| 2 | 0x0001 (Generic Desktop) | Secondary HID |
| 3 | 0x000C (Consumer) | Media keys |
| 4 | 0xFFC1 (Vendor-defined) | Unknown |

**Target:** Interface 1 with Usage Page `0xFFC0`

---

## Protocol Specification

### Packet Structure

```
┌─────────────┬─────────────────────────────────────────────────┐
│ Report ID   │ Payload (644 bytes)                             │
│ (1 byte)    │                                                 │
├─────────────┼────────┬────────┬──────────────────┬───────────┤
│    0x00     │ Command│ Mode   │ Bitmap Data      │ Padding   │
│             │ 0x1F   │ 0x81   │ (640 bytes)      │ (2 bytes) │
└─────────────┴────────┴────────┴──────────────────┴───────────┘

Total: 645 bytes
```

### USB Transfer Details

| Parameter | Value |
|-----------|-------|
| Transfer Type | Control (SET_REPORT) |
| bmRequestType | 0x21 (Class, Interface, Host-to-Device) |
| bRequest | 0x09 (SET_REPORT) |
| wValue | 0x0300 (Feature Report, Report ID 0) |
| wIndex | 0x0001 (Interface 1) |
| wLength | 644 |

### Byte Breakdown

| Offset | Size | Value | Description |
|--------|------|-------|-------------|
| 0 | 1 | `0x00` | Report ID |
| 1 | 1 | `0x1F` | OLED command prefix |
| 2 | 1 | `0x81` | Sub-command: custom bitmap |
| 3-642 | 640 | varies | Bitmap data (SSD1306 format) |
| 643-644 | 2 | `0x00` | Padding (ignored) |

---

## Command Reference

### OLED Commands (0x1F prefix)

| Command | Bytes | Effect | Data Used |
|---------|-------|--------|-----------|
| **Custom Bitmap** | `1F 81` | Display user bitmap | Yes (640 bytes) |
| **SteelSeries Logo** | `1F 80` | Display built-in logo | No (ignored) |
| **Profile Screen** | `1F 82` | Display profile indicator | No (ignored) |

### Other Discovered Commands

| Command | Effect | Warning |
|---------|--------|---------|
| `1E 81` | Shows actuation point settings | Read-only display |
| `81 xx` | Profile switching (unstable) | ⛔ **DO NOT USE** - see below |

#### ⛔ Profile Switching (`81 xx`) - Unsafe

The `81 xx` command was tested for profile switching but is **unstable and dangerous**.

**Test environment:** Apex Pro TKL Gen 3 (PID 0x1642), wired, 2025-01.

**Packet structure used:**
```
Report ID 0x00 + 0x81 + profile_byte + 642 zero bytes = 645 bytes total
```

| Tested | Result |
|--------|--------|
| `81 01` | Partial success — profile 1 activated inconsistently |
| `81 02` | Firmware error — red LED flicker, required keyboard replug |

**Observed behavior:**
- `send_feature_report()` returns 645 (apparent success)
- Triggers USB disconnect/re-enumeration (~3 seconds)
- Frequently causes firmware error state (red LED flicker)
- Keyboard becomes unresponsive until physically unplugged

**Safe alternative:** Use `1F 82` to display the current profile indicator on OLED, then use hardware shortcut (SteelSeries key + F9) to switch profiles.

**For future investigation:** Capture USB traffic from SteelSeries GG performing a profile switch to discover the correct protocol.

### Invalid/Rejected Commands

| Command | Result |
|---------|--------|
| `1F 00` | Send fails (result = -1) |
| `1F FF` | No effect |
| `61 xx` | Rejected (legacy protocol) |

---

## Bitmap Format

### Overview

The Gen3 OLED uses **SSD1306-compatible** memory layout:
- 128 columns × 40 rows = 5,120 pixels
- 1 bit per pixel = 640 bytes
- Organized in 5 "segment rows" of 8 pixels each

### Memory Layout

```
640 bytes = 5 segment rows × 128 bytes per row

┌──────────────────────────────────────────────────────┐
│ Bytes 0-127:   Segment Row 0 (pixel rows 0-7)        │
│ Bytes 128-255: Segment Row 1 (pixel rows 8-15)       │
│ Bytes 256-383: Segment Row 2 (pixel rows 16-23)      │
│ Bytes 384-511: Segment Row 3 (pixel rows 24-31)      │
│ Bytes 512-639: Segment Row 4 (pixel rows 32-39)      │
└──────────────────────────────────────────────────────┘
```

### Byte-to-Pixel Mapping

Each byte represents 8 **vertical** pixels in a single column:

```
Byte value: 0bABCDEFGH

  Bit 0 (H) → Row 0 of segment (TOP)
  Bit 1 (G) → Row 1
  Bit 2 (F) → Row 2
  Bit 3 (E) → Row 3
  Bit 4 (D) → Row 4
  Bit 5 (C) → Row 5
  Bit 6 (B) → Row 6
  Bit 7 (A) → Row 7 of segment (BOTTOM)

Pixel value: 1 = white (lit), 0 = black (off)
```

### Coordinate Conversion

```python
def get_byte_and_bit(x: int, y: int) -> tuple[int, int]:
    """Convert pixel (x, y) to (byte_index, bit_position)."""
    segment_row = y // 8          # 0-4
    bit_position = y % 8          # 0-7 (0 = top of segment)
    byte_index = segment_row * 128 + x
    return byte_index, bit_position

def set_pixel(bitmap: bytearray, x: int, y: int, on: bool = True):
    """Set pixel at (x, y) in 640-byte bitmap."""
    if not (0 <= x < 128 and 0 <= y < 40):
        return
    byte_idx, bit_pos = get_byte_and_bit(x, y)
    if on:
        bitmap[byte_idx] |= (1 << bit_pos)
    else:
        bitmap[byte_idx] &= ~(1 << bit_pos)
```

### Visual Diagram

```
        Column 0      Column 1      ...     Column 127
       ┌────────┐    ┌────────┐           ┌────────┐
Row 0  │ Bit 0  │    │ Bit 0  │           │ Bit 0  │  ─┐
Row 1  │ Bit 1  │    │ Bit 1  │           │ Bit 1  │   │ Segment
Row 2  │ Bit 2  │    │ Bit 2  │           │ Bit 2  │   │ Row 0
Row 3  │ Bit 3  │    │ Bit 3  │           │ Bit 3  │   │ (Bytes
Row 4  │ Bit 4  │    │ Bit 4  │           │ Bit 4  │   │ 0-127)
Row 5  │ Bit 5  │    │ Bit 5  │           │ Bit 5  │   │
Row 6  │ Bit 6  │    │ Bit 6  │           │ Bit 6  │   │
Row 7  │ Bit 7  │    │ Bit 7  │           │ Bit 7  │  ─┘
       └────────┘    └────────┘           └────────┘
        Byte 0        Byte 1              Byte 127
       ┌────────┐    ┌────────┐           ┌────────┐
Row 8  │ Bit 0  │    │ Bit 0  │           │ Bit 0  │  ─┐
  ...  │  ...   │    │  ...   │           │  ...   │   │ Segment
Row 15 │ Bit 7  │    │ Bit 7  │           │ Bit 7  │  ─┘ Row 1
       └────────┘    └────────┘           └────────┘
        Byte 128      Byte 129            Byte 255

       ... (continues for segment rows 2, 3, 4) ...
```

---

## Implementation Guide

### Minimal Python Example

```python
import hid

VENDOR_ID = 0x1038
PRODUCT_ID = 0x1642

def send_oled_bitmap(bitmap_640: bytes) -> bool:
    """Send 640-byte bitmap to Gen3 OLED. Returns success status."""
    # Find device
    dev = hid.device()
    for d in hid.enumerate(VENDOR_ID, PRODUCT_ID):
        if d['interface_number'] == 1:
            dev.open_path(d['path'])
            break
    else:
        raise RuntimeError("Device not found")

    # Build packet
    report = bytes([
        0x00,                    # Report ID
        0x1F, 0x81,              # Custom bitmap command
        *bitmap_640,             # 640 bytes bitmap
        0x00, 0x00               # Padding
    ])
    assert len(report) == 645

    # Send
    result = dev.send_feature_report(report)
    dev.close()
    return result > 0
```

### PIL Image Conversion

```python
from PIL import Image

def pil_to_gen3(image: Image.Image) -> bytes:
    """Convert PIL Image to Gen3 bitmap format."""
    # Normalize to 128x40 1-bit
    img = image.resize((128, 40)).convert("1")
    pixels = img.load()

    bitmap = bytearray(640)
    for seg_row in range(5):
        for x in range(128):
            byte_val = 0
            for bit in range(8):
                y = seg_row * 8 + bit
                if y < 40 and pixels[x, y]:
                    byte_val |= (1 << bit)
            bitmap[seg_row * 128 + x] = byte_val

    return bytes(bitmap)
```

### Requirements

```
hidapi>=0.14.0
Pillow>=9.0.0  # For image rendering
```

---

## Test Environment

Testing was performed on:

| Component | Version/Details |
|-----------|-----------------|
| **OS** | Windows 11 |
| **Python** | 3.14+ |
| **hidapi** | 0.15.0 |
| **Keyboard** | Apex Pro TKL Gen 3 (wired) |
| **Keyboard Firmware** | Latest as of 2026-01-11 |
| **SteelSeries GG** | Not running during tests |

### Device Identification

Windows Device Manager:
```
HID\VID_1038&PID_1642&MI_01
```

Linux `lsusb`:
```
Bus 002 Device 060: ID 1038:1642 SteelSeries ApS Apex Pro TKL Gen 3
```

---

## Known Limitations

### Untested

1. **Wireless variant** (PID 0x1644) - Protocol likely identical but unverified
2. **Other Gen3 models** - Full-size Apex Pro Gen 3 may have different PID
3. **Concurrent access** - Behavior when GG is also running
4. **Maximum frame rate** - Tested ~30 FPS, limit unknown
5. **Long-term reliability** - No extended duration testing

### Not Supported

1. **Grayscale/color** - Display is monochrome only
2. **Partial updates** - Must send full 640-byte frame
3. **Display brightness** - No brightness control discovered
4. **Display sleep/wake** - No power management commands found
5. **Profile switching via HID** — `81 xx` is unstable (see Safety Warnings); use `1F 82` to view, SteelSeries+F9 to switch

### Protocol Gaps

1. LED/RGB protocol documented separately (different command structure)
2. **Profile switching protocol** - `81 xx` tested but unstable; correct protocol unknown (needs USB capture from GG)
3. Actuation point configuration protocol not fully explored

---

## Troubleshooting

### Device Not Found

```
RuntimeError: Device not found
```

**Causes & Solutions:**
| Cause | Solution |
|-------|----------|
| Keyboard not connected | Check USB connection |
| Wrong PID | Verify with `hid.enumerate(0x1038)` |
| Wrong interface | Must use interface 1, not 0 or 2 |
| Permission denied (Linux) | Add udev rule (see below) |
| Driver conflict | Close SteelSeries GG |

**Linux udev rule** (`/etc/udev/rules.d/99-steelseries.rules`):
```
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="1038", ATTRS{idProduct}=="1642", MODE="0666"
SUBSYSTEM=="usb", ATTRS{idVendor}=="1038", ATTRS{idProduct}=="1642", MODE="0666"
```
Then: `sudo udevadm control --reload-rules && sudo udevadm trigger`

### Send Returns -1

```
result = dev.send_feature_report(report)  # Returns -1
```

**Causes & Solutions:**
| Cause | Solution |
|-------|----------|
| Invalid command bytes | Use `1F 81`, not `1F 00` or `1F FF` |
| Wrong packet size | Must be exactly 645 bytes |
| Device closed | Re-open device before sending |
| Wrong report ID | First byte must be `0x00` |

### Display Shows Nothing

**Causes & Solutions:**
| Cause | Solution |
|-------|----------|
| All-zero bitmap | Verify bitmap has non-zero bytes |
| Wrong header | Use `1F 81`, not `1F 80` (shows logo) |
| Inverted colors | 1=white, 0=black (not inverted) |
| Wrong layout | Use SSD1306 format, not raw row-major |

### Display Shows Corruption

**Causes & Solutions:**
| Cause | Solution |
|-------|----------|
| Wrong byte order | Check segment row calculation |
| Wrong bit order | Bit 0 = top, Bit 7 = bottom |
| Truncated data | Ensure full 640 bytes sent |

---

## Safety Warnings

### ⛔ Dangerous Commands

| Command | Risk | Mitigation |
|---------|------|------------|
| `81 xx` | **Unstable** — causes red LED flicker, USB disconnect, may require replug | **Do not use** — use `1F 82` to view profile, SteelSeries+F9 to switch |

### ⚠️ Commands That Affect Keyboard State

| Command | Risk | Mitigation |
|---------|------|------------|
| `1E xx` | May alter actuation settings | Use read-only |

### ⚠️ Potential Issues

1. **Rapid commands** - Sending too fast may cause USB errors; add small delays if needed
2. **Malformed packets** - May cause temporary display glitch; recovers on next valid frame
3. **Hot unplug** - Close device handle properly to avoid resource leaks

### ✅ Safe Commands

| Command | Safety |
|---------|--------|
| `1F 80` | Safe - just shows logo |
| `1F 81` + bitmap | Safe - only affects OLED |
| `1F 82` | Safe - shows profile indicator |

---

## Reproduction Steps

To verify these findings independently:

### 1. Setup Environment

```bash
pip install hidapi Pillow
```

### 2. Verify Device Detection

```python
import hid
for d in hid.enumerate(0x1038, 0x1642):
    print(f"Interface {d['interface_number']}: {d['path']}")
# Should show interfaces 0, 1, 2
```

### 3. Test Basic Protocol

```python
# Display all-white screen
dev = hid.device()
for d in hid.enumerate(0x1038, 0x1642):
    if d['interface_number'] == 1:
        dev.open_path(d['path'])
        break

report = bytes([0x00, 0x1F, 0x81]) + bytes([0xFF]*640) + bytes([0x00, 0x00])
result = dev.send_feature_report(report)
print(f"Result: {result}")  # Should be 645
dev.close()
```

### 4. Verify Pixel Positions

Run `tools/gen3_bitmap_test.py` and confirm:
- Single pixels appear at correct corners
- Lines appear at correct edges
- Border rectangle is complete

---

## Tools Reference

| Tool | Purpose | Usage |
|------|---------|-------|
| `gen3_bitmap_test.py` | Pixel layout verification | `python tools/gen3_bitmap_test.py` |
| `USB_CAPTURE_GUIDE.md` | Wireshark USB capture guide | Reference documentation |

Note: Additional discovery and analysis tools were used during reverse engineering but have been archived. See Appendix D for the methodology used.

---

## References

### External

| Resource | URL | Accessed |
|----------|-----|----------|
| apex-tux Issue #66 | https://github.com/AntoinePrworx/apex-tux/issues/66 | 2026-01-11 |
| edbgon/steelseries-oled | https://github.com/edbgon/steelseries-oled | 2026-01-11 |
| USB HID Specification | https://www.usb.org/hid | 2026-01-11 |
| SSD1306 Datasheet | (various sources) | N/A |

### Internal

| Document | Description |
|----------|-------------|
| `src/steelseries_oled/backends/hid_gen3.py` | Production implementation |
| `tools/README.md` | Tools documentation |

---

## Appendices

### A. Captured Packet Example

**OLED Bitmap Frame (Frame 311 from capture):**

```
USB SET_REPORT to Interface 1:
09 00 03 01 00 84 02    <- USB setup (7 bytes)
1f 81                   <- Command: custom bitmap
ff ff ff ff ff ff ff ff <- Bitmap data start
ff ff ff 3f 07 03 03 01
01 00 00 00 00 00 00 01
01 01 03 03 07 1f 7f ff
... (continues for 640 bytes total)
00 00                   <- Padding
```

### B. Complete Command List

```
OLED Commands (0x1F prefix):
  1F 80 - Display SteelSeries logo
  1F 81 - Display custom bitmap (640 bytes follow)
  1F 82 - Display profile indicator

Other Commands:
  1E 81 - Show actuation settings
  81 xx - Profile-related (use with caution)

Invalid:
  1F 00 - Rejected (send fails)
  1F FF - No effect
  61 xx - Rejected (legacy protocol)
```

### C. Packet Template

```python
def create_gen3_oled_packet(bitmap_640: bytes) -> bytes:
    """Create complete 645-byte packet for Gen3 OLED."""
    assert len(bitmap_640) == 640, "Bitmap must be 640 bytes"
    return bytes([
        0x00,                      # Report ID
        0x1F,                      # OLED command
        0x81,                      # Custom bitmap mode
        *bitmap_640,               # Bitmap (SSD1306 format)
        0x00, 0x00                 # Padding
    ])
```

### D. Reverse Engineering Methodology

This section documents the systematic approach used to discover the Gen3 protocol.

#### Phase 1: Device Enumeration

Used `hid.enumerate()` to discover all USB interfaces:

```
PID 0x1642 - Apex Pro TKL Gen 3:
  Interface 0: Usage Page 0x0001 (Generic Desktop) - Keyboard
  Interface 1: Usage Page 0xFFC0 (Vendor-defined) - OLED/LED control ← Target
  Interface 2: Usage Page 0x0001 (Generic Desktop) - Secondary HID
  Interface 3: Usage Page 0x000C (Consumer) - Media keys
  Interface 4: Usage Page 0xFFC1 (Vendor-defined) - Unknown
```

**Key finding:** Interface 1 with Usage Page 0xFFC0 is the control interface.

#### Phase 2: Report ID Discovery

Systematically tested report IDs 0x00-0xFF on Interface 1:

| Report ID | Result |
|-----------|--------|
| 0x00 | Accepted |
| 0x01 | Accepted (triggers profile display) |
| 0x02-0xFF | Rejected |

**Key finding:** Only Report IDs 0x00 and 0x01 are valid.

#### Phase 3: USB Traffic Capture

1. Installed Wireshark + USBPcap on Windows
2. Captured traffic while SteelSeries GG updated the OLED
3. Filtered for `usb.idVendor == 0x1038`
4. Identified 680-byte SET_REPORT packets to Interface 1

**Key finding:** Packets are 644-byte payload (after USB header), sent as Feature Reports.

#### Phase 4: Packet Structure Analysis

Analyzed captured Frame 311 (OLED bitmap):

```
Offset 0-1:   1f 81        <- Command header
Offset 2-641: ff ff ff...  <- Bitmap data (640 bytes)
Offset 642-643: 00 00      <- Padding
```

**Key finding:** Header `0x1F 0x81` indicates custom bitmap mode.

#### Phase 5: Command Discovery

Tested variations of the header byte:

| Header | Effect |
|--------|--------|
| `1F 80` | Displays built-in SteelSeries logo |
| `1F 81` | Displays custom bitmap (data used) |
| `1F 82` | Displays profile indicator |
| `1F 00` | Send fails (returns -1) |
| `1F FF` | No visible effect |

#### Phase 6: Bitmap Layout Discovery

Tested two layout hypotheses:

1. **Column-major** (5 bytes/column × 128 columns): Single-pixel tests showed wrong positions
2. **Row-of-segments** (128 bytes/row × 5 segment rows): All pixel positions correct

Verification tests:
- Pixel (0,0) → Top-left corner ✓
- Pixel (127,0) → Top-right corner ✓
- Pixel (0,39) → Bottom-left corner ✓
- Pixel (127,39) → Bottom-right corner ✓
- Full border rectangle → Complete frame ✓

**Key finding:** Layout is SSD1306-style (row-of-segments), bit 0 = top pixel.

#### Phase 7: Color Polarity

| Byte Value | Display |
|------------|---------|
| `0xFF` | White (all pixels lit) |
| `0x00` | Black (all pixels off) |
| `0xAA` | Horizontal stripes |

**Key finding:** 1 = white, 0 = black (standard polarity).

#### Tools Used

| Tool | Purpose |
|------|---------|
| `hid.enumerate()` | Device discovery |
| Wireshark + USBPcap | USB traffic capture |
| Custom Python scripts | Protocol testing |
| Interactive verification | Visual confirmation |

---

*This document was created through reverse engineering. SteelSeries, Apex Pro, and related marks are trademarks of SteelSeries. This project is not affiliated with or endorsed by SteelSeries.*

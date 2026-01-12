# USB Traffic Capture Guide for Gen3 Protocol Reverse Engineering

> **Note:** The Gen3 OLED protocol has been successfully reverse-engineered. See `docs/gen3-oled-protocol.md` for the complete specification. This guide is retained for future reverse engineering of other devices or firmware versions.

This guide explains how to capture USB traffic from your Gen3 keyboard to reverse-engineer the OLED protocol.

## Why Capture USB Traffic?

Gen3 SteelSeries keyboards (Apex Pro Gen 3, Apex Pro TKL Gen 3) use a different HID protocol than legacy models. The legacy protocol (report ID `0x61`, 642-byte packets) is ignored by Gen3 keyboards. To control the OLED without SteelSeries GG, we need to reverse-engineer the new protocol.

## What You'll Need

1. **Wireshark** (packet analyzer) - https://www.wireshark.org/
2. **USBPcap** (Windows USB capture driver) - https://desowin.org/usbpcap/
3. **SteelSeries GG** installed and working with your keyboard
4. A Gen3 keyboard connected via USB

## Step-by-Step Capture Process

### 1. Install Wireshark + USBPcap

Download and install Wireshark. During installation, make sure to install USBPcap when prompted. Restart your computer after installation.

### 2. Identify Your Keyboard's USB Bus

Open Command Prompt and run:
```cmd
USBPcapCMD.exe
```

This will list USB devices. Look for your SteelSeries keyboard and note which root hub it's connected to.

### 3. Start Capture in Wireshark

1. Open Wireshark
2. You should see USBPcap interfaces listed (e.g., `USBPcap1`, `USBPcap2`)
3. Double-click the interface your keyboard is connected to
4. Capture will start

### 4. Generate OLED Traffic

With capture running:

1. Open SteelSeries GG
2. Go to keyboard settings
3. Change something on the OLED (e.g., display settings, trigger an app notification)
4. Wait for the OLED to update
5. Repeat a few times for multiple samples

### 5. Stop and Filter Capture

1. Stop the capture (red square button)
2. Apply filter to isolate your keyboard traffic:
   ```
   usb.idVendor == 0x1038
   ```
   Or filter by address if you know it:
   ```
   usb.device_address == X
   ```

### 6. Find OLED Commands

Look for:
- **URB_CONTROL out** or **URB_INTERRUPT out** packets going TO the keyboard
- Packets that are larger (>100 bytes) - likely image data
- Packets sent when the OLED changes

Examine the packet data:
- Right-click a packet → Copy → ...as Hex Stream
- Look for patterns in the first few bytes (report ID, command type)

## What to Look For

### Packet Structure

Legacy keyboards use:
```
[0x61] [640 bytes bitmap] [0x00] = 642 bytes total
```

Gen3 might use:
- Different report ID (not 0x61)
- Different packet structure
- Initialization/handshake sequence
- Multiple packets for one image
- Encryption/obfuscation

### Key Patterns

1. **Report ID**: First byte of feature reports
2. **Command byte**: Often second byte indicates command type
3. **Length fields**: Sometimes packets include length prefixes
4. **Bitmap data**: Look for 640 bytes of image data (128×40 / 8 = 640)

## Analyzing the Capture

### Export for Analysis

1. File → Export Packet Dissections → As JSON
2. Include only filtered packets
3. Use the analysis script below

### Quick Analysis Script

Save captured packets as JSON, then run:

```python
import json

with open("capture.json") as f:
    packets = json.load(f)

print(f"Total packets: {len(packets)}")
```

## Sharing Your Findings

If you successfully capture OLED-related traffic:

1. Save the relevant packets (File → Export Specified Packets)
2. Document:
   - Your keyboard model and PID
   - What action triggered the OLED update
   - Any patterns you noticed
3. Share via GitHub issue

## Alternative: Using API Monitor

For a more detailed view of SteelSeries GG's HID calls:

1. Download API Monitor - http://www.rohitab.com/apimonitor
2. Monitor `hid.dll` and `setupapi.dll`
3. Watch for `HidD_SetFeature`, `HidD_GetFeature` calls
4. Capture the exact data being sent

## Common Pitfalls

- **Wrong interface**: Make sure to capture the correct USB bus
- **Missing packets**: Some USB traffic is filtered by default
- **Encryption**: If data looks random, it might be encrypted
- **Firmware versions**: Different firmware may use different protocols

## Next Steps

Once you have captured data:

1. Identify the report ID(s) used for OLED
2. Determine packet structure
3. Check for initialization sequence
4. Test with custom scripts based on the protocol documentation
5. Report findings for implementation

#!/usr/bin/env python3
"""Test Gen3 OLED with correct protocol: 1f 81 + 642 bytes bitmap."""


import hid

VENDOR_ID = 0x1038
GEN3_TKL_PID = 0x1642
OLED_WIDTH = 128
OLED_HEIGHT = 40

# Correct structure:
# - 0x1f = OLED command
# - 0x81 = Custom bitmap mode
# - 642 bytes = bitmap data (640 display + 2 extra?)

def open_device():
    devices = hid.enumerate(VENDOR_ID, GEN3_TKL_PID)
    dev = hid.device()
    for d in devices:
        if d["interface_number"] == 1:
            dev.open_path(d["path"])
            return dev
    return None


def send_bitmap(dev, bitmap_data: bytes):
    """Send bitmap with 1f 81 header."""
    # Ensure exactly 642 bytes of bitmap data
    data = bitmap_data[:642]
    if len(data) < 642:
        data = data + bytes([0x00] * (642 - len(data)))

    payload = bytes([0x1f, 0x81]) + data  # 2 + 642 = 644
    report = bytes([0x00]) + payload      # 1 + 644 = 645
    return dev.send_feature_report(report)


def create_bitmap():
    """Create a 642-byte bitmap buffer."""
    return bytearray(642)


def set_pixel_v1(bitmap: bytearray, x: int, y: int, value: bool = True):
    """Try layout V1: Row-of-segments (SSD1306 style).

    - 128 bytes per segment row
    - 5 segment rows (but we have 642 bytes, so ~5.01 rows?)
    - Bit 0 = top of segment
    """
    if x < 0 or x >= OLED_WIDTH or y < 0 or y >= OLED_HEIGHT:
        return

    segment_row = y // 8
    bit_pos = y % 8
    byte_index = segment_row * 128 + x

    if byte_index >= 642:
        return

    if value:
        bitmap[byte_index] |= (1 << bit_pos)
    else:
        bitmap[byte_index] &= ~(1 << bit_pos)


def set_pixel_v2(bitmap: bytearray, x: int, y: int, value: bool = True):
    """Try layout V2: Column-major.

    - 5 bytes per column (but 642/128 = ~5.01?)
    - 128 columns
    """
    if x < 0 or x >= OLED_WIDTH or y < 0 or y >= OLED_HEIGHT:
        return

    bytes_per_col = 5  # 40 pixels / 8
    byte_index = x * bytes_per_col + (y // 8)
    bit_pos = y % 8

    if byte_index >= 642:
        return

    if value:
        bitmap[byte_index] |= (1 << bit_pos)
    else:
        bitmap[byte_index] &= ~(1 << bit_pos)


def main():
    print("=" * 60)
    print("GEN3 BITMAP LAYOUT TEST")
    print("=" * 60)
    print("Using correct header: 1f 81")
    print("Bitmap data: 642 bytes")

    dev = open_device()
    if not dev:
        print("Device not found!")
        return

    try:
        # Test 1: All white
        print("\nTest 1: All white (0xFF)")
        send_bitmap(dev, bytes([0xFF] * 642))
        input("Is it WHITE? Press Enter...")

        # Test 2: All black
        print("\nTest 2: All black (0x00)")
        send_bitmap(dev, bytes([0x00] * 642))
        input("Is it BLACK? Press Enter...")

        # Test 3: First byte only
        print("\nTest 3: Only byte 0 = 0xFF")
        bitmap = create_bitmap()
        bitmap[0] = 0xFF
        send_bitmap(dev, bytes(bitmap))
        input("Where is the white mark? [describe position]...")

        # Test 4: Byte 127 only (end of first "row" if SSD1306 style)
        print("\nTest 4: Only byte 127 = 0xFF")
        bitmap = create_bitmap()
        bitmap[127] = 0xFF
        send_bitmap(dev, bytes(bitmap))
        input("Where is the white mark? [describe position]...")

        # Test 5: Byte 128 only (start of second "row" if SSD1306 style)
        print("\nTest 5: Only byte 128 = 0xFF")
        bitmap = create_bitmap()
        bitmap[128] = 0xFF
        send_bitmap(dev, bytes(bitmap))
        input("Where is the white mark? [describe position]...")

        # Test 6: Last byte (641)
        print("\nTest 6: Only byte 641 = 0xFF (last byte)")
        bitmap = create_bitmap()
        bitmap[641] = 0xFF
        send_bitmap(dev, bytes(bitmap))
        input("Where is the white mark? [describe position]...")

        # Test 7: Byte 639 (last of 640 if standard size)
        print("\nTest 7: Only byte 639 = 0xFF")
        bitmap = create_bitmap()
        bitmap[639] = 0xFF
        send_bitmap(dev, bytes(bitmap))
        input("Where is the white mark? [describe position]...")

        # Test 8: Try V1 layout - top-left pixel
        print("\nTest 8: V1 layout - pixel at (0,0)")
        bitmap = create_bitmap()
        set_pixel_v1(bitmap, 0, 0, True)
        send_bitmap(dev, bytes(bitmap))
        input("Is there a dot at TOP-LEFT? [y/n]...")

        # Test 9: Try V1 layout - pixel at (127,0)
        print("\nTest 9: V1 layout - pixel at (127,0)")
        bitmap = create_bitmap()
        set_pixel_v1(bitmap, 127, 0, True)
        send_bitmap(dev, bytes(bitmap))
        input("Is there a dot at TOP-RIGHT? [y/n]...")

        # Test 10: Try V1 layout - horizontal line at y=0
        print("\nTest 10: V1 layout - line at y=0")
        bitmap = create_bitmap()
        for x in range(128):
            set_pixel_v1(bitmap, x, 0, True)
        send_bitmap(dev, bytes(bitmap))
        input("Is there a line at TOP? [y/n]...")

        # Test 11: Try V2 layout - pixel at (0,0)
        print("\nTest 11: V2 layout - pixel at (0,0)")
        bitmap = create_bitmap()
        set_pixel_v2(bitmap, 0, 0, True)
        send_bitmap(dev, bytes(bitmap))
        input("Is there a dot at TOP-LEFT? [y/n]...")

        # Test 12: Try V2 layout - horizontal line at y=0
        print("\nTest 12: V2 layout - line at y=0")
        bitmap = create_bitmap()
        for x in range(128):
            set_pixel_v2(bitmap, x, 0, True)
        send_bitmap(dev, bytes(bitmap))
        input("Is there a line at TOP? [y/n]...")

        # Test 13: Diagonal using V1
        print("\nTest 13: V1 diagonal from (0,0) to (39,39)")
        bitmap = create_bitmap()
        for i in range(40):
            set_pixel_v1(bitmap, i, i, True)
        send_bitmap(dev, bytes(bitmap))
        input("Is there a diagonal line? [y/n]...")

        # Test 14: Simple rectangle using V1
        print("\nTest 14: V1 rectangle border")
        bitmap = create_bitmap()
        for x in range(128):
            set_pixel_v1(bitmap, x, 0, True)
            set_pixel_v1(bitmap, x, 39, True)
        for y in range(40):
            set_pixel_v1(bitmap, 0, y, True)
            set_pixel_v1(bitmap, 127, y, True)
        send_bitmap(dev, bytes(bitmap))
        input("Is there a BORDER rectangle? [y/n]...")

    finally:
        send_bitmap(dev, bytes(642))  # Clear
        dev.close()

    print("\n" + "=" * 60)
    print("Based on byte position tests (3-7), we can determine the layout.")
    print("=" * 60)


if __name__ == "__main__":
    main()

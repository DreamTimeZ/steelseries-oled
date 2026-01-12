#!/usr/bin/env python3
"""Diagnostic script to investigate SteelSeries OLED communication."""

import time

import hid
from PIL import Image, ImageDraw

VENDOR_ID = 0x1038
SUPPORTED_PIDS = {
    0x1610: "Apex Pro",
    0x1612: "Apex 7",
    0x1614: "Apex Pro TKL",
    0x1618: "Apex 7 TKL",
    0x161C: "Apex 5",
    0x1628: "Apex Pro TKL (2023)",
    0x1642: "Apex Pro TKL Gen 3",
    0x1644: "Apex Pro TKL Wireless Gen 3",
}

GEN3_PIDS = {0x1642, 0x1644}

OLED_WIDTH = 128
OLED_HEIGHT = 40


def create_test_image(text: str) -> bytes:
    """Create a test image with text."""
    im = Image.new("1", (OLED_WIDTH, OLED_HEIGHT), color=0)
    draw = ImageDraw.Draw(im)
    # Use default font
    draw.text((10, 10), text, fill=255)
    return im.tobytes()


def diagnose() -> None:
    """Print diagnostic information about detected SteelSeries devices."""
    print("=" * 70)
    print("SteelSeries OLED Diagnostic Tool")
    print("=" * 70)
    print()

    # Find all SteelSeries devices
    all_devices = hid.enumerate(VENDOR_ID, 0)

    if not all_devices:
        print("ERROR: No SteelSeries devices found!")
        print("Make sure your keyboard is connected.")
        return

    print(f"Found {len(all_devices)} SteelSeries HID interface(s):")
    print()

    # Group by product ID
    by_pid: dict[int, list[dict]] = {}
    for dev_info in all_devices:
        pid = dev_info["product_id"]
        if pid not in by_pid:
            by_pid[pid] = []
        by_pid[pid].append(dev_info)

    for pid, devices in sorted(by_pid.items()):
        name = SUPPORTED_PIDS.get(pid, f"Unknown (0x{pid:04X})")
        is_gen3 = pid in GEN3_PIDS
        gen_label = " [GEN3]" if is_gen3 else ""

        print(f"Product: {name}{gen_label}")
        print(f"  PID: 0x{pid:04X}")
        print(f"  Interfaces found: {len(devices)}")
        print()

        for dev_info in devices:
            interface = dev_info.get("interface_number", "?")
            usage_page = dev_info.get("usage_page")
            usage = dev_info.get("usage")
            path = dev_info.get("path", b"?")

            up_str = f"0x{usage_page:04X}" if usage_page is not None else "N/A"
            u_str = f"0x{usage:04X}" if usage is not None else "N/A"

            print(f"    Interface {interface}:")
            print(f"      Usage Page: {up_str}")
            print(f"      Usage: {u_str}")
            print(f"      Path: {path}")
            print()

    print("=" * 70)
    print("Current Code Analysis:")
    print("=" * 70)
    print()

    # Check which interface the current code would select
    from steelseries_oled.constants import INTERFACE_ORDER

    selected = None
    selected_interface = None
    is_gen3 = False

    for interface in INTERFACE_ORDER:
        for dev_info in hid.enumerate(VENDOR_ID, 0):
            if dev_info["product_id"] not in SUPPORTED_PIDS:
                continue
            if dev_info.get("interface_number") != interface:
                continue
            selected = dev_info
            selected_interface = interface
            break
        if selected:
            break

    if selected:
        pid = selected["product_id"]
        name = SUPPORTED_PIDS.get(pid, "Unknown")
        is_gen3 = pid in GEN3_PIDS

        print("Current code selects:")
        print(f"  Device: {name}")
        print(f"  PID: 0x{pid:04X}")
        print(f"  Interface: {selected_interface}")
        print()

        if is_gen3:
            print("⚠️  Gen3 device detected!")
            print("   Gen3 keyboards may use a different interface for OLED.")
            if selected_interface == 1:
                print("   Currently selecting interface 1 (legacy)")
                print("   Try interface 0 or 2 instead.")
            print()
    else:
        print("No compatible device found!")
        return

    print("=" * 70)
    print("OLED Interface Test (watch your keyboard!)")
    print("=" * 70)
    print()

    # Try to identify which interface accepts the OLED report
    test_results: list[tuple[int | str, bool, str | None]] = []

    for pid, devices in by_pid.items():
        if pid not in SUPPORTED_PIDS:
            continue

        name = SUPPORTED_PIDS[pid]

        for dev_info in devices:
            interface = dev_info.get("interface_number", "?")
            print(f"Testing {name} interface {interface}...", end=" ", flush=True)

            try:
                dev = hid.device()
                dev.open_path(dev_info["path"])

                # Create test image with interface number
                test_image = create_test_image(f"IF {interface} TEST")

                # Send test image with report ID 0x61
                report = bytearray([0x61]) + bytearray(test_image) + bytearray([0x00])
                dev.send_feature_report(bytes(report))

                print(f"✓ SENT - Check if OLED shows 'IF {interface} TEST'")
                test_results.append((interface, True, None))

                # Keep displayed for 2 seconds
                time.sleep(2)

                # Blank the screen
                blank_report = bytes([0x61] + [0x00] * 641)
                dev.send_feature_report(blank_report)

                dev.close()

            except Exception as e:
                print(f"✗ Failed: {e}")
                test_results.append((interface, False, str(e)))

    print()
    print("=" * 70)
    print("Results Summary:")
    print("=" * 70)
    print()

    successful = [r for r in test_results if r[1]]
    failed = [r for r in test_results if not r[1]]

    if successful:
        print("Interfaces that accepted the report:")
        for interface, _, _ in successful:
            print(f"  ✓ Interface {interface}")
        print()
        print("If you SAW text on the OLED, that's the correct interface!")
        print("If no text appeared despite 'SENT' status, the report format")
        print("may be different for Gen3 keyboards.")
    else:
        print("No interfaces accepted the OLED report!")
        print("This suggests either:")
        print("  1. Different report ID for Gen3")
        print("  2. Different report format")
        print("  3. Device permissions issue")

    if failed:
        print()
        print("Interfaces that failed:")
        for interface, _, error in failed:
            print(f"  ✗ Interface {interface}: {error}")

    print()
    print("=" * 70)
    print("Recommendations:")
    print("=" * 70)
    print()

    if is_gen3:
        print("For Gen3 keyboards:")
        print("  1. If text appeared on one interface, note which one")
        print("  2. If no text appeared but send succeeded, Gen3 may use")
        print("     a different protocol (different report ID or format)")
        print("  3. Consider using Wireshark+USBPcap to capture traffic")
        print("     from SteelSeries GG software to reverse-engineer protocol")


if __name__ == "__main__":
    diagnose()

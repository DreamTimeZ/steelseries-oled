"""Keyboard profile switching."""

from steelseries_oled.constants import GEN3_PIDS
from steelseries_oled.device import find_device, open_device
from steelseries_oled.exceptions import Gen3NotSupportedError


def switch_profile(profile_number: int) -> None:
    """Switch the keyboard to a different profile.

    Args:
        profile_number: The profile number to switch to.

    Raises:
        DeviceNotFoundError: If no compatible device is found.
        DeviceCommunicationError: If the command fails.
        Gen3NotSupportedError: If a Gen3 keyboard is detected (not supported).
    """
    # Check if device is Gen3 (profile switching not supported)
    device_info = find_device()
    if device_info["product_id"] in GEN3_PIDS:
        msg = (
            "Profile switching via HID is not supported on Gen3 keyboards. "
            "Use SteelSeries key + F9 (profile switcher) on the keyboard."
        )
        raise Gen3NotSupportedError(msg)

    with open_device(blank_on_exit=False) as device:
        device.set_profile(profile_number)

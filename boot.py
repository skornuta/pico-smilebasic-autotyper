# Switch-oriented USB keyboard for CircuitPython.
# Windows accepts default CircuitPython HID; the Switch often needs a plain
# boot-protocol keyboard with no mass storage / serial / midi.
#
# RECOVERY (get CIRCUITPY back without reflashing):
#   Before plugging into the computer, connect GP15 to GND (use a jumper wire).
#   That enables maintenance mode: drive + serial stay on, HID still works.
#   Then delete or rename boot.py, or leave GP15 grounded while editing.

import board
import digitalio
import storage
import usb_cdc
import usb_hid
import usb_midi

# Standard HID boot keyboard descriptor (8-byte report, no report ID).
# Used by BIOSes / picky hosts; closer to a normal USB keyboard than CP default.
BOOT_KEYBOARD_DESCRIPTOR = bytes((
    0x05, 0x01,        # Usage Page (Generic Desktop)
    0x09, 0x06,        # Usage (Keyboard)
    0xA1, 0x01,        # Collection (Application)
    0x05, 0x07,        #   Usage Page (Key Codes)
    0x19, 0xE0,        #   Usage Minimum (224)
    0x29, 0xE7,        #   Usage Maximum (231)
    0x15, 0x00,        #   Logical Minimum (0)
    0x25, 0x01,        #   Logical Maximum (1)
    0x75, 0x01,        #   Report Size (1)
    0x95, 0x08,        #   Report Count (8)
    0x81, 0x02,        #   Input (Data, Variable, Absolute) ; modifier byte
    0x95, 0x01,        #   Report Count (1)
    0x75, 0x08,        #   Report Size (8)
    0x81, 0x01,        #   Input (Constant) ; reserved
    0x95, 0x05,        #   Report Count (5)
    0x75, 0x01,        #   Report Size (1)
    0x05, 0x08,        #   Usage Page (LEDs)
    0x19, 0x01,        #   Usage Minimum (1)
    0x29, 0x05,        #   Usage Maximum (5)
    0x91, 0x02,        #   Output (Data, Variable, Absolute) ; LED report
    0x95, 0x01,        #   Report Count (1)
    0x75, 0x03,        #   Report Size (3)
    0x91, 0x01,        #   Output (Constant) ; LED padding
    0x95, 0x06,        #   Report Count (6)
    0x75, 0x08,        #   Report Size (8)
    0x15, 0x00,        #   Logical Minimum (0)
    0x26, 0xFF, 0x00,  #   Logical Maximum (255)
    0x05, 0x07,        #   Usage Page (Key Codes)
    0x19, 0x00,        #   Usage Minimum (0)
    0x2A, 0xFF, 0x00,  #   Usage Maximum (255)
    0x81, 0x00,        #   Input (Data, Array) ; 6 keycodes
    0xC0,              # End Collection
))

# GP15 low at boot = maintenance mode (CIRCUITPY visible).
maintain = digitalio.DigitalInOut(board.GP15)
maintain.switch_to_input(pull=digitalio.Pull.UP)
maintenance_mode = not maintain.value

boot_keyboard = usb_hid.Device(
    report_descriptor=BOOT_KEYBOARD_DESCRIPTOR,
    usage_page=0x01,  # Generic Desktop
    usage=0x06,       # Keyboard
    report_ids=(0,),
    in_report_lengths=(8,),
    out_report_lengths=(1,),
)

if maintenance_mode:
    # Drive + serial stay available for editing. Still expose boot keyboard.
    usb_midi.disable()
    usb_hid.enable((boot_keyboard,), boot_device=1)
else:
    storage.disable_usb_drive()
    usb_cdc.disable()
    usb_midi.disable()
    usb_hid.enable((boot_keyboard,), boot_device=1)

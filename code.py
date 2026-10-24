# Raspberry Pi Pico CircuitPython auto-typer for SmileBASIC.
#
# CIRCUITPY contents:
#   boot.py          (required for Switch — HID-only USB)
#   code.py
#   bootstrap.bas
#   lib/adafruit_hid/  (from Adafruit CircuitPython HID library)
#
# Test on a Mac first (TextEdit) before using the Switch.
# On Switch: open SmileBASIC -> Make a Program -> slot 0, then plug Pico.
# Unplug any other USB keyboard while testing.
#
# LED (onboard):
#   slow blink  = waiting to start
#   toggling    = typing
#   steady on   = finished
#   3-blink loop = error (missing lib/file)

import time
import board
import digitalio
import usb_hid

try:
    from adafruit_hid.keyboard import Keyboard
    from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
    from adafruit_hid.keycode import Keycode
except ImportError:
    Keyboard = None

START_DELAY_S = 8.0
LINE_DELAY_S = 0.15
CHAR_DELAY_S = 0.01
BOOTSTRAP_PATH = "bootstrap.bas"


def led_pin():
    led = digitalio.DigitalInOut(board.LED)
    led.direction = digitalio.Direction.OUTPUT
    return led


def blink(led, times=3, on=0.15, off=0.15):
    for _ in range(times):
        led.value = True
        time.sleep(on)
        led.value = False
        time.sleep(off)


def error_loop(led):
    while True:
        blink(led, 3, 0.1, 0.1)
        time.sleep(0.7)


def wait_with_blink(led, seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        led.value = True
        time.sleep(0.25)
        led.value = False
        time.sleep(0.25)


def main():
    led = led_pin()

    if Keyboard is None:
        error_loop(led)

    try:
        with open(BOOTSTRAP_PATH, "r", encoding="utf-8") as handle:
            lines = handle.read().splitlines()
    except OSError:
        error_loop(led)

    wait_with_blink(led, START_DELAY_S)

    keyboard = Keyboard(usb_hid.devices)
    layout = KeyboardLayoutUS(keyboard)
    time.sleep(0.5)

    for index, line in enumerate(lines):
        led.value = index % 2 == 0
        try:
            if CHAR_DELAY_S > 0:
                for ch in line:
                    layout.write(ch)
                    time.sleep(CHAR_DELAY_S)
                keyboard.send(Keycode.ENTER)
            else:
                layout.write(line + "\n")
        except Exception:
            keyboard.release_all()
            try:
                keyboard.send(Keycode.ENTER)
            except Exception:
                pass
        time.sleep(LINE_DELAY_S)

    keyboard.release_all()
    led.value = True
    while True:
        time.sleep(1.0)


if __name__ == "__main__":
    main()

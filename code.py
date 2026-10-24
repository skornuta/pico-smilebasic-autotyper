# Raspberry Pi Pico CircuitPython auto-typer for SmileBASIC.
#
# Types bootstrap.bas into SmileBASIC.
# Strips leading indent: SB auto-indents on Enter inside DEF/FOR/IF, and if we
# also type file spaces the indent stacks (works at the start, breaks later).
# After each Enter: HOME + Ctrl+DELETE + Shift+TAB clears auto-indent, then
# the next line is typed with no leading spaces (valid SmileBASIC).
#
# CIRCUITPY: boot.py, code.py, bootstrap.bas, lib/adafruit_hid/
# LED: slow blink=wait, toggle=typing, solid=done, 3-blink=error

import time
import board
import digitalio
import usb_hid

try:
    from adafruit_hid.keyboard import Keyboard
    from adafruit_hid.keycode import Keycode
except ImportError:
    Keyboard = None

BOOTSTRAP_PATH = "bootstrap.bas"

START_DELAY_S = 8.0
KEY_DOWN_S = 0.025
KEY_UP_S = 0.025
CHAR_GAP_S = 0.02
LINE_DELAY_S = 0.12
SHIFT_SETTLE_S = 0.02


def build_keymap():
    """ASCII char -> (keycode, needs_shift). US QWERTY only."""
    km = {}
    letters = "abcdefghijklmnopqrstuvwxyz"
    for i, ch in enumerate(letters):
        code = Keycode.A + i
        km[ch] = (code, False)
        km[ch.upper()] = (code, True)

    pairs = [
        ("1", Keycode.ONE, False), ("!", Keycode.ONE, True),
        ("2", Keycode.TWO, False), ("@", Keycode.TWO, True),
        ("3", Keycode.THREE, False), ("#", Keycode.THREE, True),
        ("4", Keycode.FOUR, False), ("$", Keycode.FOUR, True),
        ("5", Keycode.FIVE, False), ("%", Keycode.FIVE, True),
        ("6", Keycode.SIX, False), ("^", Keycode.SIX, True),
        ("7", Keycode.SEVEN, False), ("&", Keycode.SEVEN, True),
        ("8", Keycode.EIGHT, False), ("*", Keycode.EIGHT, True),
        ("9", Keycode.NINE, False), ("(", Keycode.NINE, True),
        ("0", Keycode.ZERO, False), (")", Keycode.ZERO, True),
        ("-", Keycode.MINUS, False), ("_", Keycode.MINUS, True),
        ("=", Keycode.EQUALS, False), ("+", Keycode.EQUALS, True),
        ("[", Keycode.LEFT_BRACKET, False), ("{", Keycode.LEFT_BRACKET, True),
        ("]", Keycode.RIGHT_BRACKET, False), ("}", Keycode.RIGHT_BRACKET, True),
        ("\\", Keycode.BACKSLASH, False), ("|", Keycode.BACKSLASH, True),
        (";", Keycode.SEMICOLON, False), (":", Keycode.SEMICOLON, True),
        ("'", Keycode.QUOTE, False), ('"', Keycode.QUOTE, True),
        ("`", Keycode.GRAVE_ACCENT, False), ("~", Keycode.GRAVE_ACCENT, True),
        (",", Keycode.COMMA, False), ("<", Keycode.COMMA, True),
        (".", Keycode.PERIOD, False), (">", Keycode.PERIOD, True),
        ("/", Keycode.FORWARD_SLASH, False), ("?", Keycode.FORWARD_SLASH, True),
        (" ", Keycode.SPACE, False),
        ("\t", Keycode.TAB, False),
    ]
    for ch, code, shift in pairs:
        km[ch] = (code, shift)
    return km


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


def clear_caps_lock(keyboard):
    try:
        if keyboard.led_on(Keyboard.LED_CAPS_LOCK):
            keyboard.send(Keycode.CAPS_LOCK)
            time.sleep(0.15)
            keyboard.release_all()
            time.sleep(0.15)
    except Exception:
        pass


def tap(keyboard, keycode, shift=False):
    keyboard.release_all()
    time.sleep(0.01)
    if shift:
        keyboard.press(Keycode.SHIFT)
        time.sleep(SHIFT_SETTLE_S)
        keyboard.press(keycode)
        time.sleep(KEY_DOWN_S)
        keyboard.release(keycode)
        time.sleep(KEY_UP_S)
        keyboard.release(Keycode.SHIFT)
    else:
        keyboard.press(keycode)
        time.sleep(KEY_DOWN_S)
        keyboard.release(keycode)
    time.sleep(KEY_UP_S)
    keyboard.release_all()
    time.sleep(CHAR_GAP_S)


def type_char(keyboard, keymap, ch):
    if ch == "\r":
        return
    if ch == "\n":
        tap(keyboard, Keycode.ENTER, False)
        return
    if ch not in keymap:
        raise ValueError("unmapped char %r" % (ch,))
    code, shift = keymap[ch]
    tap(keyboard, code, shift)


def load_lines(path):
    """Lines with leading indent removed (SB auto-indent handles cosmetics)."""
    with open(path, "rb") as handle:
        raw = handle.read()
    text = raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.lstrip(" \t") for line in text.split("\n")]
    if lines and lines[-1] == "":
        lines = lines[:-1]
    return lines


def validate_lines(lines, keymap):
    for line in lines:
        for ch in line:
            if ch not in keymap:
                return False
    return True


def clear_auto_indent(keyboard):
    """Undo SmileBASIC auto-indent on the current empty/new line."""
    # HOME = head of line
    tap(keyboard, Keycode.HOME, False)
    time.sleep(0.02)

    # Ctrl+DELETE = delete right side (auto-inserted spaces)
    keyboard.release_all()
    time.sleep(0.01)
    keyboard.press(Keycode.CONTROL)
    time.sleep(SHIFT_SETTLE_S)
    keyboard.press(Keycode.DELETE)
    time.sleep(KEY_DOWN_S)
    keyboard.release(Keycode.DELETE)
    time.sleep(KEY_UP_S)
    keyboard.release(Keycode.CONTROL)
    keyboard.release_all()
    time.sleep(0.02)

    # Shift+TAB unindent a few levels (SB maps this to Unindent)
    for _ in range(6):
        keyboard.release_all()
        time.sleep(0.005)
        keyboard.press(Keycode.SHIFT)
        time.sleep(SHIFT_SETTLE_S)
        keyboard.press(Keycode.TAB)
        time.sleep(KEY_DOWN_S)
        keyboard.release(Keycode.TAB)
        time.sleep(KEY_UP_S)
        keyboard.release(Keycode.SHIFT)
        keyboard.release_all()
        time.sleep(0.015)

    tap(keyboard, Keycode.HOME, False)
    time.sleep(0.02)


def type_line(keyboard, keymap, line):
    for ch in line:
        type_char(keyboard, keymap, ch)


def main():
    led = led_pin()
    if Keyboard is None:
        error_loop(led)

    keymap = build_keymap()
    try:
        lines = load_lines(BOOTSTRAP_PATH)
    except OSError:
        error_loop(led)

    if not validate_lines(lines, keymap):
        error_loop(led)

    wait_with_blink(led, START_DELAY_S)

    keyboard = Keyboard(usb_hid.devices)
    time.sleep(0.5)
    clear_caps_lock(keyboard)
    time.sleep(0.3)

    clear_auto_indent(keyboard)

    for index, line in enumerate(lines):
        led.value = index % 2 == 0
        try:
            type_line(keyboard, keymap, line)
            type_char(keyboard, keymap, "\n")
            time.sleep(LINE_DELAY_S)
            if index + 1 < len(lines):
                clear_auto_indent(keyboard)
        except Exception:
            keyboard.release_all()
            error_loop(led)

    keyboard.release_all()
    led.value = True
    while True:
        time.sleep(1.0)


if __name__ == "__main__":
    main()

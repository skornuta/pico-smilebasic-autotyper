# Raspberry Pi Pico CircuitPython auto-typer for SmileBASIC.
#
# SmileBASIC sticky indent: after Enter, the new line KEEPS the previous
# line's indentation. If we also type the file's leading spaces, indent
# stacks and later lines break. Fix: track indent depth and only type the
# delta (extra spaces or Backspace), then type the code with no leading ws.
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


def leading_indent(line):
    """Count leading ASCII spaces (tabs count as 1 each if present)."""
    n = 0
    for ch in line:
        if ch == " ":
            n += 1
        elif ch == "\t":
            n += 1
        else:
            break
    return n


def load_lines(path):
    with open(path, "rb") as handle:
        raw = handle.read()
    text = raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    return lines


def validate_lines(lines, keymap):
    for line in lines:
        body = line.lstrip(" \t")
        for ch in body:
            if ch not in keymap:
                return False
    return True


def adjust_indent(keyboard, keymap, current, desired):
    """Match sticky editor indent to the desired leading-space count."""
    if desired > current:
        for _ in range(desired - current):
            type_char(keyboard, keymap, " ")
    elif desired < current:
        # Cursor sits after sticky indent spaces; backspace removes them.
        for _ in range(current - desired):
            tap(keyboard, Keycode.BACKSPACE, False)
    # desired == current: already correct, type nothing


def type_body(keyboard, keymap, body):
    for ch in body:
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

    # Sticky indent level the editor will keep after the next Enter.
    current_indent = 0

    for index, line in enumerate(lines):
        led.value = index % 2 == 0
        desired = leading_indent(line)
        body = line.lstrip(" \t")
        try:
            adjust_indent(keyboard, keymap, current_indent, desired)
            type_body(keyboard, keymap, body)
            # Enter: next line keeps THIS line's indent (sticky).
            type_char(keyboard, keymap, "\n")
            current_indent = desired
            time.sleep(LINE_DELAY_S)
        except Exception:
            keyboard.release_all()
            error_loop(led)

    keyboard.release_all()
    led.value = True
    while True:
        time.sleep(1.0)


if __name__ == "__main__":
    main()

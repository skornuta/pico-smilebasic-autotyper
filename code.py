# Raspberry Pi Pico CircuitPython auto-typer for SmileBASIC.
#
# Types bootstrap.bas exactly: spaces, caps, symbols, newlines.
# Explicit US keycodes with slow press/release (no layout.write bursts).
#
# CIRCUITPY:
#   boot.py, code.py, bootstrap.bas, lib/adafruit_hid/
#
# LED: slow blink=wait, toggle=typing, solid=done, 3-blink loop=error

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

# Deliberately slow — hosts drop keys if press/release is too short.
START_DELAY_S = 8.0
KEY_DOWN_S = 0.018      # how long each key is held
KEY_UP_S = 0.018        # gap after release before next key
CHAR_GAP_S = 0.012      # extra gap between characters
LINE_DELAY_S = 0.10     # pause after Enter (SmileBASIC-friendly)
SHIFT_SETTLE_S = 0.015  # wait after pressing Shift before the key


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
    """If host Caps Lock is on, letters invert — toggle it off once."""
    try:
        if keyboard.led_on(Keyboard.LED_CAPS_LOCK):
            keyboard.send(Keycode.CAPS_LOCK)
            time.sleep(0.15)
            keyboard.release_all()
            time.sleep(0.15)
    except Exception:
        pass


def tap(keyboard, keycode, shift=False):
    """One clean keystroke with full press/release and no stuck modifiers."""
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


def load_source(path):
    """Read exact text; keep spaces; normalize only CR/LF to \\n."""
    with open(path, "rb") as handle:
        raw = handle.read()
    text = raw.decode("utf-8")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.endswith("\n"):
        text += "\n"
    return text


def validate(text, keymap):
    for ch in text:
        if ch in ("\n", "\r"):
            continue
        if ch not in keymap:
            return False
    return True


def main():
    led = led_pin()
    if Keyboard is None:
        error_loop(led)

    keymap = build_keymap()
    try:
        text = load_source(BOOTSTRAP_PATH)
    except OSError:
        error_loop(led)

    if not validate(text, keymap):
        error_loop(led)

    wait_with_blink(led, START_DELAY_S)

    keyboard = Keyboard(usb_hid.devices)
    time.sleep(0.5)
    clear_caps_lock(keyboard)
    time.sleep(0.3)

    # Character-by-character, including leading spaces on nested DEF bodies.
    index = 0
    length = len(text)
    while index < length:
        ch = text[index]
        led.value = (index // 8) % 2 == 0
        try:
            type_char(keyboard, keymap, ch)
        except Exception:
            keyboard.release_all()
            error_loop(led)
        if ch == "\n":
            time.sleep(LINE_DELAY_S)
        index += 1

    keyboard.release_all()
    led.value = True
    while True:
        time.sleep(1.0)


if __name__ == "__main__":
    main()

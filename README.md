# Pico SmileBASIC Auto-Typer

CircuitPython package for a **Raspberry Pi Pico** that types `bootstrap.bas` into SmileBASIC like a USB keyboard.

Almost drag-and-drop: flash the UF2, copy the rest onto **CIRCUITPY**, plug into the Switch.

## What you need

- Raspberry Pi Pico (RP2040)
- A computer (Mac / Windows / Linux)
- Nintendo Switch or Switch 2 with SmileBASIC open to **Make a Program → slot 0**

## Folder layout

```text
.
├── firmware/
│   └── adafruit-circuitpython-raspberry_pi_pico-en_US-10.3.1.uf2
├── lib/
│   └── adafruit_hid/     # prebundled for CircuitPython 10.x
├── boot.py               # Switch-friendly boot keyboard USB mode
├── code.py               # types bootstrap.bas after a short delay
├── bootstrap.bas         # source typed into SmileBASIC
└── README.md
```

## Install

### 1. Flash CircuitPython

1. Hold the Pico **BOOTSEL** button.
2. Plug the Pico into your computer, then release **BOOTSEL**.
3. A drive named **RPI-RP2** appears.
4. Copy this file onto **RPI-RP2**:

   `firmware/adafruit-circuitpython-raspberry_pi_pico-en_US-10.3.1.uf2`

5. The Pico reboots. A drive named **CIRCUITPY** appears.

### 2. Copy the app files

Copy these onto **CIRCUITPY** (not the `firmware/` folder):

- `code.py`
- `boot.py`
- `bootstrap.bas`
- `lib/` (entire folder, so you get `lib/adafruit_hid/`)

Final layout on the board:

```text
CIRCUITPY/
  boot.py
  code.py
  bootstrap.bas
  lib/
    adafruit_hid/
      __init__.mpy
      keyboard.mpy
      ...
```

After `boot.py` runs on the next plug-in, **CIRCUITPY may disappear**. That is intentional so the Switch sees a plain keyboard. See [Recovery](#recovery-edit-files-again).

### 3. Test on a computer first

1. Open Notepad or TextEdit and click in the window.
2. Unplug and replug the Pico.
3. The onboard LED should slow-blink for about 8 seconds, then type the BASIC source.
4. A repeating **3-blink** pattern means `lib/adafruit_hid` or `bootstrap.bas` is missing.

### 4. Use on the Switch

1. Open SmileBASIC → **Make a Program** → **slot 0** (cursor in the editor).
2. Unplug other USB keyboards if possible.
3. Plug the Pico into the dock or USB-C port.
4. Wait for the LED blink, then typing.
5. When finished (LED steady on), save the program as **NS2**.

## LED meanings

| Pattern | Meaning |
|---|---|
| Slow blink (~8s) | Waiting for USB host / editor focus |
| Toggling | Typing lines |
| Steady on | Finished |
| 3 quick blinks, repeat | Missing `adafruit_hid` or `bootstrap.bas` |

## Recovery (edit files again)

`boot.py` hides the USB mass-storage drive so picky hosts (like the Switch) accept the device as a keyboard.

### Option A — maintenance jumper (no reflash)

1. Connect **GP15** to **GND** with a jumper wire.
2. Plug into the computer.
3. **CIRCUITPY** should mount. Edit files, then remove the jumper.

### Option B — reflash CircuitPython

1. Hold **BOOTSEL**, plug in, release.
2. Drop the `.uf2` from `firmware/` onto **RPI-RP2**.
3. **CIRCUITPY** returns; copy the app files again.
4. Add `boot.py` last when you are ready for Switch use.


## Auto-indent note

SmileBASIC inserts indent on Enter inside `DEF` / `FOR` / `IF` blocks. This package
**strips leading spaces** from `bootstrap.bas` when typing and clears auto-indent
(HOME, Ctrl+Delete, Shift+Tab) before each line so spacing does not stack and break
later lines (e.g. around line 147). Leading indent is cosmetic in SmileBASIC.

## Timing knobs

Edit the top of `code.py` (in maintenance mode). Balanced defaults aim for ~8–10 minutes:

- `START_DELAY_S` — wait after plug-in (default `8.0`)
- `KEY_DOWN_S` / `KEY_UP_S` — key hold and release (default `0.025`)
- `CHAR_GAP_S` — gap between characters (default `0.02`)
- `LINE_DELAY_S` — pause after Enter (default `0.12`)
- `SHIFT_SETTLE_S` — delay after pressing Shift (default `0.02`)

If symbols/`#`/`$` drop, increase `KEY_DOWN_S`, `KEY_UP_S`, and `CHAR_GAP_S` slightly.

## Board notes

- Firmware in this repo is for the **original Raspberry Pi Pico (RP2040)**.
- Pico W / Pico 2 need a different CircuitPython `.uf2` from [circuitpython.org](https://circuitpython.org/downloads). Keep the same `code.py`, `boot.py`, and `lib`.

## Credits

- [CircuitPython](https://circuitpython.org/) by Adafruit Industries
- [Adafruit_CircuitPython_HID](https://github.com/adafruit/Adafruit_CircuitPython_HID)

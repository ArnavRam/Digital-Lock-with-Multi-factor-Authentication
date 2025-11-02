from machine import Pin
import time

class Keypad:
    def __init__(self, pins, keymap):
        if len(pins) != 8:
            raise ValueError("You must provide 8 pins for a 4x4 keypad.")
        if len(keymap) != 4 or any(len(row) != 4 for row in keymap):
            raise ValueError("Keymap must be a 4x4 matrix.")

        self._row_pins = [Pin(p, Pin.OUT) for p in pins[:4]]
        self._col_pins = [Pin(p, Pin.IN, Pin.PULL_UP) for p in pins[4:]]
        self._keymap = keymap
        self._last_key = None
        self._last_press_time = 0
        # Increased debounce delay for membrane keypads
        self._debounce_ms = 200

    def get_key(self):
        for r, row_pin in enumerate(self._row_pins):
            row_pin.value(0)
            for c, col_pin in enumerate(self._col_pins):
                if col_pin.value() == 0:
                    row_pin.value(1) # reset row pin
                    
                    # Debounce logic
                    current_time = time.ticks_ms()
                    if current_time - self._last_press_time > self._debounce_ms:
                        self._last_press_time = current_time
                        return self._keymap[r][c]
            row_pin.value(1)
        return None



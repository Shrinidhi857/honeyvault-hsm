"""
test_button.py
Standalone GPIO 17 button test for Raspberry Pi Zero 2 W.

Run this on the Pi terminal BEFORE starting app.py to verify
your tactile button wiring is correct.

Wiring:
  GPIO 17 (Pin 11) ── [tactile button] ── GND (Pin 9)

Usage:
  python3 test_button.py
"""

import sys
import time

try:
    import RPi.GPIO as GPIO
except ImportError:
    print("ERROR: RPi.GPIO not found. Run this script on your Raspberry Pi.")
    print("       Install with: pip install RPi.GPIO")
    sys.exit(1)

BUTTON_PIN = 17
TIMEOUT    = 10  # seconds to wait for a press

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

print("=" * 50)
print("  HoneyVault — GPIO 17 Button Test")
print("=" * 50)
print(f"  Pin     : GPIO {BUTTON_PIN} (BCM)")
print(f"  Pull-up : enabled (reads HIGH at rest)")
print(f"  Press   : connects GPIO 17 to GND (reads LOW)")
print("=" * 50)
print(f"\nWaiting {TIMEOUT}s for button press... press it now!\n")

deadline = time.time() + TIMEOUT
pressed  = False

try:
    while time.time() < deadline:
        remaining = int(deadline - time.time()) + 1
        print(f"  [{remaining:02d}s] waiting for GPIO 17 LOW...", end="\r")

        if GPIO.input(BUTTON_PIN) == GPIO.LOW:
            print()
            print("\n  PASSED — Button press detected on GPIO 17!")
            print("  Your wiring is correct. app.py hardware gate will work.\n")
            pressed = True
            # Debounce: wait for release
            while GPIO.input(BUTTON_PIN) == GPIO.LOW:
                time.sleep(0.01)
            break

        time.sleep(0.05)

except KeyboardInterrupt:
    print("\n\n  Test interrupted by user.")

finally:
    GPIO.cleanup()
    print("  GPIO cleanup done.")

if not pressed:
    print()
    print("  FAILED — No button press detected within 10 seconds.")
    print("  Check your wiring: GPIO 17 (Pin 11) -> button -> GND (Pin 9)")
    print()

import time
import logging

logger = logging.getLogger(__name__)

try:
    import RPi.GPIO as GPIO
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False
    GPIO = None

BUTTON_PIN = 17   # BCM pin number (GPIO 17 wired to one leg of tactile button, GND to other)

if HAS_GPIO:
    try:
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        # Internal pull-up: pin reads HIGH normally, LOW when button pressed to GND
        GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        logger.info("GPIO 17 configured as INPUT with PULL_UP.")
    except Exception as exc:
        logger.error(f"GPIO init failed: {exc}")
        HAS_GPIO = False
else:
    logger.warning(
        "RPi.GPIO not found (running on non-Pi host). "
        "Physical button gate will wait the full timeout then deny. "
        "Deploy this code to your Raspberry Pi to enable real hardware confirmation."
    )


def wait_for_button_press(timeout=10.0) -> bool:
    """
    Block until GPIO 17 button is pressed (pin goes LOW) within timeout seconds.

    On Raspberry Pi with RPi.GPIO installed:
        Polls GPIO 17 every 50 ms. Returns True when the button is pressed.

    On any other host (Windows, macOS, etc.):
        Waits the full timeout so the UI countdown completes, then returns False.
        The unlock request is denied — hardware presence cannot be confirmed
        without the physical button on the Pi.

    Returns:
        True  -- button was pressed within timeout (Pi only)
        False -- timeout elapsed, or not running on Pi
    """
    deadline = time.time() + timeout

    if HAS_GPIO:
        logger.info(f"Hardware gate OPEN — waiting {timeout}s for button on GPIO {BUTTON_PIN}...")
        while time.time() < deadline:
            try:
                if GPIO.input(BUTTON_PIN) == GPIO.LOW:
                    logger.info("Physical button press confirmed on GPIO 17.")
                    return True
            except Exception as exc:
                logger.error(f"GPIO read error: {exc}")
            time.sleep(0.05)
        logger.warning("Hardware gate TIMEOUT — request denied.")
        return False

    else:
        # No GPIO available — block for full duration so frontend countdown runs,
        # then deny.  This path only triggers on non-Pi development hosts.
        logger.warning(
            f"No GPIO available. Blocking for {timeout}s then denying (deploy to Pi for real gate)."
        )
        remaining = deadline - time.time()
        if remaining > 0:
            time.sleep(remaining)
        return False

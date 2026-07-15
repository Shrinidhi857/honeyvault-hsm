import time
import logging

logger = logging.getLogger(__name__)

try:
    import RPi.GPIO as GPIO
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False
    GPIO = None

BUTTON_PIN = 17   # BCM pin number

if HAS_GPIO:
    try:
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        logger.info("GPIO 17 configured as INPUT with PULL_UP.")
    except Exception as exc:
        logger.error(f"GPIO init failed: {exc}")
        HAS_GPIO = False
else:
    logger.error("RPi.GPIO library is missing! Real hardware mode is required.")

def wait_for_button_press(timeout=10.0) -> bool:
    """
    Block until GPIO 17 button is pressed (LOW state).
    Returns True if the button is pressed within timeout, False otherwise.
    """
    if not HAS_GPIO:
        logger.error("RPi.GPIO is not available. Denying unlock request.")
        return False

    deadline = time.time() + timeout
    logger.info(f"Hardware gate OPEN - waiting {timeout}s for GPIO {BUTTON_PIN}...")

    while time.time() < deadline:
        try:
            if GPIO.input(BUTTON_PIN) == GPIO.LOW:
                logger.info("Physical button press confirmed on GPIO 17.")
                return True
        except Exception as exc:
            logger.error(f"GPIO read error: {exc}")
        time.sleep(0.05)

    logger.warning("Hardware gate TIMEOUT - request denied.")
    return False

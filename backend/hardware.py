import time, logging, threading
logger = logging.getLogger(__name__)
try:
    import RPi.GPIO as GPIO
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False
    GPIO = None
BUTTON_PIN = 17
if HAS_GPIO:
    try:
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    except Exception as exc:
        HAS_GPIO = False
_mock_event = threading.Event()
def press_mock_button():
    _mock_event.set()
def clear_mock_button():
    _mock_event.clear()
def wait_for_button_press(timeout=10.0):
    clear_mock_button()
    deadline = time.time() + timeout
    while time.time() < deadline:
        if HAS_GPIO:
            try:
                if GPIO.input(BUTTON_PIN) == GPIO.LOW:
                    return True
            except Exception:
                pass
        if _mock_event.wait(timeout=0.05):
            clear_mock_button()
            return True
    return False

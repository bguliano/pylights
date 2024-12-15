"""
Mock Implementation of gpiozero.LED

This script provides a mock implementation of the gpiozero.LED class for testing purposes.
It mimics the behavior of the real gpiozero.LED class and logs LED state changes to a JSON
file (`led_state.json`) for synchronization with a GUI or other monitoring tools.

Key Features:
- Mimics `gpiozero.LED` methods: `on()`, `off()`, `toggle()`, and the `value` property.
- Supports `LED.pin.number` to replicate the `gpiozero.LED` API.
- Logs state changes to a JSON file for external monitoring.

Usage:
- Replace the real gpiozero library with this mock file during testing.
- Use the same imports in your main script as if using the real gpiozero library:
    from gpiozero import LED
- This script will seamlessly replace the `gpiozero.LED` functionality without requiring
changes to your main code.

Integration:
- Combine this mock with a GUI script (e.g., `led_gui.py`) to visualize LED states
dynamically during testing.

Deployment:
- When deploying your code, simply replace this mock file with the actual gpiozero library.
"""
import json
from pathlib import Path
from threading import Lock

# Path for storing LED states
SYNC_FILE = Path("led_state.json")
FILE_LOCK = Lock()

# Initialize the file if it doesn't exist or is blank
if not SYNC_FILE.exists() or SYNC_FILE.read_text() == '':
    SYNC_FILE.write_text("{}")


class LED:
    """Mock implementation of gpiozero.LED using a file for synchronization."""

    class MockPin:
        """Mock pin to provide the `pin.number` attribute."""

        def __init__(self, number):
            self.number = number

    def __init__(self, pin):
        self.pin = LED.MockPin(pin)  # Initialize MockPin with the pin number
        self._value = False  # Initial state: OFF
        self._is_closed = False  # Track whether the LED is closed
        self._log_state()  # Log initial state

    def on(self):
        """Turn the LED on."""
        self._ensure_open()
        self._value = True
        self._log_state()

    def off(self):
        """Turn the LED off."""
        self._ensure_open()
        self._value = False
        self._log_state()

    def toggle(self):
        """Toggle the LED state."""
        self._ensure_open()
        self._value = not self._value
        self._log_state()

    @property
    def value(self):
        """Get the current state of the LED."""
        self._ensure_open()
        return self._value

    @value.setter
    def value(self, state):
        """Set the LED state."""
        self._ensure_open()
        self._value = bool(state)
        self._log_state()

    def __del__(self):
        """Close the LED when the object is deleted."""
        self.close()

    def close(self):
        """Close the LED and release resources."""
        if not self._is_closed:
            self._is_closed = True
            self._remove_state()

    def _log_state(self):
        """Log the current state to the synchronization file."""
        with FILE_LOCK:
            data = json.loads(SYNC_FILE.read_text())
            data[self.pin.number] = {"value": self._value}
            SYNC_FILE.write_text(json.dumps(data, indent=4))

    def _remove_state(self):
        """Remove the LED state from the synchronization file."""
        with FILE_LOCK:
            data = json.loads(SYNC_FILE.read_text())
            if str(self.pin.number) in data:
                del data[str(self.pin.number)]
            SYNC_FILE.write_text(json.dumps(data, indent=4))

    def _ensure_open(self):
        """Ensure the LED is not closed before performing operations."""
        if self._is_closed:
            raise RuntimeError("Operation on a closed LED is not allowed.")

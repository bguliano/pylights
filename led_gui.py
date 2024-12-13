import json
import tkinter as tk
from pathlib import Path
from tkinter import ttk

# Path for the synchronization file
SYNC_FILE = Path("led_state.json")


def start_gui():
    """GUI for dynamically displaying and updating LED states."""
    root = tk.Tk()
    root.title("Mock GPIOZero LED GUI")

    led_frames = {}  # Dictionary to track LED widgets

    def update_gui():
        """Update the GUI with the state of LEDs."""
        try:
            # Read the synchronization file
            with SYNC_FILE.open("r") as f:
                data = json.load(f)

            # Update or add LEDs
            for pin, info in data.items():
                if pin not in led_frames:
                    # Create a new frame for the LED
                    frame = ttk.Frame(root, padding=10)
                    frame.pack(fill=tk.X, padx=10, pady=5)

                    # LED label
                    label = ttk.Label(frame, text=f"LED {pin}", font=("Arial", 12))
                    label.pack(side=tk.LEFT, padx=10)

                    # LED rectangle to indicate state
                    canvas = tk.Canvas(frame, width=100, height=50, highlightthickness=0)
                    rect = canvas.create_rectangle(10, 10, 90, 40, fill="red", outline="black")
                    canvas.pack(side=tk.LEFT)

                    # Store widgets for this pin
                    led_frames[pin] = {"frame": frame, "label": label, "canvas": canvas, "rect": rect}

                # Update the rectangle's color based on the LED state
                color = "green" if info["value"] else "red"
                led_frames[pin]["canvas"].itemconfig(led_frames[pin]["rect"], fill=color)

            # Remove LEDs that are no longer in the data
            for pin in list(led_frames.keys()):
                if pin not in data:
                    led_frames[pin]["frame"].destroy()
                    del led_frames[pin]

        except FileNotFoundError:
            pass  # Ignore if the file doesn't exist yet
        except json.JSONDecodeError:
            pass  # Ignore invalid JSON (e.g., empty or partially written file)

        root.after(100, update_gui)  # Schedule the next update

    update_gui()  # Start the update loop
    root.mainloop()


if __name__ == "__main__":
    # Automatically start the GUI when the script is executed
    start_gui()

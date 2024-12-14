import json
import tkinter as tk
from pathlib import Path

# Path for the synchronization file
SYNC_FILE = Path("led_state.json")


def start_gui(update_interval_ms: int):
    """GUI for dynamically displaying and updating LED states."""
    root = tk.Tk()
    root.title("Mock GPIOZero LED GUI")

    led_frames = {}  # Dictionary to track LED widgets
    max_columns = 4  # Maximum columns for the grid

    def update_gui():
        """Update the GUI with the state of LEDs."""
        try:
            # Read the synchronization file
            with SYNC_FILE.open("r") as f:
                data = json.load(f)

            # Update or add LEDs
            for idx, (pin, info) in enumerate(data.items()):
                if pin not in led_frames:
                    # Calculate grid position
                    row, col = divmod(idx, max_columns)

                    # Create a canvas for the LED
                    canvas = tk.Canvas(root, width=100, height=50, highlightthickness=0)
                    rect = canvas.create_rectangle(10, 10, 90, 40, fill="red", outline="black")

                    # Add text inside the rectangle
                    text = canvas.create_text(50, 25, text=f"LED {pin}", font=("Arial", 10), fill="white")

                    # Place the canvas in the grid
                    canvas.grid(row=row, column=col, padx=10, pady=10)

                    # Store widgets for this pin
                    led_frames[pin] = {"canvas": canvas, "rect": rect, "text": text}

                # Update the rectangle's color based on the LED state
                color = "green" if info["value"] else "red"
                led_frames[pin]["canvas"].itemconfig(led_frames[pin]["rect"], fill=color)

            # Remove LEDs that are no longer in the data
            current_pins = set(data.keys())
            for pin in list(led_frames.keys()):
                if pin not in current_pins:
                    led_frames[pin]["canvas"].destroy()
                    del led_frames[pin]

        except FileNotFoundError:
            pass  # Ignore if the file doesn't exist yet
        except json.JSONDecodeError:
            pass  # Ignore invalid JSON (e.g., empty or partially written file)

        root.after(update_interval_ms, update_gui)  # Schedule the next update

    update_gui()  # Start the update loop
    root.mainloop()


if __name__ == "__main__":
    # Automatically start the GUI when the script is executed
    start_gui(500)

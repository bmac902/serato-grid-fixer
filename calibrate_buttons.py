"""
Button Calibration - Click each button to record its coordinates.
Updates config.json with the results.
"""

import json
import time
from pathlib import Path
from pynput import mouse

clicks = []

def on_click(x, y, button, pressed):
    if button == mouse.Button.left and pressed:
        clicks.append((x, y))
        return False  # Stop listener after each click

def capture_click(prompt: str) -> tuple:
    print(f"  --> {prompt}")
    print(f"      (click the button now...)")
    with mouse.Listener(on_click=on_click) as listener:
        listener.join()
    coord = clicks.pop()
    print(f"      Captured: {coord}")
    return coord

def save_coord(key: str, coord: tuple):
    """Save a single coordinate to config.json immediately."""
    config_path = Path(__file__).parent / "config.json"
    with open(config_path) as f:
        config = json.load(f)
    config["coordinates"]["grid_edit"][key] = list(coord)
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"      Saved to config.json ✓")

def main():
    print("=" * 55)
    print("SERATO BUTTON CALIBRATION")
    print("=" * 55)
    print()
    print("Make sure Serato is open and visible.")
    print("Each click is saved immediately - no data lost if interrupted.")
    print()
    input("Press Enter when ready...")
    print()

    steps = [
        ("edit_grid", "Step 1: Click the EDIT GRID button"),
        ("clear",     "Step 2: Click the CLEAR button (panel should be open)"),
        ("set",       "Step 3: Click the SET button"),
        ("save",      "Step 4: Click the SAVE button"),
    ]

    results = {}
    for key, prompt in steps:
        print(prompt)
        coord = capture_click(f"Click the button now")
        save_coord(key, coord)
        results[key] = coord
        time.sleep(0.3)
        print()

    print("=" * 55)
    print("All 4 buttons calibrated!")
    print()
    for k, v in results.items():
        print(f"  {k:<12}: {v}")
    print("=" * 55)
    print()
    print("Now run: python grid_fixer.py")

if __name__ == "__main__":
    main()

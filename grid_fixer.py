"""
Serato Grid Fixer

Press ~ at the exact position where you want the grid set.
That's it.

Automates: Edit Grid -> Clear -> Set -> Save -> Hot Cue 1 -> load next track
"""

import time
import json
from pathlib import Path

import keyboard
import pyautogui

import calibrate_buttons


REQUIRED_BUTTONS = ("edit_grid", "clear", "set", "save")


class GridFixer:
    def __init__(self, grid_coords: dict):
        self.grid_coords = grid_coords

    def log(self, msg: str):
        print(msg)

    def set_grid_here(self):
        """Click Edit Grid -> Clear -> Set -> Save -> Hot Cue 1 -> load next track."""
        self.log("[~] Setting grid at current position...")

        edit_grid = self.grid_coords.get("edit_grid")
        clear     = self.grid_coords.get("clear")
        set_btn   = self.grid_coords.get("set")
        save      = self.grid_coords.get("save")

        if not all([edit_grid, clear, set_btn, save]):
            self.log("[ERROR] Button coordinates not calibrated! Run: python calibrate_buttons.py")
            return

        pyautogui.click(edit_grid[0], edit_grid[1])
        time.sleep(0.4)

        pyautogui.click(clear[0], clear[1])
        time.sleep(0.3)

        pyautogui.click(set_btn[0], set_btn[1])
        time.sleep(0.3)

        pyautogui.click(save[0], save[1])
        time.sleep(0.4)

        self.log("[~] Grid set. Setting Hot Cue 1...")

        keyboard.press('ctrl'); keyboard.press('1')
        time.sleep(0.05)
        keyboard.release('1'); keyboard.release('ctrl')

        self.log("[~] Done.")

        # Auto-load next track using Serato's built-in shortcut (Alt+W)
        self.log("[~] Loading next track...")
        keyboard.press('alt'); keyboard.press('w')
        time.sleep(0.05)
        keyboard.release('w'); keyboard.release('alt')

        # Advance library cursor so the next ~ press loads the track after this one
        time.sleep(0.1)
        keyboard.send('down')


def load_grid_coords(config_path: Path) -> dict:
    """Load the grid_edit coords subsection from config.json (returns {} if missing)."""
    if not config_path.exists():
        return {}
    with open(config_path) as f:
        config = json.load(f)
    return config.get("coordinates", {}).get("grid_edit", {}) or {}


def coords_complete(grid_coords: dict) -> bool:
    """True if every required button has a non-null [x, y] pair."""
    return all(grid_coords.get(name) for name in REQUIRED_BUTTONS)


def prompt_calibration(grid_coords: dict) -> bool:
    """
    Ask the user whether to (re)calibrate before starting.

    - If config is incomplete/missing: default = YES (Enter runs calibrator).
    - If config looks calibrated: default = NO  (Enter skips and starts).
    Returns True if the user wants to calibrate.
    """
    is_complete = coords_complete(grid_coords)

    print("=" * 50)
    print("SERATO GRID FIXER")
    print("=" * 50)

    if is_complete:
        print("Calibration found in config.json:")
        for name in REQUIRED_BUTTONS:
            print(f"  {name:<10}: {tuple(grid_coords[name])}")
        print()
        print("If your Serato layout has changed (window resize, monitor swap,")
        print("controller plugged in/out, DPI change), you should recalibrate.")
        print()
        choice = input("Recalibrate before starting? [y/N]: ").strip().lower()
        return choice in ("y", "yes")

    missing = [n for n in REQUIRED_BUTTONS if not grid_coords.get(n)]
    print("WARNING: Button coordinates are missing or incomplete.")
    print(f"  Missing: {', '.join(missing)}")
    print()
    print("You need to calibrate before the grid fixer can do anything.")
    print()
    choice = input("Run calibration now? [Y/n]: ").strip().lower()
    return choice not in ("n", "no")


def main():
    config_path = Path(__file__).parent / "config.json"
    grid_coords = load_grid_coords(config_path)

    if prompt_calibration(grid_coords):
        print()
        calibrate_buttons.main()
        # Reload coords from disk after calibration
        grid_coords = load_grid_coords(config_path)
        print()

    if not coords_complete(grid_coords):
        print("ERROR: Calibration is still incomplete. Exiting.")
        return

    fixer = GridFixer(grid_coords)

    stop_requested = False

    def on_tilde():
        fixer.set_grid_here()

    def on_stop():
        nonlocal stop_requested
        stop_requested = True

    keyboard.add_hotkey('`',   on_tilde)
    keyboard.add_hotkey('F12', on_stop)

    print("=" * 50)
    print("SERATO GRID FIXER - Ready!")
    print("=" * 50)
    print("~   : Set grid, Hot Cue 1, load next track")
    print("F12 : Exit")
    print("=" * 50)
    print()

    try:
        while not stop_requested:
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass

    keyboard.unhook_all_hotkeys()
    print("Goodbye!")


if __name__ == '__main__':
    main()

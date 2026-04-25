"""
Serato Grid Fixer

Press ~ at the exact position where you want the grid set.
That's it.

Automates: Edit Grid -> Clear -> Set -> Save -> Hot Cue 1
"""

import time
import json
from pathlib import Path

import keyboard
import pyautogui

from serato_controller import SeratoController


class GridFixer:
    def __init__(self, controller: SeratoController, grid_coords: dict):
        self.controller = controller
        self.grid_coords = grid_coords

    def log(self, msg: str):
        print(msg)

    def set_grid_here(self):
        """Click Edit Grid -> Clear -> Set -> Save -> Hot Cue 1."""
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

        self.log("[~] Grid set! ✓ Setting Hot Cue 1...")

        keyboard.press('ctrl'); keyboard.press('1')
        time.sleep(0.05)
        keyboard.release('1'); keyboard.release('ctrl')

        self.log("[~] Done! ✓✓")

        # Auto-load next track using Serato's built-in shortcut (Alt+W)
        self.log("[~] Loading next track...")
        keyboard.press('alt'); keyboard.press('w')
        time.sleep(0.05)
        keyboard.release('w'); keyboard.release('alt')

        # Advance library cursor so the next ~ press loads the track after this one
        time.sleep(0.1)
        keyboard.send('down')


def main():
    # Load config
    config_path = Path(__file__).parent / "config.json"
    if not config_path.exists():
        print("ERROR: config.json not found. Run calibrate_buttons.py first.")
        return

    with open(config_path) as f:
        config = json.load(f)

    grid_coords = config.get("coordinates", {}).get("grid_edit", {})

    controller = SeratoController()
    fixer = GridFixer(controller, grid_coords)

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

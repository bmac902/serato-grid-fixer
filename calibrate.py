"""
Serato Grid Fixer — Calibration Tool

Captures UI coordinates for Serato DJ Pro buttons by hovering and pressing F8.
Saves coordinates to config.json.

Usage:
    python calibrate.py              # Interactive calibration
    python calibrate.py --test       # Test clicks on saved coordinates
    python calibrate.py --force      # Overwrite without prompting
    python calibrate.py --only beatjump   # Calibrate only beat jump buttons
    python calibrate.py --only gridedit   # Calibrate only grid edit buttons
"""

import argparse
import json
import sys
import time
from pathlib import Path

import keyboard
import pyautogui

# =============================================================================
# CONFIGURATION
# =============================================================================

CONFIG_PATH = Path(__file__).parent / "config.json"

# Calibration items organized by category
CALIBRATION_ITEMS = {
    "beatjump": [
        ("beat_jump", "panel_left", "Beat Jump PANEL '<' (scroll sizes left)"),
        ("beat_jump", "panel_right", "Beat Jump PANEL '>' (scroll sizes right)"),
        ("beat_jump", "1", "Beat Jump '1' button (scroll panel left first if needed)"),
        ("beat_jump", "32", "Beat Jump '32' button (scroll panel right 2x first)"),
        ("beat_jump", "forward", "Beat Jump '>' (jump forward) button"),
        ("beat_jump", "backward", "Beat Jump '<' (jump backward) button"),
    ],
    "gridedit": [
        ("grid_edit", "edit_grid", "Grid Edit 'Edit Grid' button"),
        ("grid_edit", "clear", "Grid Edit 'Clear' button"),
        ("grid_edit", "set", "Grid Edit 'Set' button"),
        ("grid_edit", "save", "Grid Edit 'Save' button"),
    ],
}

# All items in suggested calibration order
ALL_ITEMS = CALIBRATION_ITEMS["beatjump"] + CALIBRATION_ITEMS["gridedit"]


# =============================================================================
# CONFIG FILE HANDLING
# =============================================================================

def load_config() -> dict:
    """Load existing config or return default structure."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    
    # Return minimal default structure
    return {
        "coordinates": {
            "beat_jump": {},
            "grid_edit": {},
            "overview_waveform": {}
        },
        "timing": {
            "post_load_delay_ms": 1200,
            "post_click_delay_ms": 100,
            "post_jump_delay_ms": 200
        },
        "safety": {
            "max_actions_per_track": 80,
            "max_track_seconds": 60,
            "max_total_minutes": 10,
            "max_focus_attempts": 3,
            "max_jump_clicks": 20
        }
    }


def save_config(config: dict):
    """Save config to file."""
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    print(f"\n[SAVED] Config written to {CONFIG_PATH}")


def get_coordinate(config: dict, category: str, key: str):
    """Get a coordinate from config, or None if not set."""
    coords = config.get("coordinates", {})
    cat = coords.get(category, {})
    return cat.get(key)


def set_coordinate(config: dict, category: str, key: str, value: list):
    """Set a coordinate in config."""
    if "coordinates" not in config:
        config["coordinates"] = {}
    if category not in config["coordinates"]:
        config["coordinates"][category] = {}
    config["coordinates"][category][key] = value


# =============================================================================
# CALIBRATION
# =============================================================================

def wait_for_f8() -> tuple:
    """Wait for F8 press and return current mouse position."""
    print("    Press F8 when ready...", end="", flush=True)
    keyboard.wait("F8")
    pos = pyautogui.position()
    print(f" Captured: ({pos.x}, {pos.y})")
    return [pos.x, pos.y]


def calibrate_item(config: dict, category: str, key: str, description: str,
                   force: bool = False) -> bool:
    """
    Calibrate a single item.
    Returns True if calibrated, False if skipped.
    """
    existing = get_coordinate(config, category, key)
    
    print(f"\n[{category}.{key}]")
    print(f"  Description: {description}")
    
    if existing is not None:
        print(f"  Current value: ({existing[0]}, {existing[1]})")
        if not force:
            response = input("  Overwrite? (Y/n): ").strip().lower()
            if response == "n":
                print("  Skipped.")
                return False
    
    print(f"  → Hover over: {description}")
    coord = wait_for_f8()
    set_coordinate(config, category, key, coord)
    return True


def run_calibration(force: bool = False, only: str = None):
    """Run interactive calibration."""
    print("\n" + "="*60)
    print("SERATO GRID FIXER — Calibration Tool")
    print("="*60)
    print("\nThis tool captures mouse coordinates for Serato UI buttons.")
    print("For each item:")
    print("  1. Hover your mouse over the target button")
    print("  2. Press F8 to capture the position")
    print("\nPress Ctrl+C at any time to cancel.\n")
    
    config = load_config()
    
    # Determine which items to calibrate
    if only:
        if only not in CALIBRATION_ITEMS:
            print(f"[ERROR] Unknown category: {only}")
            print(f"Available: {list(CALIBRATION_ITEMS.keys())}")
            sys.exit(1)
        items = CALIBRATION_ITEMS[only]
        print(f"Calibrating only: {only} ({len(items)} items)\n")
    else:
        items = ALL_ITEMS
        print(f"Calibrating all items ({len(items)} total)\n")
    
    calibrated = 0
    skipped = 0
    
    try:
        for category, key, description in items:
            if calibrate_item(config, category, key, description, force):
                calibrated += 1
            else:
                skipped += 1
        
        save_config(config)
        
        print("\n" + "="*60)
        print("CALIBRATION COMPLETE")
        print("="*60)
        print(f"Calibrated: {calibrated}")
        print(f"Skipped:    {skipped}")
        print("\nRun 'python calibrate.py --test' to verify coordinates.")
        print("="*60 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Saving progress...")
        save_config(config)
        sys.exit(0)


# =============================================================================
# TEST MODE
# =============================================================================

def run_test():
    """Test saved coordinates by clicking each one with countdown."""
    print("\n" + "="*60)
    print("SERATO GRID FIXER — Coordinate Test Mode")
    print("="*60)
    print("\nThis will move to and click each saved coordinate.")
    print("Watch carefully to verify each click lands correctly.")
    print("\nSAFETY:")
    print("  - Press F12 to abort at any time")
    print("  - Move mouse to top-left corner to abort")
    print("\nMake sure Serato DJ Pro is open and visible!\n")
    
    config = load_config()
    pyautogui.FAILSAFE = True
    
    # Register F12 abort
    abort = {"flag": False}
    keyboard.add_hotkey("F12", lambda: abort.update({"flag": True}))
    
    input("Press Enter to start test (or Ctrl+C to cancel)...")
    
    coords_to_test = []
    for category, key, description in ALL_ITEMS:
        coord = get_coordinate(config, category, key)
        if coord is not None:
            coords_to_test.append((category, key, description, coord))
    
    if not coords_to_test:
        print("[ERROR] No coordinates calibrated. Run 'python calibrate.py' first.")
        sys.exit(1)
    
    print(f"\nTesting {len(coords_to_test)} coordinates...\n")
    
    # Helper: get panel scroll coordinates
    panel_left_coord = get_coordinate(config, "beat_jump", "panel_left")
    panel_right_coord = get_coordinate(config, "beat_jump", "panel_right")
    
    def scroll_panel(direction: str, times: int):
        """Scroll beat jump panel before testing size buttons."""
        coord = panel_left_coord if direction == "left" else panel_right_coord
        if coord is None:
            return
        for _ in range(times):
            pyautogui.click(coord[0], coord[1])
            time.sleep(0.15)
    
    try:
        for i, (category, key, description, coord) in enumerate(coords_to_test):
            if abort["flag"]:
                print("\n[ABORTED] F12 pressed.")
                break
            
            # Smart panel scrolling: scroll to reveal the button before testing
            if category == "beat_jump" and key == "1":
                print("  [Scrolling panel left to reveal '1'...]")
                scroll_panel("left", 2)
            elif category == "beat_jump" and key == "32":
                print("  [Scrolling panel right to reveal '32'...]")
                scroll_panel("right", 2)
            
            print(f"[{i+1}/{len(coords_to_test)}] {description}")
            print(f"  Coordinate: ({coord[0]}, {coord[1]})")
            
            # Move to position (don't click yet)
            pyautogui.moveTo(coord[0], coord[1], duration=0.3)
            
            # Countdown
            for sec in [3, 2, 1]:
                if abort["flag"]:
                    break
                print(f"  Clicking in {sec}...", end="\r")
                time.sleep(1)
            
            if abort["flag"]:
                print("\n[ABORTED] F12 pressed.")
                break
            
            # Click
            pyautogui.click(coord[0], coord[1])
            print(f"  Clicked!              ")
            time.sleep(0.5)
        
        print("\n" + "="*60)
        print("TEST COMPLETE")
        print("="*60)
        print("If any clicks were off-target, re-run calibration for those items.")
        print("="*60 + "\n")
        
    except pyautogui.FailSafeException:
        print("\n[FAILSAFE] Mouse moved to corner. Aborting.")
    except KeyboardInterrupt:
        print("\n[CANCELLED]")
    finally:
        keyboard.unhook_all()


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Calibrate UI coordinates for Serato DJ Pro"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test saved coordinates by clicking each one"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing coordinates without prompting"
    )
    parser.add_argument(
        "--only",
        type=str,
        choices=["beatjump", "gridedit"],
        help="Calibrate only a specific category"
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Show current calibrated coordinates and exit"
    )
    args = parser.parse_args()
    
    if args.show:
        config = load_config()
        print("\nCurrent calibrated coordinates:\n")
        coords = config.get("coordinates", {})
        for category, items in coords.items():
            print(f"[{category}]")
            for key, value in items.items():
                if value is not None:
                    print(f"  {key}: ({value[0]}, {value[1]})")
                else:
                    print(f"  {key}: (not set)")
            print()
        return
    
    if args.test:
        run_test()
    else:
        run_calibration(force=args.force, only=args.only)


if __name__ == "__main__":
    main()

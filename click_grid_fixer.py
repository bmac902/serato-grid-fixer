"""
Click Grid Fixer - Human-in-the-loop grid correction

Two modes:
1. CLICK MODE (F9): Click on waveform where you want grid set
2. PLAYHEAD MODE (F10): Press hotkey at current playhead position

Eliminates the tedious Edit Grid → Clear → Set → Save sequence.
"""

import time
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Tuple

import keyboard
import pyautogui
from pynput import mouse

from serato_controller import SeratoController


@dataclass
class SeratoWaveformRegion:
    """Defines the clickable waveform area in Serato."""
    x: int          # Left edge
    y: int          # Top edge
    width: int      # Width in pixels
    height: int     # Height in pixels
    
    def contains_point(self, x: int, y: int) -> bool:
        """Check if a point is within this region."""
        return (
            self.x <= x <= self.x + self.width and
            self.y <= y <= self.y + self.height
        )
    
    def x_to_progress(self, x: int) -> float:
        """Convert X coordinate to progress ratio (0.0 to 1.0)."""
        if not self.contains_point(x, self.y):
            return -1.0
        relative_x = x - self.x
        return relative_x / self.width


class ClickGridFixer:
    """
    Listens for hotkeys and mouse clicks to set grid at human-selected positions.
    """
    
    def __init__(self, controller: SeratoController, config: dict, waveform_region: Optional[SeratoWaveformRegion] = None):
        self.controller = controller
        self.config = config
        self.waveform_region = waveform_region
        
        # Load grid edit button coordinates
        self.grid_coords = config.get("coordinates", {}).get("grid_edit", {})
        
        self.click_mode_armed = False
        self.click_listener = None
        
        self.status_callback = None  # Optional callback for status updates
    
    def set_status_callback(self, callback):
        """Set a callback function to receive status messages."""
        self.status_callback = callback
    
    def log(self, msg: str):
        """Log a message (to console and optional callback)."""
        print(msg)
        if self.status_callback:
            self.status_callback(msg)
    
    # =========================================================================
    # MODE 1: CLICK MODE
    # =========================================================================
    
    def arm_click_mode(self):
        """
        Arm click mode - next mouse click will be captured.
        User presses F9, then clicks on waveform.
        """
        if self.click_mode_armed:
            self.log("[CLICK MODE] Already armed. Click anywhere on waveform.")
            return
        
        self.click_mode_armed = True
        self.log("[CLICK MODE] Armed! Click on waveform where you want grid set.")
        self.log("[CLICK MODE] Press F9 again to cancel.")
        
        # Start listening for clicks
        self.click_listener = mouse.Listener(on_click=self._on_mouse_click)
        self.click_listener.start()
    
    def disarm_click_mode(self):
        """Cancel click mode."""
        if not self.click_mode_armed:
            return
        
        self.click_mode_armed = False
        if self.click_listener:
            self.click_listener.stop()
            self.click_listener = None
        
        self.log("[CLICK MODE] Disarmed.")
    
    def _on_mouse_click(self, x, y, button, pressed):
        """
        Mouse click callback. Captures click position and processes it.
        """
        if not self.click_mode_armed:
            return
        
        # Only respond to left-click press (not release)
        if button != mouse.Button.left or not pressed:
            return
        
        # IMMEDIATELY press W to stop - do this FIRST before the track drifts!
        # The click will move the playhead, but we need to stop it RIGHT THERE
        keyboard.press('w')
        keyboard.release('w')
        
        # Disarm click mode
        self.disarm_click_mode()
        
        self.log(f"[CLICK MODE] Captured click at ({x}, {y}) - STOPPED!")
        
        # Process the click
        try:
            # Wait for stop to complete
            time.sleep(0.2)
            
            if self.waveform_region:
                progress = self.waveform_region.x_to_progress(x)
                if progress >= 0:
                    self.log(f"[CLICK MODE] Position: {progress:.1%} through track")
            
            # Set grid at this position (already stopped)
            self._set_grid_sequence(mode="click", already_stopped=True)
            
        except Exception as e:
            self.log(f"[CLICK MODE] Error: {e}")
    
    # =========================================================================
    # MODE 2: PLAYHEAD MODE
    # =========================================================================
    
    def capture_playhead_position(self):
        """
        Capture current playhead position and set grid there.
        User seeks/plays to the right spot, then presses F10.
        """
        self.log("[PLAYHEAD MODE] Setting grid at current position...")
        
        try:
            # Just click the buttons - no keyboard shortcuts
            self._click_grid_buttons(mode="playhead")
            
        except Exception as e:
            self.log(f"[PLAYHEAD MODE] Error: {e}")
    
    # =========================================================================
    # GRID SETTING AUTOMATION
    # =========================================================================
    
    def _click_grid_buttons(self, mode: str):
        """
        Click the grid edit buttons in sequence.
        Simple version - just clicks, no keyboard shortcuts.
        
        1. Click Edit Grid button
        2. Click Clear button
        3. Click Set button
        4. Click Save button
        5. Set Hot Cue 1
        
        Args:
            mode: "click" or "playhead" (for logging)
        """
        self.log(f"[{mode.upper()}] Starting button sequence...")
        
        # Get button coordinates
        edit_grid_coord = self.grid_coords.get("edit_grid")
        clear_coord = self.grid_coords.get("clear")
        set_coord = self.grid_coords.get("set")
        save_coord = self.grid_coords.get("save")
        
        # Click Edit Grid button
        if edit_grid_coord:
            self.log(f"[{mode.upper()}] Clicking Edit Grid...")
            pyautogui.click(edit_grid_coord[0], edit_grid_coord[1])
            time.sleep(0.4)  # Wait for panel to open
        else:
            self.log(f"[{mode.upper()}] ERROR: Edit Grid button not calibrated!")
            return
        
        # Click Clear button
        if clear_coord:
            self.log(f"[{mode.upper()}] Clicking Clear...")
            pyautogui.click(clear_coord[0], clear_coord[1])
            time.sleep(0.3)
        else:
            self.log(f"[{mode.upper()}] WARNING: Clear button not calibrated!")
        
        # Click Set button
        if set_coord:
            self.log(f"[{mode.upper()}] Clicking Set...")
            pyautogui.click(set_coord[0], set_coord[1])
            time.sleep(0.3)
        else:
            self.log(f"[{mode.upper()}] WARNING: Set button not calibrated!")
        
        # Click Save button
        if save_coord:
            self.log(f"[{mode.upper()}] Clicking Save...")
            pyautogui.click(save_coord[0], save_coord[1])
            time.sleep(0.4)
        else:
            self.log(f"[{mode.upper()}] WARNING: Save button not calibrated!")
        
        self.log(f"[{mode.upper()}] Grid set! ✓")
        
        # Set Hot Cue 1
        self.log(f"[{mode.upper()}] Setting Hot Cue 1...")
        keyboard.press('ctrl')
        keyboard.press('1')
        time.sleep(0.05)
        keyboard.release('1')
        keyboard.release('ctrl')
        time.sleep(0.2)
        
        self.log(f"[{mode.upper()}] Complete! ✓✓")
    
    def _set_grid_sequence(self, mode: str, already_stopped: bool = False):
        """
        Execute the grid-setting sequence:
        1. STOP playback completely (if not already stopped)
        2. Enter grid edit mode (Alt+Space)
        3. Click Clear button
        4. Click Set button (sets grid anchor at current playhead position)
        5. Click Save button
        6. Set Hot Cue 1
        
        Args:
            mode: "click" or "playhead" (for logging)
            already_stopped: True if track is already stopped
        """
        self.log(f"[{mode.upper()}] Starting grid set sequence...")
        
        # Ensure Serato is focused
        self.controller.focus_serato()
        time.sleep(0.1)
        
        # STOP playback - press W key to stop (toggle off)
        if not already_stopped:
            self.log(f"[{mode.upper()}] Stopping playback...")
            keyboard.press('w')
            time.sleep(0.05)
            keyboard.release('w')
            time.sleep(0.3)  # Wait for stop to complete
        
        # Enter grid edit mode (Alt+Space)
        self.log(f"[{mode.upper()}] Entering grid edit mode...")
        keyboard.press('alt')
        keyboard.press('space')
        time.sleep(0.05)
        keyboard.release('space')
        keyboard.release('alt')
        time.sleep(0.5)  # Wait for edit panel to open
        
        # Click Clear button
        clear_coord = self.grid_coords.get("clear")
        if clear_coord:
            self.log(f"[{mode.upper()}] Clearing existing grid...")
            pyautogui.click(clear_coord[0], clear_coord[1])
            time.sleep(0.3)
        else:
            self.log(f"[{mode.upper()}] WARNING: Clear button not calibrated!")
        
        # Click Set button (sets grid anchor at current playhead position)
        set_coord = self.grid_coords.get("set")
        if set_coord:
            self.log(f"[{mode.upper()}] Setting grid anchor...")
            pyautogui.click(set_coord[0], set_coord[1])
            time.sleep(0.3)
        else:
            self.log(f"[{mode.upper()}] WARNING: Set button not calibrated!")
        
        # Click Save button (saves and exits edit mode)
        save_coord = self.grid_coords.get("save")
        if save_coord:
            self.log(f"[{mode.upper()}] Saving grid...")
            pyautogui.click(save_coord[0], save_coord[1])
            time.sleep(0.4)
        else:
            self.log(f"[{mode.upper()}] WARNING: Save button not calibrated!")
        
        self.log(f"[{mode.upper()}] Grid set! ✓")
        
        # Set Hot Cue 1 at this position
        self.log(f"[{mode.upper()}] Setting Hot Cue 1...")
        keyboard.press('ctrl')
        keyboard.press('1')
        time.sleep(0.05)
        keyboard.release('1')
        keyboard.release('ctrl')
        time.sleep(0.2)
        
        self.log(f"[{mode.upper()}] Complete! ✓✓")
    
    # =========================================================================
    # HOTKEY REGISTRATION
    # =========================================================================
    
    def register_hotkeys(self):
        """Register global hotkeys for both modes."""
        # F9: Toggle click mode
        keyboard.add_hotkey('F9', self._toggle_click_mode)
        
        # F8: Capture playhead position
        keyboard.add_hotkey('F8', self.capture_playhead_position)
        
        self.log("=" * 60)
        self.log("CLICK GRID FIXER - Ready!")
        self.log("=" * 60)
        self.log("F9  : CLICK MODE - Click on waveform to set grid")
        self.log("F8  : PLAYHEAD MODE - Set grid at current position")
        self.log("F12 : Emergency stop")
        self.log("=" * 60)
    
    def _toggle_click_mode(self):
        """Toggle click mode on/off."""
        if self.click_mode_armed:
            self.disarm_click_mode()
        else:
            self.arm_click_mode()


# =============================================================================
# CALIBRATION HELPER
# =============================================================================

def calibrate_waveform_region() -> SeratoWaveformRegion:
    """
    Interactive calibration to define the waveform clickable area.
    
    User will click:
    1. Top-left corner of waveform
    2. Bottom-right corner of waveform
    
    Returns the calibrated region.
    """
    print("=" * 60)
    print("WAVEFORM CALIBRATION")
    print("=" * 60)
    print("We need to map where the waveform is on your screen.")
    print()
    print("Step 1: Load a track in Serato (left deck)")
    input("Press Enter when ready...")
    
    print()
    print("Step 2: Click the TOP-LEFT corner of the main waveform display")
    print("(The big waveform, not the overview at the top)")
    
    # Capture first click
    clicks = []
    
    def on_click(x, y, button, pressed):
        if button == mouse.Button.left and pressed:
            clicks.append((x, y))
            print(f"✓ Captured: ({x}, {y})")
            return False  # Stop listener
    
    with mouse.Listener(on_click=on_click) as listener:
        listener.join()
    
    top_left = clicks[0]
    
    print()
    print("Step 3: Click the BOTTOM-RIGHT corner of the main waveform display")
    
    clicks.clear()
    
    with mouse.Listener(on_click=on_click) as listener:
        listener.join()
    
    bottom_right = clicks[0]
    
    # Calculate region
    region = SeratoWaveformRegion(
        x=top_left[0],
        y=top_left[1],
        width=bottom_right[0] - top_left[0],
        height=bottom_right[1] - top_left[1],
    )
    
    print()
    print("=" * 60)
    print("Calibration complete!")
    print(f"Waveform region: x={region.x}, y={region.y}, w={region.width}, h={region.height}")
    print("=" * 60)
    
    # Save to config
    config_path = Path(__file__).parent / "waveform_calibration.json"
    with open(config_path, 'w') as f:
        json.dump({
            'x': region.x,
            'y': region.y,
            'width': region.width,
            'height': region.height,
        }, f, indent=2)
    
    print(f"Saved to: {config_path}")
    
    return region


def load_waveform_region() -> Optional[SeratoWaveformRegion]:
    """Load calibrated waveform region from config file."""
    config_path = Path(__file__).parent / "waveform_calibration.json"
    if not config_path.exists():
        return None
    
    with open(config_path) as f:
        data = json.load(f)
    
    return SeratoWaveformRegion(**data)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Run the click grid fixer."""
    import sys
    
    # Check if we need to calibrate
    if '--calibrate' in sys.argv:
        calibrate_waveform_region()
        return
    
    # Load config
    config_path = Path(__file__).parent / "config.json"
    if not config_path.exists():
        print("Error: config.json not found.")
        print("This file contains the calibrated button positions.")
        sys.exit(1)
    
    with open(config_path) as f:
        config = json.load(f)
    
    # Load calibration (optional for click mode, required for waveform click detection)
    waveform_region = load_waveform_region()
    if not waveform_region:
        print("Note: No waveform calibration found.")
        print("      Click mode will work, but waveform position won't be displayed.")
        print("      Run with --calibrate to set it up.")
        print()
    
    # Initialize controller
    controller = SeratoController()
    
    # Create fixer
    fixer = ClickGridFixer(controller, config, waveform_region)
    
    # Register hotkeys
    fixer.register_hotkeys()
    
    # Also register emergency stop
    stop_requested = False
    
    def on_stop():
        nonlocal stop_requested
        stop_requested = True
        print("\n[STOP] Emergency stop triggered!")
    
    keyboard.add_hotkey('F12', on_stop)
    
    # Keep running until stopped
    print()
    print("Running... Press F12 to exit.")
    print()
    
    try:
        while not stop_requested:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        # Cleanup
        if fixer.click_listener:
            fixer.click_listener.stop()
        keyboard.unhook_all_hotkeys()
        print("Goodbye!")


if __name__ == '__main__':
    main()

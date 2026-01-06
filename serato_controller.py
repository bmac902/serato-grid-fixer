"""
Serato Controller — UI Automation for Serato DJ Pro

Handles:
- Window focus management
- Beat Jump clicks
- Track loading
- Coordinate-based UI interaction
"""

from typing import Callable, Optional

import pyautogui
import pygetwindow as gw


class SeratoNotFoundError(Exception):
    """Raised when Serato DJ Pro window cannot be found or focused."""
    pass


class SeratoController:
    """
    Controls Serato DJ Pro via UI automation.
    
    All actions go through safe wrappers that check for emergency stop
    and track action budgets.
    """
    
    WINDOW_TITLE_MATCH = "Serato DJ Pro"
    
    def __init__(
        self,
        config: dict,
        budget,  # BudgetTracker instance
        check_stop_fn: Callable[[], None],
        safe_sleep_fn: Callable[[float], None],
        dry_run: bool = False
    ):
        self.config = config
        self.budget = budget
        self.check_stop = check_stop_fn
        self.safe_sleep = safe_sleep_fn
        self.dry_run = dry_run
        
        # Load coordinates
        self.coords = config.get("coordinates", {})
        self.beat_jump_coords = self.coords.get("beat_jump", {})
        self.grid_edit_coords = self.coords.get("grid_edit", {})
        
        # Load timing
        timing = config.get("timing", {})
        self.post_load_delay = timing.get("post_load_delay_ms", 1200) / 1000
        self.post_click_delay = timing.get("post_click_delay_ms", 100) / 1000
        self.post_jump_delay = timing.get("post_jump_delay_ms", 200) / 1000
        
        # Load safety limits
        safety = config.get("safety", {})
        self.max_focus_attempts = safety.get("max_focus_attempts", 3)
        
        # Track state
        self._serato_window = None
    
    # =========================================================================
    # WINDOW FOCUS MANAGEMENT
    # =========================================================================
    
    def find_serato_window(self) -> Optional[gw.Window]:
        """
        Find Serato DJ Pro window by title (substring match, case-insensitive).
        Returns the best match (prefers non-minimized, largest).
        """
        all_windows = gw.getAllWindows()
        matches = [
            w for w in all_windows
            if self.WINDOW_TITLE_MATCH.lower() in w.title.lower()
        ]
        
        if not matches:
            return None
        
        if len(matches) == 1:
            return matches[0]
        
        # Multiple matches: prefer non-minimized, then largest by area
        non_minimized = [w for w in matches if not w.isMinimized]
        if non_minimized:
            matches = non_minimized
        
        # Sort by window area (width * height), largest first
        matches.sort(key=lambda w: w.width * w.height, reverse=True)
        return matches[0]
    
    def focus_serato(self):
        """
        Focus the Serato DJ Pro window.
        Uses multiple strategies: pygetwindow.activate(), then click-to-focus fallback.
        Retries up to max_focus_attempts times, then raises SeratoNotFoundError.
        """
        for attempt in range(1, self.max_focus_attempts + 1):
            self.check_stop()
            
            window = self.find_serato_window()
            if window is None:
                print(f"    [Focus] Attempt {attempt}/{self.max_focus_attempts}: "
                      f"Serato window not found")
                if attempt < self.max_focus_attempts:
                    self.safe_sleep(1.0)
                continue
            
            try:
                # Restore if minimized
                if window.isMinimized:
                    window.restore()
                    self.safe_sleep(0.3)
                
                # Strategy 1: Try pygetwindow activate
                try:
                    window.activate()
                    self.safe_sleep(0.2)
                except Exception:
                    pass  # Will try fallback
                
                # Strategy 2: Click on the window to ensure focus
                # Click near the top-center of the window (title bar area is safe)
                click_x = window.left + window.width // 2
                click_y = window.top + 50  # Below title bar, safe area
                
                # Make sure coordinates are on screen
                screen_width, screen_height = pyautogui.size()
                click_x = max(10, min(click_x, screen_width - 10))
                click_y = max(10, min(click_y, screen_height - 10))
                
                pyautogui.click(click_x, click_y)
                self.safe_sleep(0.2)
                
                self._serato_window = window
                print(f"    [Focus] Serato focused (window at {window.left}, {window.top})")
                return
                
            except Exception as e:
                print(f"    [Focus] Attempt {attempt}/{self.max_focus_attempts}: "
                      f"Failed to activate: {e}")
                if attempt < self.max_focus_attempts:
                    self.safe_sleep(1.0)
        
        raise SeratoNotFoundError(
            f"Could not find or focus Serato DJ Pro after {self.max_focus_attempts} attempts. "
            "Make sure Serato is running."
        )
    
    # =========================================================================
    # SAFE WRAPPERS
    # =========================================================================
    
    def _safe_click(self, x: int, y: int, description: str = ""):
        """Click at coordinates with safety checks."""
        self.check_stop()
        self.budget.record_action()
        
        if self.dry_run:
            print(f"    [DRY RUN] Click ({x}, {y}) — {description}")
            return
        
        pyautogui.click(x, y)
        self.safe_sleep(self.post_click_delay)
    
    def _safe_hotkey(self, *keys, description: str = ""):
        """Press hotkey combo with safety checks."""
        self.check_stop()
        self.budget.record_action()
        
        if self.dry_run:
            print(f"    [DRY RUN] Hotkey {'+'.join(keys)} — {description}")
            return
        
        pyautogui.hotkey(*keys)
        self.safe_sleep(self.post_click_delay)
    
    def _safe_press(self, key: str, description: str = ""):
        """Press a single key with safety checks."""
        self.check_stop()
        self.budget.record_action()
        
        if self.dry_run:
            print(f"    [DRY RUN] Press '{key}' — {description}")
            return
        
        pyautogui.press(key)
        self.safe_sleep(self.post_click_delay)
    
    # =========================================================================
    # BEAT JUMP CONTROLS
    # =========================================================================
    
    def set_beat_jump(self, size: int):
        """
        Set Beat Jump size by clicking the corresponding button.
        Size can be: 1, 2, 4, 8, 16, 32 (beats)
        
        Note: The Beat Jump panel has pagination. Size 32 requires
        scrolling right twice first; size 1 may require scrolling left.
        """
        size_str = str(size)
        coord = self.beat_jump_coords.get(size_str)
        
        if coord is None:
            raise ValueError(
                f"Beat Jump size '{size}' not calibrated. "
                f"Run 'python calibrate.py' to set coordinates."
            )
        
        # Panel navigation: scroll to reveal the button if needed
        if size == 32:
            # 32 is on the rightmost page, need to scroll right twice
            self._scroll_beat_jump_panel("right", 2)
        elif size == 1:
            # 1 is on the leftmost page, scroll left twice to be safe
            self._scroll_beat_jump_panel("left", 2)
        
        self._safe_click(coord[0], coord[1], f"Beat Jump = {size}")
    
    def _scroll_beat_jump_panel(self, direction: str, times: int):
        """
        Scroll the Beat Jump panel left or right to reveal different sizes.
        """
        key = f"panel_{direction}"
        coord = self.beat_jump_coords.get(key)
        
        if coord is None:
            print(f"    [WARN] Beat Jump '{key}' not calibrated, skipping scroll")
            return
        
        for _ in range(times):
            self.check_stop()
            self.budget.record_action()
            if not self.dry_run:
                pyautogui.click(coord[0], coord[1])
                self.safe_sleep(self.post_click_delay)
    
    def jump_forward(self, times: int = 1):
        """Click the forward (>) beat jump button N times."""
        coord = self.beat_jump_coords.get("forward")
        if coord is None:
            raise ValueError(
                "Beat Jump 'forward' button not calibrated. "
                "Run 'python calibrate.py' to set coordinates."
            )
        
        for i in range(times):
            self.check_stop()
            self.budget.record_jump()
            
            if self.dry_run:
                print(f"    [DRY RUN] Click forward ({i+1}/{times})")
            else:
                pyautogui.click(coord[0], coord[1])
                self.safe_sleep(self.post_jump_delay)
    
    def jump_backward(self, times: int = 1):
        """Click the backward (<) beat jump button N times."""
        coord = self.beat_jump_coords.get("backward")
        if coord is None:
            raise ValueError(
                "Beat Jump 'backward' button not calibrated. "
                "Run 'python calibrate.py' to set coordinates."
            )
        
        for i in range(times):
            self.check_stop()
            self.budget.record_jump()
            
            if self.dry_run:
                print(f"    [DRY RUN] Click backward ({i+1}/{times})")
            else:
                pyautogui.click(coord[0], coord[1])
                self.safe_sleep(self.post_jump_delay)
    
    # =========================================================================
    # TRACK LOADING
    # =========================================================================
    
    def load_track(self):
        """
        Load the next track to the left deck using Alt+W.
        This combines 'select next' and 'load to left deck' in one shortcut.
        """
        self.check_stop()
        self.budget.record_action()
        
        if self.dry_run:
            print("    [DRY RUN] Alt+W (load next track to left deck)")
        else:
            pyautogui.keyDown("alt")
            self.safe_sleep(0.05)
            pyautogui.press("w")
            self.safe_sleep(0.05)
            pyautogui.keyUp("alt")
        
        # Wait for waveform to render
        self.safe_sleep(self.post_load_delay)
    
    # =========================================================================
    # PLAYBACK CONTROLS (for Phase 2+)
    # =========================================================================
    
    def play_left_deck(self):
        """Press W to play/pause left deck."""
        self._safe_press("w", "Play/pause left deck")
    
    def set_hot_cue_1(self):
        """Set Hot Cue 1 on left deck (Ctrl+1)."""
        self._safe_hotkey("ctrl", "1", description="Set Hot Cue 1")
    
    # =========================================================================
    # GRID EDIT CONTROLS (for Phase 3+)
    # =========================================================================
    
    def click_edit_grid(self):
        """Click 'Edit Grid' button."""
        coord = self.grid_edit_coords.get("edit_grid")
        if coord is None:
            raise ValueError("Grid Edit 'edit_grid' button not calibrated.")
        self._safe_click(coord[0], coord[1], "Edit Grid")
    
    def click_clear_grid(self):
        """Click 'Clear' button in grid edit mode."""
        coord = self.grid_edit_coords.get("clear")
        if coord is None:
            raise ValueError("Grid Edit 'clear' button not calibrated.")
        self._safe_click(coord[0], coord[1], "Clear Grid")
    
    def click_set_grid(self):
        """Click 'Set' button in grid edit mode."""
        coord = self.grid_edit_coords.get("set")
        if coord is None:
            raise ValueError("Grid Edit 'set' button not calibrated.")
        self._safe_click(coord[0], coord[1], "Set Grid")
    
    def click_save_grid(self):
        """Click 'Save' button in grid edit mode."""
        coord = self.grid_edit_coords.get("save")
        if coord is None:
            raise ValueError("Grid Edit 'save' button not calibrated.")
        self._safe_click(coord[0], coord[1], "Save Grid")

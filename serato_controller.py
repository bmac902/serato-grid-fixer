"""
Simple Serato Controller — Window focus only

Just handles finding and focusing the Serato DJ Pro window.
All other automation done via keyboard/pyautogui directly in the main script.
"""

from typing import Optional
import time
import pyautogui
import pygetwindow as gw


class SeratoNotFoundError(Exception):
    """Raised when Serato DJ Pro window cannot be found or focused."""
    pass


class SeratoController:
    """Simple controller that just handles window focus."""
    
    WINDOW_TITLE_MATCH = "Serato DJ Pro"
    
    def __init__(self):
        self._serato_window = None
    
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
    
    def focus_serato(self, max_attempts: int = 3):
        """
        Focus the Serato DJ Pro window.
        Raises SeratoNotFoundError if window cannot be found/focused.
        """
        for attempt in range(1, max_attempts + 1):
            window = self.find_serato_window()
            if window is None:
                print(f"    [Focus] Attempt {attempt}/{max_attempts}: Serato window not found")
                if attempt < max_attempts:
                    time.sleep(1.0)
                continue
            
            try:
                # Restore if minimized
                if window.isMinimized:
                    window.restore()
                    time.sleep(0.3)
                
                # Try to activate
                try:
                    window.activate()
                    time.sleep(0.2)
                except Exception:
                    pass  # Will try click fallback
                
                # Click on window to ensure focus
                click_x = window.left + window.width // 2
                click_y = window.top + 50  # Below title bar
                
                # Keep coordinates on screen
                screen_width, screen_height = pyautogui.size()
                click_x = max(10, min(click_x, screen_width - 10))
                click_y = max(10, min(click_y, screen_height - 10))
                
                pyautogui.click(click_x, click_y)
                time.sleep(0.2)
                
                self._serato_window = window
                print(f"    [Focus] Serato focused ✓")
                return
                
            except Exception as e:
                print(f"    [Focus] Attempt {attempt}/{max_attempts}: Failed - {e}")
                if attempt < max_attempts:
                    time.sleep(1.0)
        
        raise SeratoNotFoundError(
            f"Could not find or focus Serato DJ Pro after {max_attempts} attempts. "
            "Make sure Serato is running."
        )
    
    # Convenience keyboard methods (just wrappers)
    def play_left_deck(self):
        """Press W to toggle play/pause on left deck."""
        pyautogui.press('w')
        time.sleep(0.1)
    
    def stop_left_deck(self):
        """Press W to stop left deck (assumes it's playing)."""
        pyautogui.press('w')
        time.sleep(0.1)

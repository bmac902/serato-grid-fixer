"""
Serato Grid Auto-Fixer — Main Entry Point

Phase 1: Navigation Proof-of-Concept
- Safety system with F12 panic stop + mouse failsafe
- Test harness: load track → jump to bar 17 → verify
"""

import argparse
import json
import sys
import threading
import time
from pathlib import Path

import keyboard
import pyautogui

from serato_controller import SeratoController, SeratoNotFoundError

# =============================================================================
# SAFETY SYSTEM (Layer 1: Hotkeys, Layer 2: Mouse Failsafe)
# =============================================================================

pyautogui.FAILSAFE = True   # Mouse to top-left corner = emergency stop
pyautogui.PAUSE = 0.02      # Small delay between pyautogui actions

stop_event = threading.Event()


def arm_kill_switches():
    """Register global hotkeys for emergency stop."""
    keyboard.add_hotkey("F12", lambda: stop_event.set())
    keyboard.add_hotkey("ctrl+shift+esc", lambda: stop_event.set())
    print("[SAFETY] Kill switches armed: F12 or Ctrl+Shift+Esc to stop")
    print("[SAFETY] Mouse to top-left corner = instant abort")


def check_stop():
    """Check if emergency stop was triggered. Raises RuntimeError if so."""
    if stop_event.is_set():
        raise RuntimeError("EMERGENCY STOP triggered (F12)")


def safe_sleep(seconds: float, step: float = 0.05):
    """Sleep in small chunks so F12 can interrupt quickly."""
    end = time.time() + seconds
    while time.time() < end:
        check_stop()
        time.sleep(step)


# =============================================================================
# BUDGET TRACKING (Runaway Prevention)
# =============================================================================

class BudgetTracker:
    """Tracks action counts and time to prevent runaway automation."""
    
    def __init__(self, config: dict):
        safety = config.get("safety", {})
        self.max_actions_per_track = safety.get("max_actions_per_track", 80)
        self.max_track_seconds = safety.get("max_track_seconds", 60)
        self.max_total_minutes = safety.get("max_total_minutes", 10)
        self.max_jump_clicks = safety.get("max_jump_clicks", 20)
        
        self.total_start_time = None
        self.track_start_time = None
        self.track_action_count = 0
        self.track_jump_count = 0
        self.total_tracks = 0
    
    def start_session(self):
        """Call once at the start of a batch run."""
        self.total_start_time = time.time()
        print(f"[BUDGET] Session started. Max runtime: {self.max_total_minutes} min")
    
    def start_track(self):
        """Call at the start of each track."""
        self.track_start_time = time.time()
        self.track_action_count = 0
        self.track_jump_count = 0
        self.total_tracks += 1
        self._check_total_time()
    
    def record_action(self):
        """Record a generic action. Raises if budget exceeded."""
        self._check_total_time()
        self._check_track_time()
        self.track_action_count += 1
        if self.track_action_count > self.max_actions_per_track:
            raise RuntimeError(
                f"BUDGET EXCEEDED: {self.track_action_count} actions on track "
                f"(max: {self.max_actions_per_track})"
            )
    
    def record_jump(self):
        """Record a jump click. Raises if budget exceeded."""
        self.record_action()
        self.track_jump_count += 1
        if self.track_jump_count > self.max_jump_clicks:
            raise RuntimeError(
                f"BUDGET EXCEEDED: {self.track_jump_count} jump clicks on track "
                f"(max: {self.max_jump_clicks})"
            )
    
    def _check_total_time(self):
        """Check if total session time exceeded."""
        if self.total_start_time:
            elapsed_min = (time.time() - self.total_start_time) / 60
            if elapsed_min > self.max_total_minutes:
                raise RuntimeError(
                    f"BUDGET EXCEEDED: Session ran for {elapsed_min:.1f} min "
                    f"(max: {self.max_total_minutes})"
                )
    
    def _check_track_time(self):
        """Check if per-track time exceeded."""
        if self.track_start_time:
            elapsed_sec = time.time() - self.track_start_time
            if elapsed_sec > self.max_track_seconds:
                raise RuntimeError(
                    f"BUDGET EXCEEDED: Track took {elapsed_sec:.1f}s "
                    f"(max: {self.max_track_seconds})"
                )
    
    def summary(self) -> str:
        """Return session summary string."""
        elapsed = (time.time() - self.total_start_time) if self.total_start_time else 0
        return f"Processed {self.total_tracks} tracks in {elapsed:.1f}s"


# =============================================================================
# CONFIG LOADING
# =============================================================================

def load_config() -> dict:
    """Load config.json from the script directory."""
    config_path = Path(__file__).parent / "config.json"
    if not config_path.exists():
        print(f"[ERROR] Config not found: {config_path}")
        print("Run 'python calibrate.py' first to set up coordinates.")
        sys.exit(1)
    
    with open(config_path, "r") as f:
        return json.load(f)


def validate_coordinates(config: dict) -> bool:
    """Check that required coordinates are calibrated."""
    coords = config.get("coordinates", {})
    beat_jump = coords.get("beat_jump", {})
    
    required = ["32", "forward", "backward"]
    missing = [k for k in required if beat_jump.get(k) is None]
    
    if missing:
        print(f"[ERROR] Missing calibrated coordinates: {missing}")
        print("Run 'python calibrate.py' to calibrate.")
        return False
    return True


# =============================================================================
# TEST HARNESS: Navigation Proof-of-Concept
# =============================================================================

def run_navigation_test(controller: SeratoController, budget: BudgetTracker,
                        num_tracks: int = 10, manual_confirm: bool = False):
    """
    Phase 1 test harness:
    - Load track
    - Set Beat Jump to 32
    - Jump forward twice (→ bar 17)
    - Optionally pause for manual confirmation
    """
    print(f"\n{'='*60}")
    print("PHASE 1: Navigation Test Harness")
    print(f"{'='*60}")
    print(f"Will process {num_tracks} tracks")
    print(f"Manual confirm mode: {manual_confirm}")
    print(f"{'='*60}\n")
    
    budget.start_session()
    successes = 0
    failures = 0
    
    for i in range(num_tracks):
        check_stop()
        print(f"\n[Track {i+1}/{num_tracks}]")
        
        try:
            budget.start_track()
            
            # Step 1: Focus Serato
            print("  → Focusing Serato...")
            controller.focus_serato()
            safe_sleep(0.3)
            
            # Step 2: Load next track (Down Arrow, then Shift+Left)
            print("  → Loading track...")
            controller.load_track()
            
            # Step 3: Set Beat Jump to 32
            print("  → Setting Beat Jump to 32...")
            controller.set_beat_jump(32)
            
            # Step 4: Jump forward twice (bar 1 → bar 17)
            print("  → Jumping to bar 17 (2 × 32 beats)...")
            controller.jump_forward(2)
            
            # Step 5: Manual confirmation if requested
            if manual_confirm:
                print("  ✓ Jumped to bar 17. Verify visually.")
                input("    Press Enter to continue (or Ctrl+C to abort)...")
            else:
                safe_sleep(0.5)  # Brief pause to observe
            
            print("  ✓ SUCCESS")
            successes += 1
            
        except SeratoNotFoundError as e:
            print(f"  ✗ FAILED: {e}")
            failures += 1
            break  # Can't continue without Serato
            
        except RuntimeError as e:
            print(f"  ✗ FAILED: {e}")
            failures += 1
            if "EMERGENCY STOP" in str(e) or "BUDGET EXCEEDED" in str(e):
                break
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST COMPLETE")
    print(f"{'='*60}")
    print(f"Successes: {successes}/{num_tracks}")
    print(f"Failures:  {failures}/{num_tracks}")
    print(budget.summary())
    print(f"{'='*60}\n")
    
    return successes, failures


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Serato Grid Auto-Fixer — Phase 1 Navigation Test"
    )
    parser.add_argument(
        "-n", "--num-tracks",
        type=int,
        default=10,
        help="Number of tracks to process (default: 10)"
    )
    parser.add_argument(
        "--manual-confirm",
        action="store_true",
        help="Pause after each bar-17 jump for visual confirmation"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without executing (for testing)"
    )
    args = parser.parse_args()
    
    # Load and validate config
    config = load_config()
    if not validate_coordinates(config):
        sys.exit(1)
    
    # Initialize components
    budget = BudgetTracker(config)
    controller = SeratoController(
        config=config,
        budget=budget,
        check_stop_fn=check_stop,
        safe_sleep_fn=safe_sleep,
        dry_run=args.dry_run
    )
    
    # Arm safety systems
    arm_kill_switches()
    
    print("\n" + "="*60)
    print("SERATO GRID AUTO-FIXER — Phase 1")
    print("="*60)
    print("Make sure Serato DJ Pro is open and a crate is selected.")
    print("Press Enter to start, or Ctrl+C to cancel...")
    
    try:
        input()
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(0)
    
    # Run test harness
    try:
        run_navigation_test(
            controller=controller,
            budget=budget,
            num_tracks=args.num_tracks,
            manual_confirm=args.manual_confirm
        )
    except pyautogui.FailSafeException:
        print("\n[FAILSAFE] Mouse moved to corner. Exiting immediately.")
    except RuntimeError as e:
        print(f"\n[STOPPED] {e}")
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Keyboard interrupt.")
    finally:
        keyboard.unhook_all()
        print("Cleanup complete.")


if __name__ == "__main__":
    main()

---

```markdown
# Serato Grid Auto-Fixer — Project Specification

## Problem Statement

When DJing with SoundCloud tracks in Serato DJ Pro, many tracks load with misaligned beatgrids. The most common issue (~90% of cases) is the grid being **off by one beat** — the detected "beat 1" is actually beat 2, 3, or 4.

**Current manual workflow:**
1. Jump ahead to the drop (where the beat structure is clear)
2. Edit Grid → Clear → Set → Save (to anchor grid to the kick)
3. Beat jump backwards to the first beat
4. Set Hot Cue 1

This takes ~1-2 hours/week of prep before DJ sessions. Over years, this adds up to hundreds of hours.

**Goal:** Automate 60-80% of this workflow, flagging only ambiguous tracks for manual review.

---

## Key Insights Discovered

### 1. Drop Detection Is Deterministic (Not Fuzzy)

Electronic music follows predictable structure:
- **Bar 17** (after 16-bar intro) — very common drop point
- **Bar 33** (after 32-bar intro) — very common drop point  
- **Bar 65** — longer intros

Instead of scanning the entire waveform for "energy spikes," we probe these known positions.

### 2. Beat Jump Math

With Beat Jump set to 32 beats (8 bars):
- 2 jumps from start → Bar 17
- 4 jumps from start → Bar 33
- 8 jumps from start → Bar 65

### 3. Genre-Specific Timing (Secondary Heuristics)

- **Standard EDM:** 15s or 30s drop points
- **Drum & Bass:** ~45s or ~1:30 drop points
- These are hints for probe ordering, not hard rules

### 4. The 90% Problem Is "Off By One Beat"

Most misaligned tracks have grids shifted by exactly 1 beat. The fix:
1. Go to a known-good section (bar 17/33)
2. Test 3 positions: current, +1 beat, -1 beat
3. Pick the one where the kick hits strongest
4. Anchor the grid there

### 5. Beat Jump Supports 1-Beat Precision

Beat Jump range: 1/32 to 32 beats. This enables precise A/B/C testing.

---

## Serato DJ Pro Controls (Mapped)

### Keyboard Shortcuts

| Action | Left Deck | Right Deck |
|--------|-----------|------------|
| Load selected track | `Shift + Left Arrow` | `Shift + Right Arrow` |
| Play/Pause | `W` | `S` |
| Set Hot Cue 1 | `Ctrl + 1` | `Ctrl + 6` |
| Set Hot Cue 2 | `Ctrl + 2` | `Ctrl + 7` |
| Enter Beatgrid Edit | `Alt + Spacebar` | (toggle between decks) |
| Fine Slip (nudge grid) | `Left Arrow` / `Right Arrow` | |
| Move through library | `Up Arrow` / `Down Arrow` | |

### On-Screen UI Elements (Need Coordinate Calibration)

**Beat Jump Controls:**
- Top row (beats): 2, 4, 8, 16
- Bottom row (bars): 4, 8, 16, 32
- `<` button: Jump backward by selected amount
- `>` button: Jump forward by selected amount
- Click a number to select jump size

**Beatgrid Edit Panel:**
- "Edit Grid" button — enters edit mode
- "Clear" button — clears existing grid
- "Set" button — sets grid anchor at playhead
- "Save" button — saves and exits edit mode
- Adjust arrows: shifts entire grid
- Slip arrows: fine-tunes grid position

**Overview Waveform:**
- Clickable to seek to approximate position
- Shows bar numbers (1, 2, 3... 17, 18... 33...)
- Color density indicates energy (useful for visual drop detection)

---

## Technical Architecture

### Tech Stack

- **Python 3.10+**
- **pyautogui** — mouse clicks, keyboard simulation
- **keyboard** — global hotkey detection (for manual triggers)
- **sounddevice** — WASAPI loopback audio capture (Windows)
- **numpy / scipy** — audio signal processing
- **json** — config and logging

### Core Components

```
serato-grid-fixer/
├── config.json              # UI coordinates, thresholds, probe settings
├── calibrate.py             # Tool to capture button coordinates
├── audio_scorer.py          # Kick detection / scoring
├── serato_controller.py     # UI automation (clicks, keys)
├── grid_fixer.py            # Main algorithm
├── main.py                  # Entry point / batch processor
├── output/
│   ├── run_log.jsonl        # Per-track results
│   └── flagged.jsonl        # Tracks needing manual review
└── README.md
```

---

## Algorithm: Grid Auto-Fixer v1

### Per-Track Flow

```
1. LOAD TRACK
   - Press Down Arrow (select next track in library)
   - Press Shift+Left Arrow (load to left deck)
   - Wait ~1s for waveform to render

2. PROBE FOR DROP
   - Click "32" in Beat Jump panel (set jump size)
   - Jump forward: click ">" twice → now at bar 17
   - Run KICK TEST (see below)
   - If kick score too low:
     - Jump forward: click ">" twice more → now at bar 33
     - Run KICK TEST again
   - If still too low:
     - Jump to bar 65 (4 more jumps) and test
   - If all fail: FLAG for manual review, skip to next track

3. A/B/C GRID TEST (at probe point)
   - Click "1" in Beat Jump panel (set jump size to 1 beat)
   - Test position A (current):
     - Press W (play), wait 0.8s, Press W (stop)
     - Capture audio, compute kick score
   - Test position B (+1 beat):
     - Click ">" (jump forward 1 beat)
     - Play/capture/stop, compute kick score
   - Test position C (-2 beats, i.e., original -1):
     - Click "<" twice (jump back 2 beats)
     - Play/capture/stop, compute kick score
   - Winner = highest kick score
   - Navigate to winning position

4. FIX GRID
   - Click "Edit Grid"
   - Click "Clear"
   - Click "Set"
   - Click "Save"

5. SET CUE POINT
   - Click "32" in Beat Jump panel
   - Click "<" repeatedly until bar 1 (or near start)
   - Fine-tune with smaller jumps if needed
   - Press Ctrl+1 (set Hot Cue 1)

6. NEXT TRACK
   - Loop back to step 1
```

### Kick Scoring Function

```python
def compute_kick_score(audio_samples, sample_rate=44100):
    """
    Score how "kick-like" a 1-second audio clip is.
    Higher score = more likely to be on a downbeat with kick drum.
    """
    # 1. Bandpass filter: 40-140 Hz (kick drum range)
    # 2. Compute short-time energy (20ms windows)
    # 3. Find peaks (transients)
    # 4. Score = count of strong peaks * average peak amplitude
    # 5. Bonus: check if peaks are evenly spaced (tempo-aligned)
    
    return score
```

### Confidence & Flagging

- If the winning score is < threshold → flag (no clear kick)
- If scores are within 10% of each other → flag (ambiguous)
- If probe points all fail → flag (unusual track structure)

Flagged tracks go to `output/flagged.jsonl` for manual review.

---

## Implementation Phases

### Phase 1: Navigation Proof-of-Concept ✅ COMPLETE
**Goal:** Prove UI automation works reliably.

- [x] Calibration script (record button coordinates via F8 hover)
- [x] Load track via Alt+W (load next track shortcut)
- [x] Click Beat Jump "32" (with panel scroll), then click ">" to jump
- [x] Verify we land on bar 17
- [x] Safety system: F12 panic stop, mouse failsafe, budget limits
- [x] Window focus with click-to-focus fallback

**Files created:** `main.py`, `serato_controller.py`, `calibrate.py`, `config.json`

---

### Phase 2: Audio Capture & Kick Scoring
**Goal:** Prove we can distinguish "on kick" from "off kick."

**New file:** `audio_scorer.py`

#### Step 2.1: WASAPI Loopback Capture
```python
# Use sounddevice with WASAPI loopback to capture system audio
import sounddevice as sd

def capture_audio(duration_ms: int = 800) -> np.ndarray:
    """Capture system audio (what Serato is playing)."""
    # Find WASAPI loopback device (name contains "Loopback" or similar)
    # Record for duration_ms
    # Return numpy array of samples
```

**Test:** Play any audio, verify we capture it correctly.

#### Step 2.2: Bandpass Filter (40-140 Hz)
```python
from scipy.signal import butter, sosfilt

def bandpass_filter(samples: np.ndarray, low=40, high=140, sr=44100) -> np.ndarray:
    """Isolate kick drum frequencies."""
    sos = butter(4, [low, high], btype='band', fs=sr, output='sos')
    return sosfilt(sos, samples)
```

#### Step 2.3: Kick Scoring Algorithm
```python
def compute_kick_score(samples: np.ndarray, sample_rate=44100) -> float:
    """
    Score how "kick-like" a clip is. Higher = stronger kick presence.
    
    1. Bandpass filter to 40-140 Hz
    2. Compute envelope (absolute value, smoothed)
    3. Find transient peaks (scipy.signal.find_peaks)
    4. Score = peak_count * mean_peak_amplitude
    5. Bonus: check peak spacing matches expected tempo
    """
```

#### Step 2.4: Manual Validation Test
```bash
python audio_scorer.py --test
```
- Manually position Serato on a kick → capture → score
- Manually position Serato off-kick (snare/hat) → capture → score
- Verify kick score is consistently higher (2x+ difference expected)

**Dependencies to uncomment in requirements.txt:**
```
sounddevice>=0.4.6
numpy>=1.24.0
scipy>=1.10.0
```

---

### Phase 3: Full Grid Fixer Loop
**Goal:** End-to-end automation for single track.

**New file:** `grid_fixer.py`

#### Step 3.1: Integrate Audio with Navigation
```python
class GridFixer:
    def __init__(self, controller: SeratoController, scorer: AudioScorer, config: dict):
        ...
    
    def probe_for_drop(self) -> Optional[int]:
        """
        Jump to bar 17, test kick score.
        If too low, try bar 33, then bar 65.
        Returns the bar number with best kick, or None if all fail.
        """
    
    def abc_grid_test(self) -> str:
        """
        At current position, test 3 grid alignments:
        - Position A: current (play 0.8s, capture, score)
        - Position B: +1 beat (jump forward 1, play, capture, score)
        - Position C: -1 beat (jump back 2, play, capture, score)
        Returns 'A', 'B', or 'C' (winner), or 'AMBIGUOUS' if scores too close.
        """
```

#### Step 3.2: Grid Edit Macro
```python
def fix_grid(self):
    """Execute grid edit sequence: Edit Grid → Clear → Set → Save."""
    self.controller.focus_serato()  # Focus before dangerous clicks
    self.controller.click_edit_grid()
    self.safe_sleep(0.2)
    self.controller.click_clear_grid()
    self.safe_sleep(0.2)
    self.controller.click_set_grid()
    self.safe_sleep(0.2)
    self.controller.click_save_grid()
```

#### Step 3.3: Single Track Flow
```python
def process_track(self) -> dict:
    """
    Full flow for one track:
    1. Load track (already on deck from navigation)
    2. Probe for drop (bar 17/33/65)
    3. A/B/C grid test
    4. Navigate to winner position
    5. Fix grid (Edit → Clear → Set → Save)
    6. Return result dict with scores, decision, confidence
    """
```

#### Step 3.4: Logging
```python
# Append to output/run_log.jsonl
{
    "timestamp": "2026-01-05T12:34:56",
    "track_index": 1,
    "probe_bar": 17,
    "scores": {"A": 0.82, "B": 0.45, "C": 0.38},
    "winner": "A",
    "confidence": "high",  # or "low", "ambiguous"
    "action": "fixed"  # or "flagged", "skipped"
}
```

---

### Phase 4: Batch Processing + Cue Setting
**Goal:** Process entire crate automatically.

#### Step 4.1: Batch Loop in main.py
```python
def run_batch(controller, fixer, budget, num_tracks: int):
    results = {"fixed": 0, "flagged": 0, "errors": 0}
    
    for i in range(num_tracks):
        check_stop()
        budget.start_track()
        
        # Load next track
        controller.load_track()
        
        # Process
        result = fixer.process_track()
        
        # Set Hot Cue 1 at bar 1 (if fixed successfully)
        if result["action"] == "fixed":
            rewind_to_bar_1(controller)
            controller.set_hot_cue_1()
            results["fixed"] += 1
        elif result["action"] == "flagged":
            results["flagged"] += 1
            append_to_flagged(result)
        
    return results
```

#### Step 4.2: Rewind to Bar 1
```python
def rewind_to_bar_1(controller: SeratoController):
    """
    From current position (bar 17/33/65), rewind to bar 1.
    Use Beat Jump 32 backward, then fine-tune with smaller jumps.
    """
    controller.set_beat_jump(32)
    
    # From bar 17: 2 jumps back → bar 1
    # From bar 33: 4 jumps back → bar 1
    # From bar 65: 8 jumps back → bar 1
    controller.jump_backward(jumps_needed)
```

#### Step 4.3: Flagged Tracks Output
```python
# output/flagged.jsonl - tracks needing manual review
{
    "timestamp": "2026-01-05T12:35:00",
    "track_index": 5,
    "reason": "ambiguous",  # or "no_kick", "probe_failed"
    "scores": {"A": 0.52, "B": 0.48, "C": 0.44},
    "probe_bar": 33
}
```

#### Step 4.4: Summary Stats
```bash
$ python main.py -n 50

Processing 50 tracks...
[====================] 50/50

RESULTS:
  Fixed:   42 (84%)
  Flagged: 6 (12%)
  Errors:  2 (4%)

Time: 7m 23s (6.8 tracks/min)
Flagged tracks saved to: output/flagged.jsonl
```

---

### Phase 5: Polish & Genre Rules
**Goal:** Handle edge cases, improve accuracy.

#### Step 5.1: Extended Probe Points
```python
# Add bar 65 for tracks with long intros
probes = config["probes"]["bar_sequence"]  # [17, 33, 65]

# Time-based fallback for DnB (slower builds)
if genre_hint == "dnb":
    time_probes = [45, 90]  # seconds
```

#### Step 5.2: Genre Detection (Optional)
```python
def estimate_genre(bpm: float) -> str:
    """Rough genre guess from BPM."""
    if 170 <= bpm <= 180:
        return "dnb"
    elif 138 <= bpm <= 150:
        return "trance"
    elif 120 <= bpm <= 130:
        return "house"
    else:
        return "unknown"
```

#### Step 5.3: Mute During Testing (Optional)
```python
# Option A: Use Serato's internal mute
# Option B: Lower Windows volume via pycaw
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

def mute_system():
    ...

def unmute_system():
    ...
```

#### Step 5.4: Configurable Probe Order
```json
{
  "probes": {
    "default": [17, 33, 65],
    "dnb": [33, 65, 17],
    "time_based": {
      "dnb": [45, 90],
      "trance": [30, 60]
    }
  }
}
```

#### Step 5.5: Confidence Tuning
```python
# Adjust thresholds based on real-world testing
"audio": {
    "min_kick_score": 0.5,       # Below this → flag
    "ambiguity_threshold": 0.1,  # If top 2 scores within 10% → flag
    "strong_confidence": 0.7     # Above this → high confidence
}
```

---

## Quick Reference: Key Commands

```bash
# Calibrate UI coordinates
python calibrate.py
python calibrate.py --test
python calibrate.py --only beatjump --force

# Run navigation test (Phase 1)
python main.py --manual-confirm
python main.py -n 5 --dry-run

# Future: Run full batch (Phase 4+)
python main.py -n 50
python main.py --crate "SoundCloud New"
```

---

## Configuration Schema

```json
{
  "coordinates": {
    "beat_jump": {
      "1": [x, y],
      "2": [x, y],
      "4": [x, y],
      "32": [x, y],
      "forward": [x, y],
      "backward": [x, y]
    },
    "grid_edit": {
      "edit_grid": [x, y],
      "clear": [x, y],
      "set": [x, y],
      "save": [x, y]
    },
    "overview_waveform": {
      "left": x,
      "right": x,
      "y": y
    }
  },
  "audio": {
    "sample_rate": 44100,
    "test_duration_ms": 800,
    "kick_band_low_hz": 40,
    "kick_band_high_hz": 140,
    "min_kick_score": 0.5,
    "ambiguity_threshold": 0.1
  },
  "probes": {
    "bar_sequence": [17, 33, 65],
    "jumps_per_bar": {
      "17": 2,
      "33": 4,
      "65": 8
    }
  },
  "timing": {
    "post_load_delay_ms": 1000,
    "post_click_delay_ms": 100,
    "post_jump_delay_ms": 200
  }
}
```

---

## Hardware Context

- **Controller:** Pioneer DDJ Rev-5
- **Software:** Serato DJ Pro (latest)
- **Streaming:** SoundCloud integration
- **OS:** Windows

---

## Open Questions / Decisions

1. **Mute during testing?** 
   - Option A: Lower Serato output programmatically
   - Option B: Accept brief audio blips during 1s tests
   
2. **Ambiguous track handling?**
   - Option A: Flag and skip
   - Option B: Pick best score anyway, log confidence
   
3. **Multi-deck support?**
   - Start with Left Deck only
   - Add Right Deck later if useful

---

## Success Metrics

- **Coverage:** % of tracks successfully auto-fixed (target: 60-80%)
- **Accuracy:** % of auto-fixed tracks with correct grid (target: 95%+)
- **Speed:** Tracks processed per minute (target: 6-10 TPM)
- **Time saved:** Hours/week reduced from 1.5 → 0.3

---

## References

- Serato Keyboard Shortcuts: (mapped above)
- WASAPI Loopback: Windows audio capture for "what you hear"
- Beat detection: Low-frequency transient detection (40-140 Hz)
```

---
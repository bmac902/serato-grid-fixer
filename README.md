# Serato Click Grid Fixer

**Stop wasting hours manually fixing beatgrids.** This tool automates the tedious button-clicking sequence when you already know where the first kick is.

## The Problem

SoundCloud tracks often load with misaligned beatgrids in Serato. The manual workflow is:
1. Find the first kick (by ear/eye)
2. Seek to that position
3. Edit Grid → Clear → Set → Save → Set Hot Cue 1
4. Repeat for 50+ tracks 😫

## The Solution

You handle the hard part (finding the kick), the tool handles the tedious part (the button sequence).

### Two Modes

**F9 - Click Mode**: Click on the waveform where you see the kick
- Fast for visually obvious kicks
- No need to play first

**F10 - Playhead Mode**: Seek/play to the exact spot, then press F10
- Precise when you need to hear it
- You control the exact position

Both modes automatically execute: **Pause → Edit Grid → Clear → Set → Save → Set Hot Cue 1**

## Quick Start

```powershell
# 1. Install dependencies
pip install -r requirements.txt

# 2. Make sure your config.json has grid_edit coordinates calibrated
#    (it should already have them from the old project)

# 3. Optional: Calibrate waveform region for click mode
python click_grid_fixer.py --calibrate

# 4. Run it
python click_grid_fixer.py
```

## Usage

1. **Load a track** in Serato (left deck)

2. **Choose your mode:**

   **Click Mode (F9):**
   - Press `F9`
   - Click where you want the grid set
   
   **Playhead Mode (F10):**
   - Seek/play to the exact position
   - Press `F10`

3. **Watch it work!** The tool will:
   - Pause playback
   - Clear the old grid
   - Set grid at your position
   - Save
   - Set Hot Cue 1

4. **Repeat** for the next track

5. **Press F12** to exit

## Configuration

`config.json` contains calibrated button positions. The grid_edit section should have:
```json
"grid_edit": {
  "edit_grid": [x, y],
  "clear": [x, y],
  "set": [x, y],
  "save": [x, y]
}
```

If these aren't set, you'll need to calibrate them (see the old calibrate.py or manually measure).

## Benefits

- **Saves hours** — reduces 30-second manual workflow to 1-2 seconds
- **No audio analysis** — uses your expert ears instead of fragile algorithms
- **Reliable** — you're in control, tool just automates the clicks
- **Fast workflow** — press F10 as you go, don't break your rhythm

## Tips

- **Use Playhead Mode (F10) while playing** — set grid on-the-fly as track plays
- **Use Click Mode (F9) for visual kicks** — fast for obvious waveforms
- **Batch process** — load track, F10, next track, F10, next track...
- **Mouse failsafe** — move mouse to top-left corner to emergency stop

## Technical

- Python 3.8+
- Uses `pyautogui` for UI automation
- Uses `keyboard` for global hotkeys
- Uses `pynput` for mouse click detection
- Uses `pygetwindow` for window focus

## License

Do whatever you want with it. If it saves you hours of tedious work, that's payment enough.

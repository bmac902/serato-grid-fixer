import argparse
import json
import sys
import time
from dataclasses import dataclass
from typing import Optional, Tuple, List

import numpy as np
from scipy.signal import butter, sosfilt, find_peaks

# PyAudioWPatch for WASAPI loopback support
try:
    import pyaudiowpatch as pyaudio
    HAS_PYAUDIO = True
except ImportError:
    pyaudio = None
    HAS_PYAUDIO = False

# sounddevice as fallback for device listing
try:
    import sounddevice as sd
    HAS_SD = True
except ImportError:
    sd = None
    HAS_SD = False

try:
    from scipy.io.wavfile import write as wav_write
except Exception:
    wav_write = None


# -----------------------------
# Config / dataclasses
# -----------------------------
@dataclass
class AudioConfig:
    sample_rate: int = 44100
    test_duration_ms: int = 800
    warmup_ms: int = 250  # delay after Play before capturing
    kick_band_low_hz: float = 40.0
    kick_band_high_hz: float = 140.0

    # envelope + peak detection
    env_smooth_ms: float = 25.0
    peak_min_distance_ms: float = 120.0  # prevent double-counting same kick
    peak_prominence: float = 0.02        # relative-ish after normalization
    peak_height: float = 0.04            # relative-ish after normalization

    # scoring
    min_peaks: int = 2
    score_power: float = 1.0             # nonlinear emphasis on strong peaks


# -----------------------------
# Device selection helpers (PyAudioWPatch)
# -----------------------------

def get_pyaudio_instance():
    """Get a PyAudio instance."""
    if not HAS_PYAUDIO:
        raise RuntimeError("pyaudiowpatch not installed. Run: pip install pyaudiowpatch")
    return pyaudio.PyAudio()


def list_devices_pyaudio() -> List[dict]:
    """List all audio devices via PyAudio."""
    p = get_pyaudio_instance()
    devices = []
    for i in range(p.get_device_count()):
        devices.append(p.get_device_info_by_index(i))
    p.terminate()
    return devices


def find_wasapi_loopback_device(
    preferred_substring: Optional[str] = None,
    verbose: bool = False
) -> dict:
    """
    Find a WASAPI loopback device for capturing system audio.
    
    PyAudioWPatch exposes loopback devices with 'isLoopbackDevice': True
    """
    p = get_pyaudio_instance()
    
    try:
        # Get WASAPI host API info
        wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
    except OSError:
        p.terminate()
        raise RuntimeError("WASAPI not available on this system")
    
    def norm(s: str) -> str:
        return (s or "").lower()
    
    # Find loopback devices
    loopback_devices = []
    for i in range(p.get_device_count()):
        device = p.get_device_info_by_index(i)
        
        # Check if it's a WASAPI device
        if device.get("hostApi") != wasapi_info["index"]:
            continue
            
        # Check if it's a loopback device (PyAudioWPatch specific)
        if device.get("isLoopbackDevice", False):
            loopback_devices.append(device)
    
    p.terminate()
    
    if not loopback_devices:
        raise RuntimeError(
            "No WASAPI loopback devices found. "
            "Make sure you have pyaudiowpatch installed (not regular pyaudio)."
        )
    
    # Preferred substring match
    if preferred_substring:
        ps = norm(preferred_substring)
        for d in loopback_devices:
            if ps in norm(d.get("name", "")):
                if verbose:
                    print(f"[audio] Using loopback device: {d['name']}")
                return d
    
    # Default: pick first loopback device
    d = loopback_devices[0]
    if verbose:
        print(f"[audio] Using loopback device: {d['name']}")
    return d


# -----------------------------
# Capture + DSP
# -----------------------------
def capture_audio(
    cfg: AudioConfig,
    device_info: Optional[dict] = None,
    verbose: bool = False,
) -> np.ndarray:
    """
    Capture system audio via WASAPI loopback for cfg.test_duration_ms.
    Returns float32 mono samples in range ~[-1, 1].
    
    Uses PyAudioWPatch for proper WASAPI loopback support.
    """
    if not HAS_PYAUDIO:
        raise RuntimeError("pyaudiowpatch not installed. Run: pip install pyaudiowpatch")
    
    # Find loopback device if not provided
    if device_info is None:
        device_info = find_wasapi_loopback_device(verbose=verbose)
    
    p = pyaudio.PyAudio()
    
    try:
        # Get device parameters
        device_index = device_info["index"]
        channels = device_info["maxInputChannels"]
        
        # Guard against weird channel counts
        if channels < 1:
            raise RuntimeError(f"Device '{device_info['name']}' has no input channels")
        channels = min(channels, 2)  # Stereo is enough, clamp to avoid issues
        
        sample_rate = int(device_info["defaultSampleRate"])
        
        # Override sample rate if specified in config
        if cfg.sample_rate:
            sample_rate = cfg.sample_rate
        
        frames_needed = int(sample_rate * (cfg.test_duration_ms / 1000.0))
        chunk_size = 1024
        
        if verbose:
            print(f"[audio] Capturing {cfg.test_duration_ms}ms from '{device_info['name']}'")
            print(f"[audio] Channels: {channels}, Sample rate: {sample_rate}")
        
        # Open stream
        stream = p.open(
            format=pyaudio.paFloat32,
            channels=channels,
            rate=sample_rate,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=chunk_size,
        )
        
        # Capture audio - request exact frames needed
        frames = []
        samples_captured = 0
        
        while samples_captured < frames_needed:
            to_read = min(chunk_size, frames_needed - samples_captured)
            data = stream.read(to_read, exception_on_overflow=False)
            frames.append(data)
            samples_captured += to_read
        
        stream.stop_stream()
        stream.close()
        
        # Convert to numpy array
        audio = np.frombuffer(b''.join(frames), dtype=np.float32)
        
        # Reshape to (samples, channels)
        if channels > 1:
            audio = audio.reshape(-1, channels)
            # Convert to mono
            mono = np.mean(audio, axis=1)
        else:
            mono = audio
        
        # Trim to exact length
        mono = mono[:frames_needed]
        
        # Remove DC offset
        mono = mono - float(np.mean(mono))
        
        return mono.astype(np.float32)
        
    finally:
        p.terminate()


def bandpass_filter(samples: np.ndarray, cfg: AudioConfig) -> np.ndarray:
    sr = cfg.sample_rate
    sos = butter(
        4,
        [cfg.kick_band_low_hz, cfg.kick_band_high_hz],
        btype="band",
        fs=sr,
        output="sos",
    )
    return sosfilt(sos, samples).astype(np.float32)


def envelope(samples: np.ndarray, cfg: AudioConfig) -> np.ndarray:
    """
    Simple amplitude envelope: abs + moving average smoothing.
    """
    sr = cfg.sample_rate
    x = np.abs(samples)

    win = max(1, int(sr * (cfg.env_smooth_ms / 1000.0)))
    kernel = np.ones(win, dtype=np.float32) / float(win)
    env = np.convolve(x, kernel, mode="same")

    # Normalize to 0..1 for stable thresholds (avoid div by zero)
    m = float(np.max(env)) if env.size else 0.0
    if m > 1e-9:
        env = env / m
    else:
        env = env * 0.0
    return env.astype(np.float32)


def compute_kick_score(samples: np.ndarray, cfg: AudioConfig) -> Tuple[float, dict]:
    """
    Returns (score, debug_info)
    """
    bp = bandpass_filter(samples, cfg)
    env = envelope(bp, cfg)

    sr = cfg.sample_rate
    min_dist = max(1, int(sr * (cfg.peak_min_distance_ms / 1000.0)))

    peaks, props = find_peaks(
        env,
        distance=min_dist,
        prominence=cfg.peak_prominence,
        height=cfg.peak_height,
    )

    peak_heights = props.get("peak_heights", np.array([], dtype=np.float32))
    peak_count = int(len(peaks))

    # Base score: count * mean amplitude (or 0)
    mean_peak = float(np.mean(peak_heights)) if peak_count > 0 else 0.0

    # Optional nonlinearity to reward stronger kicks
    score = float(peak_count) * (mean_peak ** cfg.score_power)
    
    # Require minimum peaks to avoid noise false positives
    if peak_count < cfg.min_peaks:
        score = 0.0

    debug = {
        "peak_count": peak_count,
        "mean_peak": mean_peak,
        "max_env": float(np.max(env)) if env.size else 0.0,
        "score": score,
    }
    return score, debug


# -----------------------------
# CLI
# -----------------------------
def print_device_table_pyaudio():
    """List all devices using PyAudioWPatch, highlighting loopback devices."""
    if not HAS_PYAUDIO:
        print("pyaudiowpatch not installed. Run: pip install pyaudiowpatch")
        return
    
    p = pyaudio.PyAudio()
    
    print("Index | InCh | OutCh | Loopback | Name")
    print("-" * 90)
    
    for i in range(p.get_device_count()):
        d = p.get_device_info_by_index(i)
        is_loopback = d.get("isLoopbackDevice", False)
        loopback_marker = "  YES  " if is_loopback else "   -   "
        print(
            f"{i:>5} | {d.get('maxInputChannels', 0):>4} | {d.get('maxOutputChannels', 0):>5} | "
            f"{loopback_marker} | {d.get('name', '')}"
        )
    
    p.terminate()
    
    print("\n[TIP] Use devices marked 'YES' in Loopback column for capturing system audio.")


def load_audio_config_from_config_json(path: str) -> AudioConfig:
    try:
        with open(path, "r", encoding="utf-8") as f:
            j = json.load(f)
        a = j.get("audio", {}) if isinstance(j, dict) else {}
        cfg = AudioConfig(
            sample_rate=int(a.get("sample_rate", 44100)),
            test_duration_ms=int(a.get("test_duration_ms", 800)),
            kick_band_low_hz=float(a.get("kick_band_low_hz", 40)),
            kick_band_high_hz=float(a.get("kick_band_high_hz", 140)),
        )
        return cfg
    except FileNotFoundError:
        return AudioConfig()


def main():
    ap = argparse.ArgumentParser(description="Serato Grid Fixer - Audio Scorer (WASAPI loopback)")
    ap.add_argument("--config", default="config.json", help="Path to config.json (audio section used)")
    ap.add_argument("--list-devices", action="store_true", help="List audio devices and exit")
    ap.add_argument("--device-like", type=str, default=None, help="Pick loopback device whose name contains this substring")
    ap.add_argument("--dump-wav", type=str, default=None, help="Optional path to write captured wav")
    ap.add_argument("--once", action="store_true", help="Capture and score once, then exit")
    ap.add_argument("--interactive", action="store_true", help="Press Enter to capture repeatedly")

    args = ap.parse_args()

    if args.list_devices:
        print_device_table_pyaudio()
        return

    cfg = load_audio_config_from_config_json(args.config)

    # Find loopback device
    device_info = find_wasapi_loopback_device(
        preferred_substring=args.device_like,
        verbose=True
    )

    def do_capture_and_score():
        # capture
        samples = capture_audio(cfg, device_info=device_info, verbose=False)

        # score
        score, dbg = compute_kick_score(samples, cfg)

        print(f"[score] {score:.4f} | peaks={dbg['peak_count']} | mean_peak={dbg['mean_peak']:.3f}")

        # dump wav if requested
        if args.dump_wav:
            if wav_write is None:
                print("[warn] scipy.io.wavfile not available; cannot dump wav.")
            else:
                # scale to int16
                y = np.clip(samples, -1.0, 1.0)
                y16 = (y * 32767.0).astype(np.int16)
                wav_write(args.dump_wav, cfg.sample_rate, y16)
                print(f"[audio] Wrote wav: {args.dump_wav}")

    if args.once:
        do_capture_and_score()
        return

    if args.interactive:
        print("Interactive mode. Press Enter to capture/score. Ctrl+C to exit.")
        while True:
            input()
            do_capture_and_score()
        return

    # default: capture a few times
    for _ in range(3):
        do_capture_and_score()
        time.sleep(0.5)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting.")

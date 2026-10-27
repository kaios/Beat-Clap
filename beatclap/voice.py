"""Text-to-speech for word and syllable prompts, synthesized in memory from a system engine.

Tries espeak-ng / espeak (Linux), `say` (macOS), then pyttsx3 (Windows SAPI and others).
Clips are trimmed and annotated with their vowel onset so the audible "beat" of each
syllable can be placed exactly on its timeline node.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile
import wave

import numpy as np

MAX_SYLLABLE_MS = 520     # stay shorter than one 600 ms beat so syllables never overlap
FADE_MS = 30


def _read_wav(data):
    with wave.open(io.BytesIO(data)) as w:
        sr, ch, width = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    if width != 2:
        raise ValueError(f"unsupported sample width {width}")
    x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    return x, sr


def _espeak(exe):
    def synth(text):
        out = subprocess.run([exe, "-s", "150", "--stdout", text],
                             capture_output=True, check=True, timeout=10).stdout
        return _read_wav(out)
    return synth


def _say(text):
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "s.wav")
        subprocess.run(["say", "-r", "170", "--file-format=WAVE", "--data-format=LEI16@22050",
                        "-o", path, text], check=True, timeout=10)
        with open(path, "rb") as f:
            return _read_wav(f.read())


def _pyttsx3():
    import pyttsx3
    engine = pyttsx3.init()

    def synth(text):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "s.wav")
            engine.save_to_file(text, path)
            engine.runAndWait()
            with open(path, "rb") as f:
                return _read_wav(f.read())
    return synth


def find_engine():
    """Returns (name, synth_fn) or (None, None). synth_fn(text) -> (float32 mono, samplerate)."""
    for exe in ("espeak-ng", "espeak"):
        if shutil.which(exe):
            return exe, _espeak(exe)
    if sys.platform == "darwin" and shutil.which("say"):
        return "say", _say
    try:
        return "pyttsx3", _pyttsx3()
    except Exception:
        return None, None


def prepare(samples, sr, target_sr, max_ms=None):
    """Resample, trim silence, cap length with a fade, normalize.

    Returns (samples, onset_index): onset is where the smoothed envelope first reaches
    half its peak, i.e. roughly the vowel attack that listeners hear as the beat.
    """
    x = np.asarray(samples, dtype=np.float32)
    if sr != target_sr and len(x):
        n = int(len(x) * target_sr / sr)
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    peak = float(np.max(np.abs(x))) if len(x) else 0.0
    if peak <= 0:
        return np.zeros(0, np.float32), 0
    loud = np.nonzero(np.abs(x) > peak * 0.02)[0]
    x = x[loud[0]:loud[-1] + 1]
    if max_ms is not None:
        x = x[: int(target_sr * max_ms / 1000)].copy()
    fade = min(len(x), int(target_sr * FADE_MS / 1000))
    if fade:
        x[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)
    x *= 0.8 / peak
    win = max(1, int(target_sr * 0.01))
    env = np.convolve(np.abs(x), np.ones(win) / win, mode="same")
    onset = int(np.argmax(env >= env.max() * 0.5))
    return x, onset


class Clip:
    def __init__(self, sound, onset_ms, length_ms):
        self.sound, self.onset_ms, self.length_ms = sound, onset_ms, length_ms


class Voice:
    def __init__(self):
        import pygame
        self._pygame = pygame
        self.engine, self._synth = find_engine() if pygame.mixer.get_init() else (None, None)
        self._cache = {}

    @property
    def available(self):
        return self._synth is not None

    def clip(self, text, syllable=True):
        """Synthesize (cached). Returns a Clip, or None if no engine or synthesis failed."""
        key = (text, syllable)
        if key not in self._cache:
            self._cache[key] = self._make(text, syllable) if self.available else None
        return self._cache[key]

    def _make(self, text, syllable):
        try:
            raw, sr = self._synth(text)
        except Exception:
            return None
        rate, _, channels = self._pygame.mixer.get_init()
        x, onset = prepare(raw, sr, rate, MAX_SYLLABLE_MS if syllable else None)
        if not len(x):
            return None
        pcm = (x * 32767).astype(np.int16)
        if channels > 1:
            pcm = np.repeat(pcm[:, None], channels, axis=1)
        sound = self._pygame.sndarray.make_sound(np.ascontiguousarray(pcm))
        return Clip(sound, onset * 1000.0 / rate, len(x) * 1000.0 / rate)

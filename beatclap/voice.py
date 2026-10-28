"""Voice prompts: words, syllables and the mic-check count.

The voice is pre-rendered with Kokoro, a neural TTS model, and bundled as voice_clips.npz
(see tools/generate_voice.py). Anything missing from the bundle falls back to a system
engine synthesized in memory: espeak-ng / espeak (Linux), `say` (macOS), then pyttsx3
(Windows SAPI and others). Clips are trimmed and annotated with their vowel onset so the
audible "beat" of each syllable can be placed exactly on its timeline node.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile
import wave

import numpy as np

from .words import spoken_syllables

BUNDLE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voice_clips.npz")
COUNT_WORDS = ["one", "two", "three", "four"]
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
    def __init__(self, bundle=BUNDLE):
        import pygame
        self._pygame = pygame
        self._cache = {}
        self._bank, self._bank_sr = {}, 0
        self._fallback = None  # (name, synth) once looked up
        if pygame.mixer.get_init() and os.path.exists(bundle):
            try:
                with np.load(bundle) as d:
                    self._bank_sr = int(d["sr"])
                    self._bank = {k: d[k] for k in d.files if k[:2] in ("w:", "s:", "c:")}
            except Exception:
                self._bank = {}

    @property
    def engine(self):
        return "Kokoro" if self._bank else self._fallback_engine()[0]

    @property
    def available(self):
        return bool(self._bank) or self._fallback_engine()[1] is not None

    def word_clip(self, word):
        return self._clip(f"w:{word}", word.replace("-", "").lower(), syllable=False)

    def syllable_clip(self, word, index):
        return self._clip(f"s:{word}:{index}", spoken_syllables(word)[index], syllable=True)

    def count_clip(self, n):
        return self._clip(f"c:{n}", COUNT_WORDS[n - 1], syllable=True)

    def _fallback_engine(self):
        if self._fallback is None:
            self._fallback = find_engine() if self._pygame.mixer.get_init() else (None, None)
        return self._fallback

    def _clip(self, key, text, syllable):
        """Bundled clip for key, else synthesize text (cached). None if neither works."""
        if key not in self._cache:
            raw = None
            if key in self._bank:
                raw = (self._bank[key].astype(np.float32) / 32768.0, self._bank_sr)
            elif self._fallback_engine()[1] is not None:
                try:
                    raw = self._fallback_engine()[1](text)
                except Exception:
                    raw = None
            self._cache[key] = self._make(*raw, syllable) if raw else None
        return self._cache[key]

    def _make(self, samples, sr, syllable):
        rate, _, channels = self._pygame.mixer.get_init()
        x, onset = prepare(samples, sr, rate, MAX_SYLLABLE_MS if syllable else None)
        if not len(x):
            return None
        pcm = (x * 32767).astype(np.int16)
        if channels > 1:
            pcm = np.repeat(pcm[:, None], channels, axis=1)
        sound = self._pygame.sndarray.make_sound(np.ascontiguousarray(pcm))
        return Clip(sound, onset * 1000.0 / rate, len(x) * 1000.0 / rate)

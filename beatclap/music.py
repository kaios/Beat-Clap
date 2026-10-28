"""Procedural background music: an 8-bar loop per stage, synthesized with numpy at 100 BPM.

Songs are written as scale degrees on a step grid (see stages.py). Sample 0 of the loop is
beat 0 of the timeline and the loop is exactly 8 bars long, so it stays locked to the rail.
After mixing, transients are tamed so no drum hit can look like a clap to the mic detector.
"""
from dataclasses import dataclass, field

import numpy as np

from . import core

BARS = 8
STEPS_PER_BEAT = 4                                    # 16th-note grid
STEPS_PER_BAR = STEPS_PER_BEAT * core.BEATS_PER_BAR
STEP_S = core.BEAT_MS / 1000.0 / STEPS_PER_BEAT

SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
}

# Transient taming: the 5 ms RMS may exceed its own slow (0.75 s) average by at most this
# much. The clap detector needs 2.5x its ambient floor, so the music stays well below it.
CREST_LIMIT = 1.6
PEAK = 0.5


@dataclass
class Song:
    root: int                 # MIDI note of scale degree 1 for the melody
    scale: str
    chords: list              # chord root as 0-based scale degree, one per bar (cycled)
    melody: str               # 8th-note tokens over 8 bars: degree [' or ,]  "-" hold  "." rest
    lead: str
    bass: str                 # 16th tokens per bar (cycled): R root, F fifth, O octave, - hold, . rest
    bass_voice: str
    comps: list = field(default_factory=list)    # (voice, 16-step pattern, "chord" | "arp")
    kick: str = "." * 16      # 16 steps per bar: x full, o soft, . rest
    snare: str = "." * 16
    hat: str = "." * 16
    sevenths: bool = False


def midi_hz(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def _degree_semis(scale, index):
    """0-based scale index (may exceed 6 or go negative) -> semitones from the root."""
    return scale[index % 7] + 12 * (index // 7)


def _melody_semis(scale, token):
    deg = int(token.rstrip("',")) - 1
    return _degree_semis(scale, deg) + 12 * token.count("'") - 12 * token.count(",")


def _events(tokens, step_len):
    """Parse a token list into (start_step, length_steps, token) note events."""
    out = []
    for i, tok in enumerate(tokens):
        if tok in "-.":
            if tok == "." and out and out[-1][3]:
                out[-1][3] = False           # a rest ends the held note
            elif tok == "-" and out and out[-1][3]:
                out[-1][1] += step_len
            continue
        out.append([i * step_len, step_len, tok, True])
    return [(s, n, t) for s, n, t, _ in out]


# ---------- voices ----------

def _env(n, sr, attack, release, hold_n):
    """Linear attack, flat hold, linear release; attacks are never shorter than 3 ms."""
    a = max(int(sr * max(attack, 0.003)), 1)
    r = max(int(sr * release), 1)
    e = np.ones(n, np.float32)
    e[:a] = np.linspace(0, 1, a)
    end = min(hold_n, n)
    e[end:end + r] = np.linspace(1, 0, len(e[end:end + r]))
    e[end + r:] = 0
    return e


def _additive(freq, t, sr, amps, detune=0.0):
    out = np.zeros_like(t)
    for k, amp in enumerate(amps, start=1):
        if amp and freq * k < sr / 2.2:
            out += amp * np.sin(2 * np.pi * freq * k * t)
            if detune:
                out += amp * np.sin(2 * np.pi * freq * k * (1 + detune) * t)
    return out


SAW = [1 / k for k in range(1, 11)]
SQUARE = [1 / k if k % 2 else 0 for k in range(1, 10)]


def tone(voice, freq, dur, sr):
    """Render one note. dur is the held length in seconds; the tail is added on top."""
    tail = {"pad": 0.4, "marimba": 0.6, "pluck": 0.5, "keys": 0.5}.get(voice, 0.12)
    n = int(sr * (dur + tail))
    t = np.arange(n, dtype=np.float32) / sr
    hold = int(sr * dur)
    if voice == "pluck":
        sig = _additive(freq, t, sr, SAW[:7]) * np.exp(-t / 0.22)
        return sig * _env(n, sr, 0.004, tail, n)
    if voice == "keys":
        sig = _additive(freq, t, sr, [1, 0.4, 0.2]) * np.exp(-t / 0.4)
        return sig * _env(n, sr, 0.005, 0.08, hold)
    if voice == "marimba":
        sig = np.sin(2 * np.pi * freq * t) * np.exp(-t / 0.35)
        sig += 0.35 * np.sin(2 * np.pi * freq * 4 * t) * np.exp(-t / 0.05)
        return sig * _env(n, sr, 0.003, tail, n)
    if voice in ("square", "chip"):
        return _additive(freq, t, sr, SQUARE) * 0.8 * _env(n, sr, 0.005, 0.04, hold)
    if voice == "saw":
        return _additive(freq, t, sr, SAW, detune=0.004) * 0.5 * _env(n, sr, 0.01, 0.08, hold)
    if voice == "clav":
        amps = [1 / k * (1 if k % 2 else 0.6) for k in range(1, 7)]
        return _additive(freq, t, sr, amps) * np.exp(-t / 0.12) * _env(n, sr, 0.003, 0.03, hold)
    if voice == "organ":
        return _additive(freq, t, sr, [1, 0.5, 0.3, 0.2]) * _env(n, sr, 0.008, 0.03, hold)
    if voice == "pad":
        return _additive(freq, t, sr, SAW[:5], detune=0.003) * 0.5 * _env(n, sr, 0.3, tail, hold)
    if voice == "sub":
        return _additive(freq, t, sr, [1, 0.25]) * _env(n, sr, 0.008, 0.05, hold)
    if voice == "slap":
        amps = [1, 0.5, 1 / 9, 0.2, 1 / 25]
        return _additive(freq, t, sr, amps) * np.exp(-t / 0.25) * _env(n, sr, 0.004, 0.04, hold)
    if voice == "square_bass":
        return _additive(freq, t, sr, SQUARE[:7]) * 0.7 * _env(n, sr, 0.006, 0.04, hold)
    if voice == "saw_bass":
        return _additive(freq, t, sr, SAW[:6]) * 0.6 * _env(n, sr, 0.006, 0.05, hold)
    raise ValueError(f"unknown voice {voice}")


def drum(kind, sr, rng):
    if kind == "kick":
        n = int(sr * 0.35)
        t = np.arange(n, dtype=np.float32) / sr
        freq = 45 + 65 * np.exp(-t / 0.03)
        phase = 2 * np.pi * np.cumsum(freq) / sr
        return np.sin(phase) * np.exp(-t / 0.15) * _env(n, sr, 0.004, 0.05, n)
    if kind == "snare":  # soft brush: filtered noise plus a little body
        n = int(sr * 0.25)
        t = np.arange(n, dtype=np.float32) / sr
        noise = np.convolve(rng.uniform(-1, 1, n), np.ones(4) / 4, mode="same")
        sig = noise * np.exp(-t / 0.08) + 0.4 * np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.04)
        return sig * _env(n, sr, 0.006, 0.03, n)
    if kind == "hat":
        n = int(sr * 0.08)
        t = np.arange(n, dtype=np.float32) / sr
        noise = np.diff(rng.uniform(-1, 1, n + 1))
        return noise * np.exp(-t / 0.025) * _env(n, sr, 0.002, 0.01, n)
    raise ValueError(kind)


# ---------- arrangement ----------

def _add(buf, start, sig, gain):
    """Mix sig into buf at start, wrapping the tail to the loop start for a seamless loop."""
    n = len(buf)
    start %= n
    first = min(len(sig), n - start)
    buf[start:start + first] += gain * sig[:first]
    rest = sig[first:]
    while len(rest):
        k = min(len(rest), n)
        buf[:k] += gain * rest[:k]
        rest = rest[k:]


def loop_samples(sr):
    return int(round(BARS * core.BEATS_PER_BAR * core.BEAT_MS / 1000.0 * sr))


def chord_semis(song, bar):
    scale = SCALES[song.scale]
    d = song.chords[bar % len(song.chords)]
    idx = [d, d + 2, d + 4] + ([d + 6] if song.sevenths else [])
    return [_degree_semis(scale, i) for i in idx]


def render(song, sr, seed=7):
    rng = np.random.default_rng(seed)
    scale = SCALES[song.scale]
    buf = np.zeros(loop_samples(sr), np.float32)
    at = lambda step: int(round(step * STEP_S * sr))

    # lead melody (8th-note grid)
    for start, length, tok in _events(song.melody.split(), 2):
        f = midi_hz(song.root + _melody_semis(scale, tok))
        _add(buf, at(start), tone(song.lead, f, length * STEP_S * 0.9, sr), 0.30)

    for bar in range(BARS):
        base = bar * STEPS_PER_BAR
        chord = chord_semis(song, bar)
        key = song.root % 12                  # bass and chords sit in fixed registers
        root = 36 + key + chord[0]

        for start, length, tok in _events(list(song.bass), 1):
            semis = {"R": 0, "F": 7, "O": 12}[tok]
            f = midi_hz(root + semis)
            _add(buf, at(base + start), tone(song.bass_voice, f, length * STEP_S * 0.9, sr), 0.34)

        for voice, pattern, mode in song.comps:
            arp_i = 0
            for start, length, _ in _events(list(pattern), 1):
                notes = chord if mode == "chord" else [chord[arp_i % len(chord)] + 12 * (arp_i // len(chord) % 2)]
                arp_i += 1
                gain = 0.16 / len(notes) ** 0.5 if mode == "chord" else 0.13
                for semis in notes:
                    f = midi_hz(48 + key + semis)
                    _add(buf, at(base + start), tone(voice, f, length * STEP_S * 0.95, sr), gain)

        for kind, pattern, gain in (("kick", song.kick, 0.55),
                                    ("snare", song.snare, 0.22),
                                    ("hat", song.hat, 0.07)):
            for step, ch in enumerate(pattern):
                if ch in "xo":
                    _add(buf, at(base + step), drum(kind, sr, rng), gain * (1 if ch == "x" else 0.5))

    buf = tame_transients(buf, sr)
    peak = float(np.max(np.abs(buf))) or 1.0
    return buf * (PEAK / peak)


def tame_transients(x, sr, limit=CREST_LIMIT, block_s=0.005, tau_s=0.75):
    """Duck any 5 ms block whose RMS exceeds `limit` x the slow running RMS of the loop.

    Levels are measured on the first difference, the same high-passed signal the clap
    detector listens to (audio.hf_rms), so hi-hats count as much as the detector hears them.
    """
    block = max(1, int(sr * block_s))
    n = len(x)
    nb = -(-n // block)
    for _ in range(6):  # ducking lowers the slow average a little, so iterate to a fixed point
        hp = np.diff(x, prepend=x[-1])  # loop wraps, so the first sample follows the last
        padded = np.concatenate([hp, hp[: nb * block - n]])
        fast = np.sqrt(np.mean(padded.reshape(nb, block) ** 2, axis=1)) + 1e-9
        alpha = min(1.0, block_s / tau_s)
        slow = np.empty(nb)
        acc = float(np.mean(fast))
        for _pass in range(2):  # second lap around the loop gives the steady-state average
            for i in range(nb):
                acc += alpha * (fast[i] - acc)
                slow[i] = acc
        gain = np.minimum(1.0, limit * 0.95 * slow / fast)
        if gain.min() >= 0.999:
            break
        # widen each dip to its neighbours, then smooth over one block so gain changes don't click
        gain = np.minimum(gain, np.minimum(np.roll(gain, 1), np.roll(gain, -1)))
        g = np.repeat(gain, block)
        g = np.convolve(np.concatenate([g[-block:], g, g[:block]]), np.ones(block) / block,
                        mode="same")[block:block + n]
        x = x * g.astype(np.float32)
    return x

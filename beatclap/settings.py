"""Persist player settings (language, toggles, mic calibration) as JSON in the user's config dir."""
import json
import os
import sys

DEFAULTS = {
    "lang": "en",
    "voice_on": True,
    "music_on": True,
    "metronome": False,
    "stress_mode": False,
    "word_cards": True,
    "offset_ms": 0,
    "threshold": 2.5,   # clap = high-band RMS above this many times the room's floor
}


def path():
    if os.environ.get("ANDROID_PRIVATE"):  # the app's private storage on Android
        return os.path.join(os.environ["ANDROID_PRIVATE"], "settings.json")
    if sys.platform == "win32":
        return os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"),
                            "BeatClap", "settings.json")
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/BeatClap/settings.json")
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "beat-clap", "settings.json")


def load(file=None):
    out = dict(DEFAULTS)
    try:
        with open(file or path(), encoding="utf-8") as f:
            data = json.load(f)
        for key, default in DEFAULTS.items():
            value = data.get(key)
            if isinstance(default, bool):
                ok = isinstance(value, bool)
            elif isinstance(default, (int, float)):
                ok = isinstance(value, (int, float)) and not isinstance(value, bool)
            else:
                ok = isinstance(value, str)
            if ok:
                out[key] = type(default)(value)
        if out["lang"] not in ("en", "ja"):
            out["lang"] = DEFAULTS["lang"]
    except (OSError, ValueError, AttributeError):
        pass
    return out


def save(values, file=None):
    file = file or path()
    try:
        os.makedirs(os.path.dirname(file), exist_ok=True)
        tmp = file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({k: values[k] for k in DEFAULTS if k in values}, f, indent=2)
        os.replace(tmp, file)
    except OSError:
        pass

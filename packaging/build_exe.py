"""Build dist/BeatClap.exe with PyInstaller. Run with a *Windows* Python that has
pygame, numpy, sounddevice, pyttsx3 and pyinstaller installed:

    py packaging\\build_exe.py

On Linux, packaging/build-exe.sh runs this under Wine.
"""
import os
import sys

import PyInstaller.__main__

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRY = os.path.join(ROOT, "packaging", "beat_clap_entry.py")

PyInstaller.__main__.run([
    ENTRY,
    "--name", "BeatClap",
    "--onefile",
    "--windowed",                         # no console window behind the game
    "--noconfirm",
    "--clean",
    "--paths", ROOT,
    "--add-data", os.pathsep.join([os.path.join(ROOT, "beatclap", "voice_clips.npz"), "beatclap"]),
    "--distpath", os.path.join(ROOT, "dist"),
    "--workpath", os.path.join(ROOT, "build", "pyinstaller"),
    "--specpath", os.path.join(ROOT, "build"),
    # pyttsx3 picks its driver with importlib and SAPI goes through comtypes' generated
    # wrappers, so PyInstaller can't see these imports on its own.
    "--collect-submodules", "pyttsx3",
    "--collect-submodules", "comtypes",
    "--hidden-import", "pythoncom",
    "--hidden-import", "pywintypes",
    "--exclude-module", "win32ui",        # pywin32's MFC UI layer; unused and needs mfc140u.dll
    "--exclude-module", "tkinter",
    *sys.argv[1:],
])

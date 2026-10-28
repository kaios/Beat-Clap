"""Build dist/BeatClap_v<version>.exe with PyInstaller. Run with a *Windows* Python that has
pygame, numpy, sounddevice, pyttsx3 and pyinstaller installed:

    py packaging\\build_exe.py

On Linux, packaging/build-exe.sh runs this under Wine.
"""
import os
import re
import sys

import PyInstaller.__main__

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRY = os.path.join(ROOT, "packaging", "beat_clap_entry.py")
with open(os.path.join(ROOT, "beatclap", "__init__.py"), encoding="utf-8") as f:
    VERSION = re.search(r'__version__ = "([^"]+)"', f.read()).group(1)
NAME = f"BeatClap_v{VERSION}"

# Windows "Details" tab: file and product version, description, original file name.
nums = tuple(int(n) for n in (VERSION.split(".") + ["0"] * 4)[:4])
os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
VERSION_FILE = os.path.join(ROOT, "build", "exe-version.txt")
with open(VERSION_FILE, "w", encoding="utf-8") as f:
    f.write(f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={nums}, prodvers={nums}, mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('FileDescription', 'Beat Clap'),
      StringStruct('FileVersion', '{VERSION}'),
      StringStruct('InternalName', 'BeatClap'),
      StringStruct('OriginalFilename', '{NAME}.exe'),
      StringStruct('ProductName', 'Beat Clap'),
      StringStruct('ProductVersion', '{VERSION}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""")

PyInstaller.__main__.run([
    ENTRY,
    "--name", NAME,
    "--version-file", VERSION_FILE,
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

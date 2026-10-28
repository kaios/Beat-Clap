#!/bin/sh
# Build dist/BeatClap.exe on Linux by running Windows Python + PyInstaller under Wine.
# PyInstaller can't cross-compile, so this keeps a dedicated Wine prefix with Windows
# Python and the game's dependencies. First run sets it up (needs network); later runs reuse it.
#   WINEPREFIX  prefix to use (default: build/wine, separate from ~/.wine)
set -eu

cd "$(dirname "$0")/.."
PY_VERSION=3.11.9
export WINEPREFIX="${WINEPREFIX:-$PWD/build/wine}"
export WINEDEBUG=-all WINEDLLOVERRIDES="mscoree,mshtml="
PY='C:\Python311\python.exe'

winpy() { wine "$PY" "$@" < /dev/null; }  # Windows Python needs a valid stdin handle

if ! winpy -c "import PyInstaller" 2>/dev/null; then
    echo "Setting up Windows Python $PY_VERSION in $WINEPREFIX ..."
    mkdir -p "$WINEPREFIX" build/download
    wineboot -i >/dev/null 2>&1 || true
    winecfg -v win10 >/dev/null 2>&1        # Python 3.11 refuses to install on Wine's default Win7
    installer="build/download/python-$PY_VERSION-amd64.exe"
    [ -f "$installer" ] || curl -fsSL -o "$installer" \
        "https://www.python.org/ftp/python/$PY_VERSION/python-$PY_VERSION-amd64.exe"
    wine "$installer" /quiet InstallAllUsers=0 PrependPath=0 Include_test=0 Include_doc=0 \
        Include_tcltk=0 Include_launcher=0 'TargetDir=C:\Python311' >/dev/null 2>&1
    winpy -m pip install --disable-pip-version-check -q \
        pygame==2.6.1 numpy==1.26.4 sounddevice==0.5.1 pyttsx3==2.90 pyinstaller==6.10.0
fi

winpy packaging/build_exe.py --log-level WARN "$@"
ls -l dist/BeatClap.exe

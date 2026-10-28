#!/bin/sh
# Build dist/beat-clap-<version>-arm64-v8a-debug.apk with buildozer / python-for-android.
# Uses the Android SDK/NDK in ~/.buildozer (the first build downloads them, ~7 GB) and a
# buildozer venv in ~/.venvs/beatclap-android. First build takes a long while; later ones reuse
# build/android/.buildozer.
set -eu

cd "$(dirname "$0")/.."
VERSION="${VERSION:-0.3.0}"
VENV="${VENV:-$HOME/.venvs/beatclap-android}"
STAGE=build/android

if [ ! -x "$VENV/bin/buildozer" ]; then
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install -q buildozer==1.6.0 setuptools==84.2.1 sh==2.4.0
    # buildozer pins an old Cython; the pygame 2.6.1 recipe needs 3.1+ (Python 3.14 support)
    "$VENV/bin/pip" install -q cython==3.2.9
fi

mkdir -p "$STAGE"
rm -rf "$STAGE/src" "$STAGE/p4a-recipes"
mkdir -p "$STAGE/src/beatclap"
cp beatclap/*.py beatclap/voice_clips.npz "$STAGE/src/beatclap/"
cp packaging/android/main.py "$STAGE/src/"
cp -r packaging/android/p4a-recipes "$STAGE/"
sed "s/@VERSION@/$VERSION/" packaging/android/buildozer.spec > "$STAGE/buildozer.spec"
python3 packaging/android/make_icon.py "$STAGE"

# VIRTUAL_ENV, as `activate` would set it: buildozer checks it to avoid `pip install --user`
(cd "$STAGE" && VIRTUAL_ENV="$VENV" PATH="$VENV/bin:$PATH" buildozer android debug)
mkdir -p dist
cp "$STAGE"/bin/beatclap-"$VERSION"-*-debug.apk dist/
ls -l dist/*.apk

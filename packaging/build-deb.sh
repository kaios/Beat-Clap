#!/bin/sh
# Build dist/beat-clap_<version>_all.deb from the working tree.
# Maintainer defaults to the git identity; override with DEBFULLNAME / DEBEMAIL.
set -eu

cd "$(dirname "$0")/.."
VERSION="${VERSION:-0.3.0}"
NAME="${DEBFULLNAME:-$(git config user.name)}"
EMAIL="${DEBEMAIL:-$(git config user.email)}"
PKG=beat-clap
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
ROOT="$STAGE/${PKG}_${VERSION}_all"

install -d "$ROOT/DEBIAN" "$ROOT/usr/bin" "$ROOT/usr/share/$PKG/beatclap" \
    "$ROOT/usr/share/applications" "$ROOT/usr/share/doc/$PKG"
install -m 644 beatclap/*.py beatclap/voice_clips.npz "$ROOT/usr/share/$PKG/beatclap/"

cat > "$ROOT/usr/bin/$PKG" <<'EOF'
#!/bin/sh
PYTHONPATH="/usr/share/beat-clap${PYTHONPATH:+:$PYTHONPATH}" exec python3 -m beatclap "$@"
EOF
chmod 755 "$ROOT/usr/bin/$PKG"

cat > "$ROOT/usr/share/applications/$PKG.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Beat Clap
Name[ja]=ビート・クラップ
Comment=Clap along with English syllables at 100 BPM
Comment[ja]=英語の音節に合わせて手をたたくリズムゲーム
Exec=beat-clap
Icon=audio-input-microphone
Terminal=false
Categories=Game;Education;
EOF

install -m 644 README.md "$ROOT/usr/share/doc/$PKG/"
cat > "$ROOT/usr/share/doc/$PKG/copyright" <<EOF
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: Beat Clap

Files: *
Copyright: $(date +%Y) $NAME
License: GPL-3+
 On Debian systems the full text of the GNU General Public License version 3
 is in /usr/share/common-licenses/GPL-3.

Files: usr/share/beat-clap/beatclap/voice_clips.npz
Comment: Speech generated with the Kokoro-82M model (https://huggingface.co/hexgrad/Kokoro-82M).
License: Apache-2.0
 On Debian systems the full text of the Apache License 2.0 is in
 /usr/share/common-licenses/Apache-2.0.
EOF
printf '%s (%s) unstable; urgency=low\n\n  * Initial release.\n\n -- %s <%s>  %s\n' \
    "$PKG" "$VERSION" "$NAME" "$EMAIL" "$(date -R)" \
    | gzip -9n > "$ROOT/usr/share/doc/$PKG/changelog.Debian.gz"

cat > "$ROOT/DEBIAN/control" <<EOF
Package: $PKG
Version: $VERSION
Architecture: all
Maintainer: $NAME <$EMAIL>
Installed-Size: $(du -sk "$ROOT/usr" | cut -f1)
Depends: python3 (>= 3.9), python3-pygame (>= 2.0), python3-numpy, python3-pyaudio
Recommends: fonts-noto-cjk | fonts-ipafont-gothic | fonts-droid-fallback
Suggests: espeak-ng
Section: games
Priority: optional
Description: clap-along rhythm game for English syllables
 Beat Clap speaks an English word, then each of its syllables on the beat
 at 100 BPM. Clap into the microphone once per syllable to score.
 .
 The interface switches between English and Japanese. The voice is a
 bundled neural voice (Kokoro) and claps are captured with PyAudio; without
 a microphone the SPACE key works as the clap.
EOF

mkdir -p dist
fakeroot dpkg-deb --build "$ROOT" "dist/${PKG}_${VERSION}_all.deb"

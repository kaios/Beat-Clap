# Beat Clap

A rhythm game for practicing English syllables. Each word is shown split into
syllables (`RO-BOT`, `U-NI-VER-SI-TY`), and each syllable is a node on a rail
that scrolls at **100 BPM**. The game says the whole word once, then speaks it
again one syllable per beat. Clap into your microphone along with each
syllable as its node crosses the hit ring.

There are five stages, each with its own background song, and the words get
longer as you go. Match 60% of a stage's syllables to clear it and move on to
the next.

| # | Stage | Words | Music |
|---|---|---|---|
| 1 | Sunny Start | 1–2 syllables | C major pluck pop |
| 2 | Bubble Pop | 2–3 syllables | F major chiptune with arpeggios |
| 3 | Midnight Funk | 3 syllables | E dorian funk: slap bass, clav, organ |
| 4 | Island Breeze | 3–4 syllables | G major tropical marimba with offbeat organ |
| 5 | Neon Finale | 4–5 syllables | A minor synthwave: saw lead, pad, arpeggios |

**Syllable stress** is shown on every word: the stressed syllable is written in
capitals on a big gold node (`ba-NA-na`), and the voice says it louder.

- **Stress mode** (optional, in the menu, needs a mic) is the advanced challenge: clap
  loud on the big node and soft on the small ones. Each word gets a verdict, shown
  as a separate Stress count. Points don't change: still 1 per syllable.
- **Word cards** (on by default) appear after you hit every syllable of a word, with a
  picture, its meaning and an example sentence. In Japanese mode the meaning and
  sentence are also given in Japanese. Turning them on adds one bar between words
  for reading time, and the music keeps going.

The graphics, music, metronome click and app icon are all generated in code, and
fonts come from the system. The only asset is the bundled voice (see below).

The interface switches between English and Japanese (press **L**, or use the
menu). The words to clap always stay in English.

## Install

| Platform | Package | How |
|---|---|---|
| Debian / Ubuntu | `beat-clap_0.4.0_all.deb` | `sudo apt install ./beat-clap_0.4.0_all.deb`, then run `beat-clap` (use `apt`, not `dpkg -i`, so the mic library gets installed) |
| Windows | `BeatClap_v0.4.0.exe` | Double-click. It isn't code-signed, so SmartScreen may warn: choose "More info" → "Run anyway". |
| Android 10+ | `beatclap-0.4.0-arm64-v8a-debug.apk` | Copy it to the phone, open it, and allow installing from unknown sources. Allow the microphone on first launch. |

Packages are built into `dist/` by the scripts in `packaging/` (see below).

**First run: do a Mic check** (in the menu). You clap along to 8 beats with the
music playing. The game measures how loud your claps are compared to the room
and to its own voice, and how late your mic delivers sound. It then sets the
clap threshold and timing offset for you. Settings are saved to
`~/.config/beat-clap/settings.json` (`%APPDATA%\BeatClap` on Windows, app
storage on Android).

## Run from source

```bash
pip install -r requirements.txt     # pygame, numpy, sounddevice (or pyaudio)
python -m beatclap                  # --lang ja, --words 15, --device N
python -m beatclap --list-devices
```

If neither `sounddevice` nor `pyaudio` can open a mic, the game falls back to
**SPACE** (or a tap / click on the screen) as the clap.

The voice is a natural neural voice (Kokoro, voice `af_heart`), pre-rendered once
and bundled as `beatclap/voice_clips.npz` (4.6 MB): every word, every syllable,
and the mic-check count. To regenerate it after changing the word list, see
`tools/generate_voice.py`. Any word missing from the bundle falls back to the
system's speech engine (`espeak-ng`, macOS `say`, or Windows SAPI).

## Debian package

```bash
./packaging/build-deb.sh                      # -> dist/beat-clap_0.4.0_all.deb
sudo apt install ./dist/beat-clap_0.4.0_all.deb
beat-clap
```

The package depends on `python3-pygame`, `python3-numpy` and `python3-pyaudio`
(the mic). The maintainer field comes from your git identity; override it with
`DEBFULLNAME` / `DEBEMAIL`. The version for every package comes from `__version__`
in `beatclap/__init__.py`, so bump it there; the exe also carries it in its file
properties, and the menu shows it.

## Windows .exe

```bash
./packaging/build-exe.sh        # Linux: builds dist/BeatClap_v0.4.0.exe under Wine
```

The first run sets up a separate Wine prefix in `build/wine` with Windows Python
3.11 and the pinned dependencies (it needs network access). Later runs reuse it.
On Windows itself, install the same packages and run `py packaging\build_exe.py`.

The exe is a single 38 MB file with Python and all libraries bundled. It uses the
bundled Kokoro voice and Japanese fonts that come with Windows (Yu
Gothic, Meiryo, MS Gothic).

## Android .apk

```bash
./packaging/build-apk.sh        # -> dist/beatclap-0.4.0-arm64-v8a-debug.apk
```

This builds with buildozer / python-for-android, using the Android SDK/NDK in
`~/.buildozer` and a buildozer venv in `~/.venvs/beatclap-android`. Everything
else lives under `build/android`. The first build compiles Python, numpy, pygame
and SDL2 for ARM and takes a long time; later builds are quicker. The app targets
Android 10+ on 64-bit ARM (`arm64-v8a`), and asks for the microphone on first
launch.

On Android the mic is read with `AudioRecord`, preferring the `UNPROCESSED`
source so the system's noise suppression doesn't flatten claps. Everything is
playable by touch: tap menu items (tap the `<` / `>` ends to change a value),
use the on-screen buttons, and the Back button goes back. The launcher icon is
drawn in code (`packaging/android/make_icon.py`).

## How it works

| Piece | Where | Details |
|---|---|---|
| Audio capture | `beatclap/audio.py` `MicListener` | sounddevice or PyAudio on desktop, `AudioRecord` on Android. 256-sample blocks at 48 kHz (44.1 kHz on Android, ~5 ms) go into a 1 s ring buffer. RMS is computed per block on the first difference of the signal, a gentle high-pass: claps are broadband, while speech and music sit mostly low, so on this level an equally loud clap reads about 4.7× louder than a spoken syllable. Timestamps come from the ADC clock, mapped to `perf_counter`. |
| Clap detector | `ClapDetector` | Fires when `rms > ambient_floor * 2.5` (adjustable as "Clap threshold", 1.3–3.0, set by the mic check), then blocks for **150 ms**. The level must also fall back below threshold before the next clap, so one sustained noise counts once. The floor adapts only on quiet blocks. |
| Voice | `beatclap/voice.py`, `words.SPOKEN` | The word is spoken on beat 1 of its read bar. Each syllable is spoken so its vowel onset (where the loudness first reaches half its peak) lands on the node. Syllables use respellings (`U-NI-VER-SI-TY` is spoken as `you-nih-ver-sih-tee`) so TTS doesn't read letter names. |
| Self-trigger guard | `ClapDetector.measure_voice` / `guard_voice` | While the word preview plays, the detector records how loud the game's voice is at the mic (no claps register then). While a syllable plays, a clap must be 1.2× louder than that, so speaker output can't score points by itself. |
| Music | `beatclap/music.py`, `beatclap/stages.py` | Each song is an 8-bar loop at exactly 100 BPM, synthesized with numpy when the stage starts. Sample 0 is beat 0, so the music stays locked to the rail. It plays on its own mixer channel and peaks at about a third of the voice's level. |
| Music vs. the mic | `music.tame_transients`, `ClapDetector.rewarm` | Hits whose 5 ms RMS rises more than 1.6× above the loop's running average get softened, so drums can never reach the detector's 2.5× threshold. When a stage starts, the detector re-learns the background level with the music playing. If the room stays louder for 0.3 s or more (a fan, for example), the floor follows it instead of getting stuck. |
| Mic check | `Game.start_calibration` / `measure_calibration` | Plays a spoken count of four, then 8 beats to clap on. For each beat it finds the loudest block within ±250 ms. From those it sets the timing offset (median) and the clap threshold (half the claps' median loudness over the room, never above 2.5×), and warns if the game's voice is nearly as loud as the claps. |
| Settings | `beatclap/settings.py` | Language, voice / music / metronome toggles, timing offset and clap threshold, saved as JSON when you quit or save a mic check. |
| Chart | `beatclap/core.py` `build_chart` | Each word gets one read bar, then one syllable per beat starting on the next downbeat, padded to whole bars, plus one extra bar with word cards on. |
| Stress | `words.STRESS`, `core.stress_verdict` | Primary stress per word, by dictionary pronunciation. Each clap's strength is its loudest block in the 30 ms after onset. A word passes if its stressed clap is at least 1.4× the median of its unstressed claps. Comparing within a word means mic gain and distance don't matter. One-syllable words and keyboard claps aren't judged. |
| Word cards | `beatclap/wordinfo.py`, `beatclap/pictures.py` | Meanings and examples for every word in English and Japanese. Pictures are drawn from shape lists in code, so there are still no image files. |
| Judging | `judge`, `Session` | Each syllable matched by a clap scores **1 point**. The flash shows timing: ±75 ms is **PERFECT**, ±150 ms is **GOOD**. A missed syllable or a clap outside every window resets the combo. |
| UI / i18n | `beatclap/game.py`, `beatclap/i18n.py` | Keyboard, mouse and touch all work. Press **L** anywhere to switch English / 日本語. Word prompts always stay English. A Japanese system font is picked automatically (Noto CJK, IPA, Hiragino, Yu Gothic, Meiryo, Android's system fonts, ...); when a CJK font has no Latin letters, English runs in a line are drawn with the Latin font. |

## Controls

Menu: `UP`/`DOWN` select, `LEFT`/`RIGHT` change the stage or clap threshold, `ENTER` confirm.
The mouse or touch works everywhere too: click or tap menu items (the `<` / `>` ends
change a value) and the on-screen buttons. On Android, Back acts as `ESC`.
In play: `SPACE` clap (keyboard) · `[` / `]` mic latency offset ±5 ms · `M` metronome
click · `L` language · `ESC` menu

**Tip:** Headphones work best, since the mic then hears only your claps. On
speakers, keep the volume moderate so your claps are clearly louder than the
voice and music. Run the Mic check to see if they are. The metronome click
is off by default for the same reason. If your judgements are consistently
"late", the mic check fixes the offset, or adjust it in play with `[` / `]`.

## Credits

The voice was generated with [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M)
(Apache-2.0) via [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx).

## Tests

```bash
python -m unittest
```

The tests cover timing and scoring, syllable stress, word cards, the clap detector (including a full mic
pipeline test with music and the game's voice leaking in), the music loops (none
of them may trigger the detector), the voice bundle, settings, and headless UI
tests that draw every screen with and without a mic, in both languages and in
Android layout, and drive the touch controls.

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
| 5 | Neon Finale | 4–5 syllables | A minor synthwave: saw lead, pad, arpeggios | Everything (shapes, metronome click, fonts) is generated in code
or comes from the system. There are no asset files.

## Run

```bash
pip install -r requirements.txt     # pygame, numpy, sounddevice (or pyaudio)
python -m beatclap                  # --lang ja, --words 15, --device N
python -m beatclap --list-devices
```

If neither `sounddevice` nor `pyaudio` can open a mic, the game falls back to
**SPACE** as the clap key.

The voice uses whatever speech engine the system has, synthesized in memory at
runtime: `espeak-ng` / `espeak` on Linux (`sudo apt install espeak-ng`), `say`
on macOS, or `pip install pyttsx3` on Windows. If none is found, the game runs
silently.

## Debian package

```bash
./packaging/build-deb.sh                      # -> dist/beat-clap_0.1.0_all.deb
sudo apt install ./dist/beat-clap_0.1.0_all.deb
beat-clap
```

The maintainer field comes from your git identity; override it with
`DEBFULLNAME` / `DEBEMAIL`, and the version with `VERSION=0.2.0`.

## Windows .exe

```bash
./packaging/build-exe.sh        # Linux: builds dist/BeatClap.exe under Wine
```

The first run sets up a separate Wine prefix in `build/wine` with Windows Python
3.11 and the pinned dependencies (it needs network access). Later runs reuse it.
On Windows itself, install the same packages and run `py packaging\build_exe.py`.

The exe is a single 33 MB file with Python and all libraries bundled. It uses the
Windows voice (SAPI) for speech and Japanese fonts that come with Windows (Yu
Gothic, Meiryo, MS Gothic).

## How it works

| Piece | Where | Details |
|---|---|---|
| Audio capture | `beatclap/audio.py` `MicListener` | 256-sample blocks at 48 kHz (~5 ms) go into a 1 s ring buffer. RMS is computed per block. Timestamps come from the ADC clock, mapped to `perf_counter`. |
| Clap detector | `ClapDetector` | Fires when `rms > ambient_floor * 2.5`, then blocks for **150 ms**. The level must also fall back below threshold before the next clap, so one sustained noise counts once. The floor adapts only on quiet blocks. |
| Voice | `beatclap/voice.py`, `words.SPOKEN` | The word is spoken on beat 1 of its read bar. Each syllable is spoken so its vowel onset (where the loudness first reaches half its peak) lands on the node. Syllables use respellings (`U-NI-VER-SI-TY` is spoken as `you-nih-ver-sih-tee`) so TTS doesn't read letter names. |
| Self-trigger guard | `ClapDetector.measure_voice` / `guard_voice` | While the word preview plays, the detector records how loud the game's voice is at the mic (no claps register then). While a syllable plays, a clap must be 1.5× louder than that, so speaker output can't score points by itself. |
| Music | `beatclap/music.py`, `beatclap/stages.py` | Each song is an 8-bar loop at exactly 100 BPM, synthesized with numpy when the stage starts. Sample 0 is beat 0, so the music stays locked to the rail. It plays on its own mixer channel and peaks at about a third of the voice's level. |
| Music vs. the mic | `music.tame_transients`, `ClapDetector.rewarm` | Hits whose 5 ms RMS rises more than 1.6× above the loop's running average get softened, so drums can never reach the detector's 2.5× threshold. When a stage starts, the detector re-learns the background level with the music playing. If the room stays louder for 0.3 s or more (a fan, for example), the floor follows it instead of getting stuck. |
| Chart | `beatclap/core.py` `build_chart` | Each word gets one read bar, then one syllable per beat starting on the next downbeat, padded to whole bars. |
| Judging | `judge`, `Session` | Each syllable matched by a clap scores **1 point**. The flash shows timing: ±75 ms is **PERFECT**, ±150 ms is **GOOD**. A missed syllable or a clap outside every window resets the combo. |
| UI / i18n | `beatclap/game.py`, `beatclap/i18n.py` | Press **L** anywhere to switch English / 日本語. Word prompts always stay English. A Japanese system font is picked automatically (Noto CJK, IPA, Hiragino, Yu Gothic, Meiryo, ...). |

## Controls

Menu: `UP`/`DOWN` select, `LEFT`/`RIGHT` choose stage, `ENTER` confirm.
In play: `SPACE` clap (keyboard) · `[` / `]` mic latency offset ±5 ms · `M` metronome
click · `L` language · `ESC` menu

**Tip:** Headphones work best, since the mic then hears only your claps. On
speakers, keep the volume moderate so your claps are clearly louder than the
voice and music. The metronome click is off by default for the same reason. If your judgements
are consistently "late", lower the mic offset with `[`.

## Tests

```bash
python -m unittest
```

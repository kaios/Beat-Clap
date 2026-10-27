"""Stages: a word pool by syllable count plus a song for each. All run at 100 BPM."""
from dataclasses import dataclass

from .music import Song
from .words import WORDS

CLEAR_RATIO = 0.6   # fraction of syllables needed to clear a stage


@dataclass
class Stage:
    name: dict          # {"en": ..., "ja": ...}
    syllables: tuple    # inclusive (min, max) syllables per word
    song: Song

    def pool(self):
        lo, hi = self.syllables
        return [w for w in WORDS if lo <= len(w.split("-")) <= hi]


STAGES = [
    Stage({"en": "Sunny Start", "ja": "サニー・スタート"}, (1, 2), Song(
        root=72, scale="major", chords=[0, 4, 5, 3],          # C  G  Am  F
        melody="5 . 5 6 5 - 3 .  2 . 2 3 2 - 7, .  1 . 1 2 3 - 5 .  6 - 5 - 4 - 3 . "
               "1' . 7 . 6 . 5 .  5 . 4 . 3 . 2 .  3 . 5 . 6 5 3 1  2 - - - 1 - . .",
        lead="pluck",
        bass="R.....R...R.F...", bass_voice="sub",
        comps=[("keys", "....x-......x-..", "chord")],
        kick="x.......x.x.....", snare="....o.......o...", hat="o.o.o.o.o.o.o.o.",
    )),
    Stage({"en": "Bubble Pop", "ja": "バブル・ポップ"}, (2, 3), Song(
        root=65, scale="major", chords=[5, 3, 0, 4],          # Dm  Bb  F  C
        melody="3 . 3 4 3 . 1 .  4 . 4 5 4 . 2 .  5 . 5 6 5 . 3 .  2 . 3 . 5 - - . "
               "6 . 6 . 5 3 1 .  4 . 4 . 3 2 1 .  1 3 5 1' 5 3 1 .  2 - 3 - 2 - . .",
        lead="square",
        bass="R.R.R.R.R.R.R.O.", bass_voice="square_bass",
        comps=[("chip", "xxxxxxxxxxxxxxxx", "arp")],
        kick="x...x...x...x...", snare="....x.......x...", hat="..x...x...x...x.",
    )),
    Stage({"en": "Midnight Funk", "ja": "ミッドナイト・ファンク"}, (3, 3), Song(
        root=64, scale="dorian", chords=[0, 3, 0, 3], sevenths=True,   # Em7  A7
        melody="1' . 7 5 . . 7 1'  - . 5 4 3 . 1 .  1 . 3 . 4 5 . 7  - . 5 . 4 - 3 . "
               "5 . 5 7 1' . 7 5  6 . 6 5 4 . 3 .  1 3 4 5 7 5 4 3  4 - - - . . . .",
        lead="organ",
        bass="R..R..O.R.F.R..O", bass_voice="slap",
        comps=[("clav", "..x..x.x..x..x..", "chord")],
        kick="x..x....x.x.....", snare="....x.......x..o", hat="xoxoxoxoxoxoxoxo",
    )),
    Stage({"en": "Island Breeze", "ja": "アイランド・ブリーズ"}, (3, 4), Song(
        root=67, scale="major", chords=[0, 5, 3, 4],          # G  Em  C  D
        melody="1' . 5 . 3 . 5 1'  7 . 5 . 3 . 5 7  6 . 4 . 1 . 4 6  5 - 7 - 2' - . . "
               "3' . 2' 1' . 5 . 3  5 . . 3 5 6 5 .  4 . 6 . 1' . 6 4  5 - 4 - 2 - . .",
        lead="marimba",
        bass="R...R..FR...O...", bass_voice="sub",
        comps=[("organ", "..x...x...x...x.", "chord")],
        kick="x.......x.......", snare="....o.......o...", hat="o.o.o.o.o.o.o.o.",
    )),
    Stage({"en": "Neon Finale", "ja": "ネオン・フィナーレ"}, (4, 5), Song(
        root=69, scale="minor", chords=[0, 5, 2, 6],          # Am  F  C  G
        melody="1' . 1' 7 1' . 5 .  6 . 6 5 6 . 3 .  5 . 5 4 5 . 1' .  7 - 2' - 7 - 5 . "
               "3' . 2' 1' 7 . 1' .  6 . 5 6 1' . 6 .  5 . 3 5 1' 2' 3' .  2' - - - 7 - . .",
        lead="saw",
        bass="R.R.R.R.R.R.R.R.", bass_voice="saw_bass",
        comps=[("pad", "x---------------", "chord"), ("pluck", "x.x.x.x.x.x.x.x.", "arp")],
        kick="x...x...x...x...", snare="....x.......x...", hat="..x...x...x...x.",
    )),
]

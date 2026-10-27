"""Pure game logic: timing windows, chart layout, scoring. No pygame/audio imports."""
import math
from dataclasses import dataclass, field

BPM = 100
BEAT_MS = 60000.0 / BPM          # 600 ms per beat
BEATS_PER_BAR = 4

PERFECT_MS = 75.0
GOOD_MS = 150.0
POINTS_PER_SYLLABLE = 1   # PERFECT and GOOD both score; the label is timing feedback

PERFECT = "PERFECT"
GOOD = "GOOD"
MISS = "MISS"


def judge(dt_ms):
    """Classify a clap offset (clap time - target time) into PERFECT / GOOD / None."""
    a = abs(dt_ms)
    if a <= PERFECT_MS:
        return PERFECT
    if a <= GOOD_MS:
        return GOOD
    return None


@dataclass
class Target:
    time_ms: float
    syllable: str
    seg_index: int
    syl_index: int
    result: str = None       # PERFECT / GOOD / MISS once judged
    hit_dt: float = None     # clap offset in ms for PERFECT / GOOD
    judged_at: float = None  # song time at which the judgement happened


@dataclass
class Segment:
    word: str
    syllables: list
    start_ms: float
    end_ms: float
    targets: list = field(default_factory=list)


def build_chart(words, start_ms=BEAT_MS * BEATS_PER_BAR):
    """Lay words out on the 100 BPM grid.

    Each word gets one "read" bar (metronome only), then one syllable per beat
    starting on the downbeat of the next bar, padded to whole bars.
    """
    segments = []
    t = start_ms
    for i, word in enumerate(words):
        syllables = word.split("-")
        bars = math.ceil(len(syllables) / BEATS_PER_BAR)
        targets = [
            Target(t + (BEATS_PER_BAR + j) * BEAT_MS, s, i, j)
            for j, s in enumerate(syllables)
        ]
        end = t + (BEATS_PER_BAR + bars * BEATS_PER_BAR) * BEAT_MS
        segments.append(Segment(word, syllables, t, end, targets))
        t = end
    return segments


class Scorer:
    def __init__(self):
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.counts = {PERFECT: 0, GOOD: 0, MISS: 0}

    def hit(self, result):
        points = POINTS_PER_SYLLABLE
        self.score += points
        self.combo += 1
        self.max_combo = max(self.max_combo, self.combo)
        self.counts[result] += 1
        return points

    def miss(self, counted=True):
        self.combo = 0
        if counted:
            self.counts[MISS] += 1


class Session:
    """Owns a chart and turns clap timestamps into judgements."""

    def __init__(self, segments):
        self.segments = segments
        self.targets = [t for s in segments for t in s.targets]
        self.scorer = Scorer()
        self._pending_from = 0  # index of the earliest possibly-unjudged target

    @property
    def end_ms(self):
        return self.segments[-1].end_ms if self.segments else 0.0

    def segment_at(self, now_ms):
        for s in self.segments:
            if now_ms < s.end_ms:
                return s
        return self.segments[-1] if self.segments else None

    def handle_clap(self, clap_ms):
        """Returns (result, dt_ms, target). result is MISS with target None for stray claps."""
        best, best_dt = None, None
        for tgt in self.targets[self._pending_from:]:
            if tgt.time_ms - clap_ms > GOOD_MS:
                break
            if tgt.result is not None:
                continue
            dt = clap_ms - tgt.time_ms
            if abs(dt) <= GOOD_MS and (best is None or abs(dt) < abs(best_dt)):
                best, best_dt = tgt, dt
        if best is None:
            # Clap outside every window: combo breaks, but it's not a missed syllable.
            self.scorer.miss(counted=False)
            return MISS, None, None
        best.result = judge(best_dt)
        best.hit_dt = best_dt
        best.judged_at = clap_ms
        self.scorer.hit(best.result)
        self._advance()
        return best.result, best_dt, best

    def update(self, now_ms):
        """Mark targets whose GOOD window has fully passed as missed. Returns them."""
        missed = []
        for tgt in self.targets[self._pending_from:]:
            if now_ms - tgt.time_ms <= GOOD_MS:
                break
            if tgt.result is None:
                tgt.result = MISS
                tgt.judged_at = now_ms
                self.scorer.miss()
                missed.append(tgt)
        self._advance()
        return missed

    def _advance(self):
        while (self._pending_from < len(self.targets)
               and self.targets[self._pending_from].result is not None):
            self._pending_from += 1

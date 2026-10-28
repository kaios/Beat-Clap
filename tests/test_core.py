import unittest

import numpy as np

from beatclap import core, music, voice
from beatclap.audio import ClapDetector, hf_rms
from beatclap.stages import STAGES
from beatclap.words import WORDS, spoken_syllables

BLOCK = 0.005  # 5 ms audio blocks


def warm(det, level=0.01):
    t = 0.0
    while not det.ready:
        det.process(level, t, BLOCK)
        t += BLOCK
    return t


class JudgeTest(unittest.TestCase):
    def test_windows(self):
        self.assertEqual(core.judge(0), core.PERFECT)
        self.assertEqual(core.judge(-75), core.PERFECT)
        self.assertEqual(core.judge(75.1), core.GOOD)
        self.assertEqual(core.judge(-150), core.GOOD)
        self.assertIsNone(core.judge(150.1))


class ChartTest(unittest.TestCase):
    def test_syllables_on_beats(self):
        segs = core.build_chart(["RO-BOT", "U-NI-VER-SI-TY"], start_ms=0)
        robot, uni = segs
        self.assertEqual([t.syllable for t in robot.targets], ["RO", "BOT"])
        self.assertEqual([t.time_ms for t in robot.targets], [2400, 3000])
        self.assertEqual(robot.end_ms, 8 * core.BEAT_MS)
        # 5 syllables need two bars after the read bar
        self.assertEqual(uni.end_ms - uni.start_ms, 12 * core.BEAT_MS)
        self.assertEqual(uni.targets[0].time_ms, robot.end_ms + 4 * core.BEAT_MS)


class SessionTest(unittest.TestCase):
    def setUp(self):
        self.s = core.Session(core.build_chart(["RO-BOT"], start_ms=0))

    def test_perfect_and_good_scoring(self):
        r, dt, _ = self.s.handle_clap(2400 + 30)
        self.assertEqual((r, dt), (core.PERFECT, 30))
        r, _, _ = self.s.handle_clap(3000 - 120)
        self.assertEqual(r, core.GOOD)
        self.assertEqual(self.s.scorer.score, 2)  # 1 point per syllable
        self.assertEqual(self.s.scorer.combo, 2)

    def test_stray_clap_resets_combo(self):
        self.s.handle_clap(2400)
        r, _, tgt = self.s.handle_clap(2700)
        self.assertEqual(r, core.MISS)
        self.assertIsNone(tgt)
        self.assertEqual(self.s.scorer.combo, 0)
        self.assertEqual(self.s.scorer.counts[core.MISS], 0)

    def test_target_judged_once(self):
        self.s.handle_clap(2400)
        r, _, _ = self.s.handle_clap(2450)
        self.assertEqual(r, core.MISS)

    def test_auto_miss_after_window(self):
        self.assertEqual(self.s.update(2400 + 150), [])
        missed = self.s.update(2400 + 151)
        self.assertEqual([t.syllable for t in missed], ["RO"])
        self.assertEqual(self.s.scorer.counts[core.MISS], 1)

    def test_one_point_per_syllable_regardless_of_combo(self):
        sc = core.Scorer()
        for _ in range(20):
            self.assertEqual(sc.hit(core.PERFECT), 1)
        self.assertEqual(sc.hit(core.GOOD), 1)
        self.assertEqual((sc.score, sc.combo), (21, 21))
        sc.miss()
        self.assertEqual((sc.score, sc.combo), (21, 0))


class DetectorTest(unittest.TestCase):
    def test_no_trigger_during_warmup(self):
        det = ClapDetector()
        self.assertFalse(det.process(1.0, 0.0, BLOCK))

    def test_spike_threshold(self):
        det = ClapDetector()
        t = warm(det)
        self.assertFalse(det.process(0.024, t, BLOCK))    # 2.4x floor
        self.assertTrue(det.process(0.026, t + BLOCK, BLOCK))  # 2.6x floor

    def test_cooldown_blocks_echo(self):
        det = ClapDetector()
        t = warm(det)
        self.assertTrue(det.process(0.5, t, BLOCK))
        det.process(0.01, t + 0.05, BLOCK)                 # dips, re-arms
        self.assertFalse(det.process(0.5, t + 0.10, BLOCK))  # echo inside 150 ms
        det.process(0.01, t + 0.14, BLOCK)
        self.assertTrue(det.process(0.5, t + 0.16, BLOCK))

    def test_sustained_noise_fires_once(self):
        det = ClapDetector()
        t = warm(det)
        fired = sum(det.process(0.5, t + i * BLOCK, BLOCK) for i in range(200))
        self.assertEqual(fired, 1)

    def test_floor_ignores_claps_and_tracks_room(self):
        det = ClapDetector()
        t = warm(det, 0.01)
        det.process(0.9, t, BLOCK)
        self.assertAlmostEqual(det.floor, 0.01)
        for i in range(1, 1000):
            det.process(0.02, t + i * BLOCK, BLOCK)
        self.assertAlmostEqual(det.floor, 0.02, places=3)

    def test_voice_preview_measured_without_triggering(self):
        det = ClapDetector()
        t = warm(det)
        det.measure_voice(t, t + 0.5)
        fired = [det.process(0.2, t + i * BLOCK, BLOCK) for i in range(100)]
        self.assertFalse(any(fired))
        det.process(0.01, t + 0.6, BLOCK)
        self.assertEqual(list(det.voice_peaks), [0.2])
        self.assertAlmostEqual(det.voice_threshold, 0.24)

    def test_guard_rejects_own_voice_but_accepts_loud_clap(self):
        det = ClapDetector()
        t = warm(det)
        det.measure_voice(t, t + 0.1)
        det.process(0.2, t, BLOCK)
        det.process(0.01, t + 0.2, BLOCK)
        det.guard_voice(t + 1.0, t + 1.5)
        self.assertFalse(det.process(0.22, t + 1.1, BLOCK))   # leaked speech
        self.assertAlmostEqual(det.floor, 0.01)                # and floor untouched
        det.process(0.01, t + 1.2, BLOCK)
        self.assertTrue(det.process(0.4, t + 1.3, BLOCK))     # real clap over it
        det.process(0.01, t + 1.6, BLOCK)
        self.assertTrue(det.process(0.22, t + 1.7, BLOCK))    # same level, no guard

    def test_clapped_over_preview_is_discarded(self):
        det = ClapDetector()
        t = warm(det)
        for i, peak in enumerate((0.2, 0.9)):
            start = t + i
            det.measure_voice(start, start + 0.1)
            det.process(peak, start, BLOCK)
            det.process(0.01, start + 0.2, BLOCK)
        self.assertAlmostEqual(det.voice_threshold, 0.24)

    def test_recovers_when_room_gets_permanently_louder(self):
        det = ClapDetector()
        t = warm(det, 0.01)
        fired = [det.process(0.1, t + i * BLOCK, BLOCK) for i in range(600)]  # 3 s of fan noise
        self.assertEqual(sum(fired), 1)                    # only the onset looked like a clap
        self.assertGreater(det.floor, 0.08)                # floor followed the new ambience
        t += 600 * BLOCK
        self.assertTrue(det.process(0.5, t, BLOCK))        # claps work again over the noise

    def test_rewarm_relearns_floor_without_triggering(self):
        det = ClapDetector()
        t = warm(det, 0.01)
        det.rewarm(0.5)
        fired = [det.process(0.1, t + i * BLOCK, BLOCK) for i in range(100)]
        self.assertFalse(any(fired))
        self.assertAlmostEqual(det.floor, 0.1)


class MicPipelineTest(unittest.TestCase):
    """End to end through MicListener's ingest path: speakers playing music and the game's
    voice into the mic, with claps no louder (full-band) than the voice itself."""

    SR = 48000

    def synth_clap(self, rng):
        n = int(self.SR * 0.06)
        noise = rng.normal(0, 1, n)
        band = np.convolve(noise, np.ones(3) / 3, "same") - np.convolve(noise, np.ones(40) / 40, "same")
        return band * np.exp(-np.arange(n) / self.SR / 0.008)

    def test_claps_heard_over_music_and_voice_but_voice_alone_is_not(self):
        from beatclap.audio import MicListener, rms as full_rms
        sr, rng = self.SR, np.random.default_rng(3)
        bank = np.load(voice.BUNDLE)
        def clip(key):
            x = bank[key].astype(np.float32) / 32768
            return np.interp(np.linspace(0, len(x) - 1, len(x) * 2), np.arange(len(x)), x)  # 24k -> 48k
        def peak(x):
            return max(full_rms(x[i:i + 256]) for i in range(0, len(x) - 256, 256))

        y = rng.normal(0, 0.002, sr * 6)                               # room
        loop = music.render(STAGES[0].song, sr)
        y += np.tile(loop, 2)[: len(y)] * 0.15                         # background music
        word, syl1, syl2 = clip("w:RO-BOT"), clip("s:RO-BOT:0"), clip("s:RO-BOT:1")
        gain = 0.3 / np.abs(syl1).max()
        events = [(1.0, word), (3.0, syl1), (3.6, syl2)]
        for t, x in events:
            y[int(t * sr): int(t * sr) + len(x)] += x * gain
        voice_peak = peak(syl1 * gain)
        claps = [3.03, 4.2]                                            # on a syllable, and alone
        for t in claps:
            c = self.synth_clap(rng)
            c *= voice_peak / peak(c)                                  # only as loud as the voice
            y[int(t * sr): int(t * sr) + len(c)] += c

        mic = MicListener()
        mic.detector.rewarm(1.0)
        mic.detector.measure_voice(1.0, 1.0 + len(word) / sr + 0.08)
        heard = []
        for i in range(0, len(y) - 256, 256):
            t = i / sr
            for start, x in events[1:]:
                if abs(t - start) < 0.003:
                    mic.detector.guard_voice(start, start + len(x) / sr + 0.08)
            mic._ingest(y[i:i + 256].astype(np.float32), t)
            while not mic.claps.empty():
                heard.append(mic.claps.get())
        self.assertEqual(len(heard), len(claps), heard)
        for got, want in zip(heard, claps):
            self.assertLess(abs(got - want), 0.01)


class MusicTest(unittest.TestCase):
    SR = 22050

    @classmethod
    def setUpClass(cls):
        cls.loops = [music.render(st.song, cls.SR) for st in STAGES]

    def test_loop_is_exactly_eight_bars_at_100_bpm(self):
        for x in self.loops:
            self.assertEqual(len(x), round(8 * 4 * 0.6 * self.SR))

    def test_songs_are_distinct_and_quieter_than_voice(self):
        for i, x in enumerate(self.loops):
            self.assertLessEqual(float(np.max(np.abs(x))), music.PEAK + 1e-6)
            for y in self.loops[i + 1:]:
                self.assertLess(abs(np.corrcoef(x, y)[0, 1]), 0.5)

    def test_music_never_looks_like_a_clap(self):
        block = 128
        for st, x in zip(STAGES, self.loops):
            for level in (0.05, 1.0):
                det = ClapDetector()
                y = np.tile(x, 2) * level
                fired = sum(det.process(hf_rms(y[i:i + block], y[i - 1] if i else 0.0),
                                        i / self.SR, block / self.SR)
                            for i in range(0, len(y) - block, block))
                self.assertEqual(fired, 0, st.name["en"])

    def test_melodies_cover_eight_bars(self):
        for st in STAGES:
            self.assertEqual(len(st.song.melody.split()), 8 * 8, st.name["en"])


class StageTest(unittest.TestCase):
    def test_pools_match_syllable_ranges_and_get_harder(self):
        prev_hi = 0
        for st in STAGES:
            lo, hi = st.syllables
            self.assertGreaterEqual(len(st.pool()), 8, st.name["en"])
            for w in st.pool():
                self.assertTrue(lo <= len(w.split("-")) <= hi)
            self.assertGreaterEqual(hi, prev_hi)
            prev_hi = hi
            self.assertTrue(st.name["en"] and st.name["ja"])


class VoiceTest(unittest.TestCase):
    def test_prepare_trims_caps_and_finds_onset(self):
        sr = 1000
        silence = np.zeros(200, np.float32)
        consonant = np.full(100, 0.05, np.float32)
        vowel = np.full(900, 0.5, np.float32)
        x, onset = voice.prepare(np.concatenate([silence, consonant, vowel]), sr, sr,
                                 max_ms=520)
        self.assertEqual(len(x), 520)                  # leading silence trimmed, capped
        self.assertTrue(95 <= onset <= 105)            # onset at the vowel, not the consonant
        self.assertAlmostEqual(float(np.max(np.abs(x))), 0.8, places=3)
        self.assertEqual(x[-1], 0.0)                   # faded out

    def test_prepare_resamples(self):
        x, _ = voice.prepare(np.ones(100, np.float32), 1000, 2000)
        self.assertEqual(len(x), 200)

    def test_every_word_has_matching_spoken_syllables(self):
        for w in WORDS:
            self.assertEqual(len(spoken_syllables(w)), len(w.split("-")), w)


if __name__ == "__main__":
    unittest.main()

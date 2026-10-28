"""Headless UI tests: draw every screen, with and without a microphone, in both languages."""
import os
import tempfile
import time
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from beatclap import core, game, settings  # noqa: E402


class UITest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._path = settings.path
        settings.path = lambda: os.path.join(self.tmp.name, "settings.json")
        self.g = game.Game(num_words=2)

    def tearDown(self):
        self.g.mic.stop()
        settings.path = self._path
        self.tmp.cleanup()

    def draw(self):
        self.g.screen.fill(game.BG)
        getattr(self.g, f"draw_{self.g.state}")()

    def fake_mic(self):
        self.g.mic.backend, self.g.mic.device_name = "fake", "Test microphone"

    def test_every_screen_draws_with_and_without_mic(self):
        g = self.g
        for has_mic in (False, True):
            if has_mic:
                self.fake_mic()
            for lang in ("en", "ja"):
                g.lang = lang
                g.state = "menu"
                for g.menu_index in range(len(game.MENU)):
                    self.draw()
                g.start_session()
                self.draw()
                g.t0 -= (g.session.end_ms + 1000) / 1000
                g.update_play()
                self.assertEqual(g.state, "results")
                self.draw()
                g.start_calibration()
                self.draw()
                g.cal["result"] = {"heard": 2}
                self.draw()
                g.cal["result"] = {"heard": 8, "room": 6.0, "offset": 40, "threshold": 2.5,
                                   "voice_loud": True}
                self.draw()

    def test_threshold_menu_adjusts_and_clamps(self):
        import pygame
        g = self.g
        g.menu_index = game.MENU.index("threshold")
        left = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT)
        for _ in range(30):
            g.handle_event(left)
        self.assertEqual(g.mic.detector.ratio, game.THRESHOLD_MIN)
        g.menu_select()  # ENTER resets to the default
        self.assertEqual(g.mic.detector.ratio, settings.DEFAULTS["threshold"])

    def test_mic_check_measures_offset_and_loudness(self):
        g = self.g
        self.fake_mic()
        g.start_calibration()
        det, t0 = g.mic.detector, g.t0
        det.floor = 0.01
        g.mic.history.clear()
        # room noise every 5 ms, plus a clap 40 ms after each clap beat, 8x the floor
        end = (game.CAL_CLAP_FROM + game.CAL_CLAPS + 1) * core.BEAT_MS
        for ms in range(0, int(end), 5):
            g.mic.history.append((t0 + ms / 1000, 0.01))
        for k in range(game.CAL_CLAP_FROM, game.CAL_CLAP_FROM + game.CAL_CLAPS):
            g.mic.history.append((t0 + (k * core.BEAT_MS + 40) / 1000, 0.08))
        r = g.measure_calibration()
        self.assertEqual(r["heard"], 8)
        self.assertEqual(r["offset"], 40)
        self.assertAlmostEqual(r["room"], 8.0)
        self.assertEqual(r["threshold"], 2.5)   # loud claps keep the default
        # quiet claps (3x the floor) get a more sensitive threshold
        for i, (t, lvl) in enumerate(g.mic.history):
            if lvl == 0.08:
                g.mic.history[i] = (t, 0.03)
        self.assertEqual(g.measure_calibration()["threshold"], 1.5)

    def test_settings_round_trip(self):
        g = self.g
        g.lang, g.offset_ms, g.mic.detector.ratio = "ja", 35, 1.8
        g.save_settings()
        loaded = settings.load()
        self.assertEqual((loaded["lang"], loaded["offset_ms"], loaded["threshold"]), ("ja", 35, 1.8))

    def test_settings_ignore_bad_values(self):
        path = settings.path()
        with open(path, "w") as f:
            f.write('{"lang": "xx", "offset_ms": true, "threshold": "loud", "voice_on": 0}')
        self.assertEqual(settings.load(), settings.DEFAULTS)


if __name__ == "__main__":
    unittest.main()

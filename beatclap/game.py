"""Pygame front end: menu, stages, scrolling 100 BPM rail, music, judgement flashes, results."""
import math
import random
import time

import numpy as np
import pygame

from . import core, i18n, music
from .audio import MicListener
from .stages import CLEAR_RATIO, STAGES
from .voice import Voice
from .words import spoken_syllables

W, H = 1280, 720
HIT_X = 260
RAIL_Y = 440
PX_PER_MS = 0.32            # 192 px per beat
NODE_R = 26
FLASH_MS = 550
AUDIO_GRACE_MS = 60
OUTPUT_LATENCY_MS = 20      # mixer output latency: sounds start this early to be heard on time
VOICE_GUARD_MARGIN_MS = 80  # extra time either side of a clip for speaker-to-mic delay
MUSIC_VOLUME = 0.5          # music peaks at 0.25 after this, well under the voice's 0.8
MUSIC_REWARM_S = 1.0        # let the clap detector re-learn the room once music starts
MENU = ("start", "stage", "language", "voice", "music", "metronome", "quit")

BG = (14, 17, 30)
RAIL = (60, 68, 98)
DIM = (110, 118, 150)
TEXT = (230, 234, 245)
CYAN = (80, 220, 255)
GOLD = (255, 205, 70)
GREEN = (110, 230, 140)
RED = (255, 90, 100)
WINDOW_GOOD = (40, 70, 60)
WINDOW_PERFECT = (60, 105, 80)

RESULT_COLOR = {core.PERFECT: GOLD, core.GOOD: GREEN, core.MISS: RED}
FLASH_TEXT = {core.PERFECT: "PERFECT!", core.GOOD: "GOOD", core.MISS: "MISS"}


def ms_to_x(t_ms, now_ms):
    return HIT_X + (t_ms - now_ms) * PX_PER_MS


class Fonts:
    def __init__(self):
        self.ja_path = i18n.find_japanese_font()
        self._cache = {}

    def get(self, size, lang="en"):
        key = (size, lang)
        if key not in self._cache:
            if lang == "ja" and self.ja_path:
                self._cache[key] = pygame.font.Font(self.ja_path, size)
            else:
                # pygame's built-in font renders small for its nominal size
                self._cache[key] = pygame.font.Font(None, int(size * 1.35))
        return self._cache[key]

    def render(self, size, text, color, lang="en"):
        """Render text; in Japanese mode ASCII runs use the Latin font, since many
        CJK system fonts (e.g. Droid Sans Fallback) ship without Latin glyphs."""
        if lang != "ja" or not self.ja_path:
            return self.get(size).render(text, True, color)
        runs = []
        for ch in text:
            font = self.get(size, "en" if ch.isascii() else "ja")
            if runs and runs[-1][0] is font:
                runs[-1][1].append(ch)
            else:
                runs.append((font, [ch]))
        parts = [(f, f.render("".join(chars), True, color)) for f, chars in runs]
        ascent = max(f.get_ascent() for f, _ in parts)
        height = max(ascent - f.get_ascent() + s.get_height() for f, s in parts)
        out = pygame.Surface((sum(s.get_width() for _, s in parts), height), pygame.SRCALPHA)
        x = 0
        for f, s in parts:
            out.blit(s, (x, ascent - f.get_ascent()))
            x += s.get_width()
        return out


def make_click(freq, ms=30, volume=0.5):
    """Synthesize a short decaying sine click matching the mixer format."""
    rate, _, channels = pygame.mixer.get_init()
    n = int(rate * ms / 1000)
    t = np.arange(n) / rate
    wave = np.sin(2 * np.pi * freq * t) * np.exp(-t * 180) * volume
    samples = (wave * 32767).astype(np.int16)
    if channels > 1:
        samples = np.repeat(samples[:, None], channels, axis=1)
    return pygame.sndarray.make_sound(np.ascontiguousarray(samples))


class Flash:
    def __init__(self, text, color, born, sub=""):
        self.text, self.color, self.born, self.sub = text, color, born, sub


class Game:
    def __init__(self, device=None, lang="en", num_words=8):
        pygame.mixer.pre_init(44100, -16, 2, 256)
        pygame.init()
        pygame.display.set_caption("Beat Clap")
        self.screen = pygame.display.set_mode((W, H))
        self.clock = pygame.time.Clock()
        self.fonts = Fonts()
        self.lang = lang
        self.num_words = num_words
        self.state = "menu"
        self.menu_index = 0
        self.metronome = False
        self.voice_on = True
        self.music_on = True
        self.stage_index = 0
        self.cleared = False
        self.offset_ms = 0
        self.last_clap_wall = -10.0
        self.session = None

        self.clicks = None
        self.music_channel = None
        self._music_cache = {}
        if pygame.mixer.get_init():
            self.clicks = (make_click(1760), make_click(1175, volume=0.35))
            pygame.mixer.set_reserved(1)  # channel 0 is the music's alone
            self.music_channel = pygame.mixer.Channel(0)
            self.music_channel.set_volume(MUSIC_VOLUME)
        self.voice = Voice()

        self.mic = MicListener(device=device)
        self.mic.start()

    # ---------- helpers ----------

    def tr(self, key, **kw):
        s = i18n.STRINGS[self.lang][key]
        return s.format(**kw) if kw else s

    def ui_text(self, size, text, color):
        return self.fonts.render(size, text, color, self.lang)

    def en_font(self, size):
        return self.fonts.get(size, "en")

    def blit_center(self, surf, cx, cy):
        self.screen.blit(surf, surf.get_rect(center=(int(cx), int(cy))))

    def now_ms(self):
        return (time.perf_counter() - self.t0) * 1000.0

    def drain_mic(self):
        claps = []
        while True:
            try:
                claps.append(self.mic.claps.get_nowait())
            except Exception:
                return claps

    # ---------- main loop ----------

    def run(self):
        try:
            while self.state != "quit":
                for event in pygame.event.get():
                    self.handle_event(event)
                getattr(self, f"update_{self.state}", lambda: None)()
                if self.state == "quit":
                    break
                self.screen.fill(BG)
                getattr(self, f"draw_{self.state}")()
                pygame.display.flip()
                self.clock.tick(144)
        finally:
            self.mic.stop()
            pygame.quit()

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.state = "quit"
            return
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_l:
            self.lang = "ja" if self.lang == "en" else "en"
            return
        if self.state == "menu":
            if event.key in (pygame.K_UP, pygame.K_w):
                self.menu_index = (self.menu_index - 1) % len(MENU)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.menu_index = (self.menu_index + 1) % len(MENU)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.menu_select()
            elif event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_a, pygame.K_d):
                step = 1 if event.key in (pygame.K_RIGHT, pygame.K_d) else -1
                self.stage_index = (self.stage_index + step) % len(STAGES)
            elif event.key == pygame.K_SPACE:
                self.last_clap_wall = time.perf_counter()
            elif event.key == pygame.K_ESCAPE:
                self.state = "quit"
        elif self.state == "play":
            if event.key == pygame.K_ESCAPE:
                self.stop_music()
                self.state = "menu"
            elif event.key == pygame.K_SPACE:
                self.on_clap(self.now_ms())
            elif event.key == pygame.K_m:
                self.metronome = not self.metronome
            elif event.key == pygame.K_LEFTBRACKET:
                self.offset_ms -= 5
            elif event.key == pygame.K_RIGHTBRACKET:
                self.offset_ms += 5
        elif self.state == "results":
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.cleared:
                    self.stage_index = (self.stage_index + 1) % len(STAGES)
                self.start_session()
            elif event.key == pygame.K_r:
                self.start_session()
            elif event.key == pygame.K_ESCAPE:
                self.state = "menu"

    def menu_select(self):
        item = MENU[self.menu_index]
        if item == "start":
            self.start_session()
        elif item == "stage":
            self.stage_index = (self.stage_index + 1) % len(STAGES)
        elif item == "language":
            self.lang = "ja" if self.lang == "en" else "en"
        elif item == "voice":
            self.voice_on = not self.voice_on
        elif item == "music":
            self.music_on = not self.music_on
        elif item == "metronome":
            self.metronome = not self.metronome
        else:
            self.state = "quit"

    # ---------- session ----------

    @property
    def stage(self):
        return STAGES[self.stage_index]

    def stage_label(self):
        return self.tr("stage", n=self.stage_index + 1, name=self.stage.name[self.lang])

    def start_session(self):
        pool = self.stage.pool()
        words = random.sample(pool, min(self.num_words, len(pool)))
        self.session = core.Session(core.build_chart(words))
        self.screen.fill(BG)
        self.blit_center(self.ui_text(36, self.stage_label(), CYAN), W / 2, H / 2 - 30)
        self.blit_center(self.ui_text(24, self.tr("loading"), DIM), W / 2, H / 2 + 20)
        pygame.display.flip()
        self.cues = self.build_voice_cues() if self.voice_on and self.voice.available else []
        song = self.stage_music() if self.music_on and self.music_channel else None
        self.cue_index = 0
        self.flashes = []
        self.last_beat = -1
        self.beat_pulse_at = -1e9
        self.cleared = False
        self.drain_mic()
        if song:
            # Sample 0 of the loop is beat 0; it's heard OUTPUT_LATENCY_MS after play().
            self.music_channel.play(song, loops=-1)
            self.mic.detector.rewarm(MUSIC_REWARM_S)
        self.t0 = time.perf_counter() + OUTPUT_LATENCY_MS / 1000.0
        self.state = "play"

    def stage_music(self):
        if self.stage_index not in self._music_cache:
            rate, _, channels = pygame.mixer.get_init()
            pcm = (music.render(self.stage.song, rate) * 32767).astype(np.int16)
            if channels > 1:
                pcm = np.repeat(pcm[:, None], channels, axis=1)
            self._music_cache[self.stage_index] = pygame.sndarray.make_sound(
                np.ascontiguousarray(pcm))
        return self._music_cache[self.stage_index]

    def stop_music(self, fade_ms=300):
        if self.music_channel:
            self.music_channel.fadeout(fade_ms)

    def build_voice_cues(self):
        """The whole word is spoken on the first beat of its read bar, then each
        syllable is spoken so its vowel onset lands exactly on its node."""
        cues = []
        for seg in self.session.segments:
            word = self.voice.clip(seg.word.replace("-", "").lower(), syllable=False)
            if word:
                cues.append((seg.start_ms - word.onset_ms - OUTPUT_LATENCY_MS, word, True))
            for tgt, text in zip(seg.targets, spoken_syllables(seg.word)):
                clip = self.voice.clip(text)
                if clip:
                    cues.append((tgt.time_ms - clip.onset_ms - OUTPUT_LATENCY_MS, clip, False))
        cues.sort(key=lambda c: c[0])
        return cues

    def play_due_cues(self, now):
        while self.cue_index < len(self.cues) and self.cues[self.cue_index][0] <= now:
            at_ms, clip, is_preview = self.cues[self.cue_index]
            self.cue_index += 1
            if now - at_ms > 100:  # skip speech that's already late (e.g. after a frame hitch)
                continue
            clip.sound.play()
            start = self.t0 + at_ms / 1000.0
            end = start + (clip.length_ms + VOICE_GUARD_MARGIN_MS) / 1000.0
            if is_preview:
                self.mic.detector.measure_voice(start, end)
            else:
                self.mic.detector.guard_voice(start, end)

    def on_clap(self, clap_ms):
        self.last_clap_wall = time.perf_counter()
        result, dt, _ = self.session.handle_clap(clap_ms)
        sub = ""
        if dt is not None and abs(dt) >= 1:
            sub = self.tr("late" if dt > 0 else "early", ms=int(round(abs(dt))))
        self.flashes.append(Flash(FLASH_TEXT[result], RESULT_COLOR[result], self.now_ms(), sub))

    def update_menu(self):
        if self.drain_mic():
            self.last_clap_wall = time.perf_counter()

    def update_play(self):
        for clap_wall in self.drain_mic():
            clap_ms = (clap_wall - self.t0) * 1000.0 - self.offset_ms
            # The lead-in has nothing to hit, and it's where the music's onset could
            # slip past the detector before it re-learns the room; don't count it.
            if clap_ms >= self.session.segments[0].start_ms:
                self.on_clap(clap_ms)

        now = self.now_ms()
        self.play_due_cues(now)
        # Mic claps are timestamped at the ADC but delivered a block or two later,
        # so give late-window claps time to arrive before calling a miss.
        for _ in self.session.update(now - AUDIO_GRACE_MS):
            self.flashes.append(Flash("MISS", RED, now))

        beat = int(now // core.BEAT_MS)
        if beat > self.last_beat:
            self.last_beat = beat
            self.beat_pulse_at = beat * core.BEAT_MS
            if self.metronome and self.clicks:
                self.clicks[0 if beat % core.BEATS_PER_BAR == 0 else 1].play()

        self.flashes = [f for f in self.flashes if now - f.born < FLASH_MS]
        if now > self.session.end_ms + core.BEAT_MS:
            total = len(self.session.targets)
            self.cleared = self.session.scorer.score >= math.ceil(total * CLEAR_RATIO)
            self.stop_music(1500)
            self.state = "results"

    # ---------- drawing ----------

    def draw_mic_meter(self, x, y, w=240, h=14, centered=False):
        det = self.mic.detector
        if self.mic.backend is None:
            surf = self.ui_text(20, self.tr("no_mic"), DIM)
            anchor = {"midtop": (x + w // 2, y)} if centered else {"topright": (x + w, y)}
            self.screen.blit(surf, surf.get_rect(**anchor))
            return

        def to_px(level):  # -60 dBFS .. 0 dBFS
            db = 20 * math.log10(max(level, 1e-6))
            return int(w * min(1.0, max(0.0, (db + 60) / 60)))

        pygame.draw.rect(self.screen, (35, 40, 60), (x, y, w, h), border_radius=4)
        hot = det.level > det.threshold
        pygame.draw.rect(self.screen, GOLD if hot else CYAN, (x, y, to_px(det.level), h),
                         border_radius=4)
        tx = x + to_px(det.threshold)
        pygame.draw.line(self.screen, RED, (tx, y - 4), (tx, y + h + 4), 2)
        fx = x + to_px(det.floor)
        pygame.draw.line(self.screen, DIM, (fx, y), (fx, y + h), 1)
        name = self.mic.device_name[:28]
        label = self.ui_text(16, self.tr("mic", name=name, backend=self.mic.backend),
                                        True, DIM)
        self.screen.blit(label, (x, y + h + 6))
        age = time.perf_counter() - self.last_clap_wall
        if age < 0.3:
            r = int(10 + age * 60)
            pygame.draw.circle(self.screen, GOLD, (x - 22, y + h // 2), r, 2)

    def draw_menu(self):
        self.blit_center(self.ui_text(84, self.tr("title"), CYAN), W / 2, 105)
        self.blit_center(self.ui_text(26, self.tr("subtitle"), DIM), W / 2, 172)
        if self.lang == "ja" and not self.fonts.ja_path:
            self.blit_center(self.en_font(20).render(self.tr("no_ja_font"), True, RED), W / 2, 205)

        items = [
            self.tr("start"),
            f"<  {self.stage_label()}  >",
            self.tr("language"),
            self.tr("voice", state=self.tr("on" if self.voice_on else "off"))
            if self.voice.available else self.tr("no_voice"),
            self.tr("music", state=self.tr("on" if self.music_on else "off")),
            self.tr("metronome", state=self.tr("on" if self.metronome else "off")),
            self.tr("quit"),
        ]
        for i, label in enumerate(items):
            sel = i == self.menu_index
            surf = self.ui_text(32, label, GOLD if sel else TEXT)
            cy = 250 + i * 46
            self.blit_center(surf, W / 2, cy)
            if sel:
                r = surf.get_rect(center=(W // 2, cy))
                pygame.draw.circle(self.screen, GOLD, (r.left - 26, cy), 8)

        self.draw_mic_meter(W // 2 - 120, 600, centered=True)
        test = "clap_detected" if time.perf_counter() - self.last_clap_wall < 0.6 else "clap_test"
        self.blit_center(self.ui_text(20, self.tr(test), DIM), W / 2, 575)
        self.blit_center(self.ui_text(18, self.tr("menu_hint"), DIM), W / 2, H - 24)

    def draw_rail(self, now):
        # timing windows around the hit line
        good_w = core.GOOD_MS * PX_PER_MS
        perf_w = core.PERFECT_MS * PX_PER_MS
        pygame.draw.rect(self.screen, WINDOW_GOOD,
                         (HIT_X - good_w, RAIL_Y - 46, 2 * good_w, 92), border_radius=10)
        pygame.draw.rect(self.screen, WINDOW_PERFECT,
                         (HIT_X - perf_w, RAIL_Y - 46, 2 * perf_w, 92), border_radius=10)
        pygame.draw.line(self.screen, RAIL, (0, RAIL_Y), (W, RAIL_Y), 3)

        # beat grid
        first = math.floor((now - HIT_X / PX_PER_MS) / core.BEAT_MS)
        last = math.ceil((now + (W - HIT_X) / PX_PER_MS) / core.BEAT_MS)
        for b in range(max(0, first), last + 1):
            x = ms_to_x(b * core.BEAT_MS, now)
            if b % core.BEATS_PER_BAR == 0:
                pygame.draw.line(self.screen, RAIL, (x, RAIL_Y - 30), (x, RAIL_Y + 30), 1)
                pygame.draw.circle(self.screen, DIM, (x, RAIL_Y), 6)
            else:
                pygame.draw.circle(self.screen, RAIL, (x, RAIL_Y), 4)

        # hit ring pulses on every beat
        pulse = max(0.0, 1 - (now - self.beat_pulse_at) / 250)
        pygame.draw.circle(self.screen, TEXT, (HIT_X, RAIL_Y), NODE_R + 6 + int(8 * pulse), 2)

        label_font = self.en_font(26)
        word_font = self.en_font(30)
        for seg in self.session.segments:
            if not seg.targets:
                continue
            x0 = ms_to_x(seg.targets[0].time_ms, now)
            x1 = ms_to_x(seg.targets[-1].time_ms, now)
            if x1 < -NODE_R * 3 or x0 > W + NODE_R * 3:
                continue
            pygame.draw.line(self.screen, (40, 90, 120), (x0, RAIL_Y), (x1, RAIL_Y), 8)
            self.screen.blit(word_font.render(seg.word, True, DIM), (x0 - NODE_R, RAIL_Y - 100))
            for tgt in seg.targets:
                self.draw_node(tgt, now, label_font)

    def draw_node(self, tgt, now, font):
        x = ms_to_x(tgt.time_ms, now)
        if tgt.result in (core.PERFECT, core.GOOD):
            age = now - tgt.judged_at
            if age < 300:  # burst ring at the hit line
                r = int(NODE_R + age * 0.12)
                pygame.draw.circle(self.screen, RESULT_COLOR[tgt.result], (HIT_X, RAIL_Y), r, 3)
            color = RESULT_COLOR[tgt.result]
            pygame.draw.circle(self.screen, color, (x, RAIL_Y), 8)
        elif tgt.result == core.MISS:
            pygame.draw.circle(self.screen, (90, 40, 50), (x, RAIL_Y), NODE_R, 2)
            d = NODE_R // 2
            pygame.draw.line(self.screen, RED, (x - d, RAIL_Y - d), (x + d, RAIL_Y + d), 2)
            pygame.draw.line(self.screen, RED, (x - d, RAIL_Y + d), (x + d, RAIL_Y - d), 2)
            color = (120, 60, 70)
        else:
            pygame.draw.circle(self.screen, CYAN, (x, RAIL_Y), NODE_R)
            pygame.draw.circle(self.screen, TEXT, (x, RAIL_Y), NODE_R, 2)
            color = TEXT
        self.blit_center(font.render(tgt.syllable, True, color), x, RAIL_Y + NODE_R + 24)

    def draw_word_prompt(self, now):
        seg = self.session.segment_at(now)
        if seg is None:
            return
        font = self.en_font(92)
        pieces = []
        for i, tgt in enumerate(seg.targets):
            if i:
                pieces.append(font.render("-", True, DIM))
            pieces.append(font.render(tgt.syllable, True, RESULT_COLOR.get(tgt.result, TEXT)))
        total = sum(p.get_width() for p in pieces)
        x = (W - total) / 2
        for p in pieces:
            self.screen.blit(p, (x, 150))
            x += p.get_width()
        reading = seg.targets and now < seg.targets[0].time_ms - core.BEAT_MS * 2
        hint = self.tr("listen" if reading else "go")
        self.blit_center(self.ui_text(26, hint, DIM), W / 2, 265)

    def draw_hud(self):
        sc = self.session.scorer
        big = self.en_font(40)
        self.screen.blit(self.ui_text(20, self.tr("score"), DIM), (24, 18))
        self.screen.blit(big.render(f"{sc.score:,}", True, TEXT), (24, 40))
        self.screen.blit(self.ui_text(20, self.tr("combo"), DIM), (230, 18))
        self.screen.blit(big.render(str(sc.combo), True, TEXT), (230, 40))
        self.blit_center(self.ui_text(22, self.stage_label(), DIM), W / 2, 34)
        self.draw_mic_meter(W - 280, 26)
        if self.mic.backend:
            off = self.ui_text(16, self.tr("offset", ms=self.offset_ms), DIM)
            self.screen.blit(off, (W - 280, 70))
        self.blit_center(self.ui_text(18, self.tr("play_hint"), DIM), W / 2, H - 24)

    def draw_flashes(self, now):
        for f in self.flashes[-3:]:
            age = (now - f.born) / FLASH_MS
            scale = 1.0 + 0.25 * max(0.0, 1 - age * 4)
            surf = self.en_font(int(54 * scale)).render(f.text, True, f.color)
            surf.set_alpha(int(255 * (1 - age)))
            self.blit_center(surf, HIT_X, RAIL_Y - 150 - age * 30)
            if f.sub:
                sub = self.ui_text(20, f.sub, f.color)
                sub.set_alpha(int(255 * (1 - age)))
                self.blit_center(sub, HIT_X, RAIL_Y + 110)

    def draw_play(self):
        now = self.now_ms()
        self.draw_word_prompt(now)
        self.draw_rail(now)
        self.draw_flashes(now)
        self.draw_hud()

    def draw_results(self):
        sc = self.session.scorer
        total = len(self.session.targets) or 1
        accuracy = (sc.counts[core.PERFECT] + 0.5 * sc.counts[core.GOOD]) / total * 100
        if not self.cleared:
            title, color, hint = "try_again", RED, "hint_retry"
        elif self.stage_index == len(STAGES) - 1:
            title, color, hint = "all_clear", GOLD, "hint_done"
        else:
            title, color, hint = "stage_clear", GREEN, "hint_next"
        self.blit_center(self.ui_text(64, self.tr(title), color), W / 2, 90)
        self.blit_center(self.ui_text(24, self.stage_label(), DIM), W / 2, 145)
        need = math.ceil(len(self.session.targets) * CLEAR_RATIO)
        self.blit_center(self.ui_text(20, self.tr("clear_need", need=need, total=len(self.session.targets)),
                                      DIM), W / 2, 178)
        rows = [
            (self.tr("final_score"), f"{sc.score} / {len(self.session.targets)}", TEXT),
            (self.tr("perfect"), str(sc.counts[core.PERFECT]), GOLD),
            (self.tr("good"), str(sc.counts[core.GOOD]), GREEN),
            (self.tr("miss"), str(sc.counts[core.MISS]), RED),
            (self.tr("max_combo"), str(sc.max_combo), TEXT),
            (self.tr("accuracy"), f"{accuracy:.1f}%", TEXT),
        ]
        for i, (label, value, color) in enumerate(rows):
            y = 240 + i * 56
            l = self.ui_text(34, label, DIM)
            self.screen.blit(l, l.get_rect(midright=(W // 2 - 30, y)))
            v = self.en_font(40).render(value, True, color)
            self.screen.blit(v, v.get_rect(midleft=(W // 2 + 30, y)))
        self.blit_center(self.ui_text(22, self.tr(hint), DIM), W / 2, H - 50)

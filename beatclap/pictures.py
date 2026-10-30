"""A small picture for every word, drawn in code on a 120x120 canvas.

Each picture is a list of shapes: ("c", color, x, y, r) circle, ("e", color, x, y, rx, ry)
ellipse, ("r", color, x, y, w, h) rectangle, ("p", color, points) polygon,
("l", color, x1, y1, x2, y2, width) line, ("a", color, x, y, r, start_deg, end_deg, width) arc,
("t", color, text, x, y, size) centred text.
"""
import math

import pygame

INK = (40, 44, 60)
WHITE = (245, 245, 250)
RED = (225, 70, 70)
ORANGE = (240, 150, 60)
YELLOW = (250, 215, 80)
GREEN = (90, 190, 100)
DARK_GREEN = (50, 130, 75)
BLUE = (80, 160, 240)
SKY = (150, 210, 245)
PURPLE = (150, 110, 215)
PINK = (240, 150, 170)
BROWN = (145, 95, 60)
TAN = (215, 170, 120)
GRAY = (150, 155, 170)
DARK = (80, 85, 105)

EYES = [("c", INK, 50, 50, 4), ("c", INK, 70, 50, 4)]

PICTURES = {
    "CAT": [("p", ORANGE, [(32, 42), (38, 14), (54, 32)]), ("p", ORANGE, [(88, 42), (82, 14), (66, 32)]),
            ("c", ORANGE, 60, 60, 34), ("c", INK, 47, 54, 4), ("c", INK, 73, 54, 4),
            ("p", PINK, [(55, 64), (65, 64), (60, 70)]),
            ("l", INK, 30, 64, 46, 68, 2), ("l", INK, 30, 76, 46, 72, 2),
            ("l", INK, 90, 64, 74, 68, 2), ("l", INK, 90, 76, 74, 72, 2)],
    "DOG": [("c", TAN, 60, 60, 32), ("e", BROWN, 26, 58, 12, 26), ("e", BROWN, 94, 58, 12, 26),
            ("c", INK, 48, 52, 4), ("c", INK, 72, 52, 4), ("e", WHITE, 60, 72, 15, 12),
            ("c", INK, 60, 66, 5), ("e", PINK, 60, 84, 7, 8)],
    "TRAIN": [("r", DARK, 12, 90, 96, 5), ("r", BLUE, 20, 34, 80, 50), ("r", WHITE, 20, 66, 80, 5),
              ("r", SKY, 30, 42, 18, 16), ("r", SKY, 52, 42, 18, 16), ("r", SKY, 74, 42, 18, 16),
              ("c", INK, 38, 88, 7), ("c", INK, 82, 88, 7)],
    "RO-BOT": [("l", GRAY, 60, 12, 60, 26, 3), ("c", RED, 60, 11, 5), ("r", GRAY, 30, 26, 60, 40),
               ("c", SKY, 46, 44, 8), ("c", SKY, 74, 44, 8), ("r", INK, 46, 56, 28, 4),
               ("r", DARK, 38, 70, 44, 34), ("r", GRAY, 22, 72, 12, 26), ("r", GRAY, 86, 72, 12, 26),
               ("c", YELLOW, 60, 86, 6)],
    "HAP-PY": [("c", YELLOW, 60, 60, 44), ("c", INK, 44, 48, 6), ("c", INK, 76, 48, 6),
               ("a", INK, 60, 62, 28, 20, 160, 5)],
    "WA-TER": [("p", BLUE, [(60, 12), (88, 58), (92, 74), (84, 92), (60, 104), (36, 92), (28, 74), (32, 58)]),
               ("a", WHITE, 60, 72, 20, 110, 180, 4)],
    "MU-SIC": [("e", PURPLE, 38, 90, 14, 10), ("e", PURPLE, 84, 78, 14, 10), ("r", PURPLE, 46, 28, 6, 62),
               ("r", PURPLE, 92, 16, 6, 62), ("p", PURPLE, [(46, 28), (98, 16), (98, 32), (46, 44)])],
    "PEN-CIL": [("p", YELLOW, [(84, 14), (106, 36), (46, 96), (24, 74)]),
                ("p", TAN, [(24, 74), (46, 96), (16, 104)]), ("p", INK, [(22, 92), (28, 98), (16, 104)]),
                ("p", PINK, [(84, 14), (106, 36), (112, 30), (90, 8)])],
    "RAIN-BOW": [("a", RED, 60, 86, 50, 180, 360, 7), ("a", ORANGE, 60, 86, 43, 180, 360, 7),
                 ("a", YELLOW, 60, 86, 36, 180, 360, 7), ("a", GREEN, 60, 86, 29, 180, 360, 7),
                 ("a", BLUE, 60, 86, 22, 180, 360, 7), ("c", WHITE, 14, 88, 11), ("c", WHITE, 28, 92, 9),
                 ("c", WHITE, 106, 88, 11), ("c", WHITE, 92, 92, 9)],
    "MON-KEY": [("c", BROWN, 24, 52, 13), ("c", BROWN, 96, 52, 13), ("c", TAN, 24, 52, 7), ("c", TAN, 96, 52, 7),
                ("c", BROWN, 60, 56, 34), ("e", TAN, 60, 66, 25, 21), ("c", INK, 50, 50, 4), ("c", INK, 70, 50, 4),
                ("a", INK, 60, 62, 13, 20, 160, 3)],
    "TEA-CHER": [("r", DARK_GREEN, 12, 14, 96, 56), ("t", WHITE, "ABC", 60, 42, 26), ("c", TAN, 34, 80, 12),
                 ("r", PURPLE, 20, 92, 28, 26), ("l", TAN, 46, 98, 72, 62, 5)],
    "WIN-DOW": [("r", SKY, 24, 16, 72, 88), ("c", YELLOW, 78, 34, 9), ("r", WHITE, 57, 16, 6, 88),
                ("r", WHITE, 24, 56, 72, 6), ("r", BROWN, 16, 10, 88, 6), ("r", BROWN, 16, 104, 88, 7),
                ("r", BROWN, 18, 10, 6, 96), ("r", BROWN, 96, 10, 6, 96)],
    "GAR-DEN": [("r", GREEN, 0, 84, 120, 36), ("r", DARK_GREEN, 28, 52, 4, 40), ("r", DARK_GREEN, 58, 40, 4, 52),
                ("r", DARK_GREEN, 88, 52, 4, 40),
                *[("c", col, x + dx, y + dy, 8) for x, y, col in ((30, 46, PINK), (60, 32, YELLOW), (90, 46, PURPLE))
                  for dx, dy in ((-7, 0), (7, 0), (0, -7), (0, 7))],
                ("c", ORANGE, 30, 46, 5), ("c", ORANGE, 60, 32, 5), ("c", ORANGE, 90, 46, 5)],
    "COF-FEE": [("a", WHITE, 88, 70, 15, 270, 450, 6), ("r", WHITE, 28, 46, 60, 52), ("e", BROWN, 58, 48, 30, 7),
                ("r", GRAY, 22, 100, 72, 5), ("a", GRAY, 48, 28, 8, 90, 270, 3), ("a", GRAY, 68, 28, 8, 90, 270, 3)],
    "BA-NA-NA": [("p", YELLOW, [(22, 24), (34, 22), (42, 54), (66, 78), (100, 82), (106, 90), (70, 102),
                                (36, 84), (20, 50)]),
                 ("p", BROWN, [(20, 20), (32, 16), (34, 24), (24, 27)]), ("c", BROWN, 104, 87, 3)],
    "COM-PU-TER": [("r", DARK, 16, 18, 88, 62), ("r", SKY, 23, 25, 74, 48), ("r", GRAY, 52, 80, 16, 12),
                   ("r", GRAY, 34, 92, 52, 6), ("l", BLUE, 32, 38, 66, 38, 4), ("l", GREEN, 32, 50, 84, 50, 4),
                   ("l", PURPLE, 32, 62, 58, 62, 4)],
    "E-LE-PHANT": [("e", DARK, 22, 50, 20, 26), ("e", DARK, 98, 50, 20, 26), ("c", GRAY, 60, 48, 30),
                   ("p", GRAY, [(50, 62), (70, 62), (68, 100), (78, 108), (70, 114), (54, 104)]),
                   ("c", INK, 48, 44, 4), ("c", INK, 72, 44, 4)],
    "TO-MA-TO": [("c", RED, 60, 66, 40), ("p", GREEN, [(60, 34), (40, 24), (52, 36), (34, 42), (56, 42), (60, 54),
                                                     (64, 42), (86, 42), (68, 36), (80, 24)]),
                 ("a", WHITE, 60, 66, 30, 120, 170, 4)],
    "HAM-BUR-GER": [("e", ORANGE, 60, 38, 44, 24), ("r", ORANGE, 16, 38, 88, 8), ("r", GREEN, 12, 50, 96, 7),
                    ("r", RED, 16, 57, 88, 5), ("r", BROWN, 16, 62, 88, 12), ("r", YELLOW, 16, 74, 88, 4),
                    ("r", ORANGE, 16, 78, 88, 14), ("c", WHITE, 44, 28, 2), ("c", WHITE, 62, 22, 2), ("c", WHITE, 78, 30, 2)],
    "PI-AN-O": [("r", INK, 8, 24, 104, 22), ("r", WHITE, 8, 46, 104, 56),
                *[("l", GRAY, x, 46, x, 102, 2) for x in range(23, 112, 15)],
                *[("r", INK, x, 46, 9, 32) for x in (18, 33, 63, 78, 93)]],
    "KAN-GA-ROO": [("e", TAN, 54, 74, 22, 30), ("c", TAN, 72, 34, 15), ("p", TAN, [(64, 26), (66, 6), (74, 22)]),
                   ("p", TAN, [(76, 22), (84, 6), (84, 26)]), ("c", INK, 76, 32, 3),
                   ("p", TAN, [(38, 86), (8, 60), (12, 56), (46, 76)]), ("r", TAN, 50, 98, 34, 9),
                   ("l", TAN, 72, 56, 88, 66, 5), ("a", BROWN, 62, 78, 13, 20, 160, 3)],
    "OC-TO-PUS": [*[("l", PURPLE, 60, 62, x, 106, 8) for x in (12, 28, 44, 60, 76, 92, 108)],
                  ("l", PURPLE, 60, 62, 4, 86, 8), ("c", PURPLE, 60, 44, 32), ("c", WHITE, 48, 42, 8), ("c", WHITE, 72, 42, 8),
                  ("c", INK, 48, 43, 4), ("c", INK, 72, 43, 4)],
    "BEAU-TI-FUL": [("r", DARK_GREEN, 57, 66, 6, 46), ("e", GREEN, 42, 92, 16, 7),
                    *[("c", PINK, 60 + 24 * math.cos(a * math.pi / 3), 44 + 24 * math.sin(a * math.pi / 3), 15)
                      for a in range(6)],
                    ("c", YELLOW, 60, 44, 14)],
    "DI-NO-SAUR": [("p", GREEN, [(4, 90), (34, 62), (60, 58), (72, 36), (70, 22), (98, 18), (110, 30), (88, 42),
                                 (84, 66), (72, 88), (72, 108), (60, 108), (56, 92), (44, 92), (44, 108),
                                 (32, 108), (30, 88)]),
                   ("c", INK, 88, 27, 3),
                   ("p", DARK_GREEN, [(36, 62), (42, 50), (50, 59)]), ("p", DARK_GREEN, [(52, 58), (60, 46), (64, 52)])],
    "TEL-E-PHONE": [("r", RED, 20, 62, 80, 42), ("p", RED, [(32, 62), (42, 42), (78, 42), (88, 62)]),
                    ("r", INK, 12, 22, 96, 12), ("r", INK, 12, 22, 22, 24), ("r", INK, 86, 22, 22, 24),
                    ("c", WHITE, 60, 80, 15), ("c", RED, 60, 80, 5)],
    "STRAW-BER-RY": [("p", RED, [(28, 40), (92, 40), (88, 72), (60, 110), (32, 72)]), ("c", RED, 44, 44, 18), ("c", RED, 76, 44, 18),
                     ("p", GREEN, [(60, 30), (34, 20), (46, 34), (28, 40), (92, 40), (74, 34), (86, 20)]),
                     *[("c", YELLOW, x, y, 2) for x, y in ((44, 56), (60, 54), (76, 56), (52, 72), (68, 72), (60, 88))]],
    "VI-O-LIN": [("l", BROWN, 76, 44, 104, 14, 8), ("l", INK, 104, 14, 112, 6, 7), ("e", ORANGE, 42, 86, 25, 21), ("e", ORANGE, 62, 62, 18, 16),
                 ("l", INK, 44, 88, 88, 34, 2), ("l", GRAY, 8, 42, 86, 108, 3)],
    "A-MER-I-CA": [("r", WHITE, 12, 26, 96, 68), *[("r", RED, 12, y, 96, 7) for y in (26, 40, 54, 68, 82)],
                   ("r", BLUE, 12, 26, 44, 35), *[("c", WHITE, x, y, 2) for x in (21, 34, 47) for y in (35, 46, 55)]],
    "HEL-I-COP-TER": [("r", DARK, 18, 20, 84, 5), ("r", DARK, 56, 22, 8, 16), ("e", BLUE, 52, 60, 34, 24), ("c", SKY, 36, 56, 13),
                      ("p", BLUE, [(74, 52), (112, 48), (112, 56), (76, 72)]), ("r", DARK, 108, 38, 4, 28),
                      ("l", DARK, 36, 84, 34, 96, 3), ("l", DARK, 68, 84, 70, 96, 3), ("r", DARK, 22, 96, 62, 4)],
    "AV-O-CA-DO": [("p", DARK_GREEN, [(60, 10), (76, 22), (94, 62), (88, 92), (60, 108), (32, 92), (26, 62), (44, 22)]),
                   ("p", (205, 225, 130), [(60, 18), (72, 28), (86, 62), (82, 86), (60, 100), (38, 86), (34, 62), (48, 28)]),
                   ("c", BROWN, 60, 70, 17)],
    "CAL-CU-LA-TOR": [("r", DARK, 26, 8, 68, 104), ("r", (190, 225, 190), 34, 16, 52, 22), ("t", INK, "123", 62, 27, 18),
                      *[("r", WHITE if x < 70 else ORANGE, x, y, 12, 12) for x in (34, 54, 74) for y in (46, 64, 84)]],
    "VEG-E-TA-BLE": [("p", ORANGE, [(44, 42), (76, 42), (60, 114)]), ("p", GREEN, [(60, 44), (40, 14), (54, 24), (60, 6), (66, 24), (80, 14)]),
                     ("l", BROWN, 50, 58, 60, 58, 2), ("l", BROWN, 60, 72, 68, 72, 2), ("l", BROWN, 54, 86, 62, 86, 2)],
    "TEL-E-VI-SION": [("l", GRAY, 60, 28, 40, 8, 3), ("l", GRAY, 60, 28, 80, 8, 3), ("r", DARK, 12, 28, 96, 68), ("r", SKY, 20, 36, 66, 52),
                      ("c", RED, 97, 48, 4), ("c", GREEN, 97, 62, 4), ("r", DARK, 28, 96, 12, 8), ("r", DARK, 80, 96, 12, 8),
                      ("p", WHITE, [(45, 50), (45, 74), (66, 62)])],
    "WA-TER-MEL-ON": [("a", DARK_GREEN, 60, 42, 50, 0, 180, 9), ("p", RED, [(14, 44), (106, 44), (98, 70), (80, 84), (60, 88), (40, 84), (22, 70)]),
                      *[("e", INK, x, y, 3, 5) for x, y in ((38, 56), (60, 54), (82, 56), (50, 70), (70, 70))],
                      ("r", RED, 10, 40, 100, 5)],
    "IN-FOR-MA-TION": [("c", BLUE, 60, 60, 46), ("c", WHITE, 60, 34, 8), ("r", WHITE, 53, 50, 14, 42)],
    "U-NI-VER-SI-TY": [("p", INK, [(60, 18), (108, 44), (60, 68), (12, 44)]), ("p", DARK, [(32, 60), (88, 60), (88, 86), (60, 96), (32, 86)]),
                       ("p", INK, [(60, 18), (108, 44), (60, 68), (12, 44)]), ("l", YELLOW, 60, 44, 96, 58, 3), ("l", YELLOW, 96, 58, 96, 86, 3),
                       ("c", YELLOW, 96, 90, 5)],
    "DIC-TION-AR-Y": [("r", RED, 20, 12, 80, 96), ("r", WHITE, 26, 94, 74, 9), ("r", (170, 50, 50), 20, 12, 8, 96),
                      ("t", WHITE, "A-Z", 64, 46, 25), ("l", WHITE, 42, 68, 86, 68, 3)],
    "HIP-PO-POT-A-MUS": [("c", GRAY, 36, 24, 9), ("c", GRAY, 84, 24, 9), ("e", GRAY, 60, 46, 32, 26), ("e", DARK, 60, 78, 42, 28),
                         ("c", INK, 48, 40, 4), ("c", INK, 72, 40, 4), ("e", INK, 44, 70, 5, 4), ("e", INK, 76, 70, 5, 4),
                         ("r", WHITE, 46, 90, 8, 12), ("r", WHITE, 66, 90, 8, 12)],
    "CON-GRAT-U-LA-TIONS": [("p", ORANGE, [(10, 110), (36, 44), (76, 84)]),
                            *[("c", col, x, y, 5) for x, y, col in ((60, 24, RED), (92, 20, BLUE), (102, 54, YELLOW), (80, 42, GREEN), (40, 22, PURPLE), (106, 88, PINK))],
                            ("l", PINK, 68, 62, 90, 38, 3), ("l", SKY, 48, 42, 56, 12, 3), ("l", YELLOW, 76, 76, 110, 72, 3)],
    "AL-PHA-BET": [("r", RED, 8, 38, 34, 44), ("t", WHITE, "A", 25, 60, 32), ("r", BLUE, 43, 38, 34, 44), ("t", WHITE, "B", 60, 60, 32),
                   ("r", GREEN, 78, 38, 34, 44), ("t", WHITE, "C", 95, 60, 32)],
    "EN-VI-RON-MENT": [("c", BLUE, 60, 60, 46), ("p", GREEN, [(38, 24), (66, 20), (72, 40), (54, 56), (60, 76), (44, 86), (34, 58), (22, 48)]),
                       ("p", GREEN, [(82, 56), (100, 50), (102, 72), (84, 90), (74, 76)])],
}

_SUPERSAMPLE = 3


def _draw(surface, shape, s, font_for):
    kind, color, *a = shape
    if kind == "c":
        pygame.draw.circle(surface, color, (a[0] * s, a[1] * s), a[2] * s)
    elif kind == "e":
        pygame.draw.ellipse(surface, color, ((a[0] - a[2]) * s, (a[1] - a[3]) * s, 2 * a[2] * s, 2 * a[3] * s))
    elif kind == "r":
        pygame.draw.rect(surface, color, (a[0] * s, a[1] * s, a[2] * s, a[3] * s))
    elif kind == "p":
        pygame.draw.polygon(surface, color, [(x * s, y * s) for x, y in a[0]])
    elif kind == "l":
        pygame.draw.line(surface, color, (a[0] * s, a[1] * s), (a[2] * s, a[3] * s), max(1, a[4] * s))
    elif kind == "a":  # drawn as a thick polyline; angles are screen degrees, clockwise from +x
        x, y, r, start, end, width = a
        steps = max(4, int(abs(end - start) / 4))
        points = [((x + r * math.cos(math.radians(start + (end - start) * i / steps))) * s,
                   (y + r * math.sin(math.radians(start + (end - start) * i / steps))) * s)
                  for i in range(steps + 1)]
        pygame.draw.lines(surface, color, False, points, max(1, width * s))
    elif kind == "t":
        text = font_for(a[3] * s).render(a[0], True, color)
        surface.blit(text, text.get_rect(center=(a[1] * s, a[2] * s)))
    else:
        raise ValueError(kind)


def render(word, size):
    """The word's picture as a size x size surface with a light rounded card behind it."""
    s = _SUPERSAMPLE
    big = pygame.Surface((120 * s, 120 * s), pygame.SRCALPHA)
    pygame.draw.rect(big, (232, 236, 245), big.get_rect(), border_radius=14 * s)
    fonts = {}

    def font_for(px):
        return fonts.setdefault(px, pygame.font.Font(None, int(px * 1.35)))

    clip = pygame.Surface(big.get_size(), pygame.SRCALPHA)
    for shape in PICTURES.get(word, []):
        _draw(clip, shape, s, font_for)
    big.blit(clip, (0, 0))
    return pygame.transform.smoothscale(big, (size, size))

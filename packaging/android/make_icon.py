"""Draw the launcher icon and splash screen in code (the game ships no image files)."""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402

BG, RAIL, CYAN, GOLD = (14, 17, 30), (60, 68, 98), (80, 220, 255), (255, 205, 70)


def icon(size):
    s = pygame.Surface((size, size))
    s.fill(BG)
    u = size / 512
    y = int(300 * u)
    pygame.draw.line(s, RAIL, (0, y), (size, y), int(10 * u))
    for x, r, color in ((130, 46, GOLD), (256, 46, CYAN), (382, 46, CYAN)):
        pygame.draw.circle(s, color, (int(x * u), y), int(r * u))
    pygame.draw.circle(s, (230, 234, 245), (int(130 * u), y), int(66 * u), int(8 * u))
    # two "clap" arcs above the first node
    for k in (1, 2):
        rect = pygame.Rect(0, 0, int((120 + 70 * k) * u), int((120 + 70 * k) * u))
        rect.center = (int(130 * u), y)
        pygame.draw.arc(s, GOLD, rect, 0.9, 2.25, int(8 * u))
    return s


def main(out_dir):
    pygame.init()
    pygame.image.save(icon(512), os.path.join(out_dir, "icon.png"))
    splash = pygame.Surface((1280, 720))
    splash.fill(BG)
    big = icon(360)
    splash.blit(big, big.get_rect(center=(640, 360)))
    pygame.image.save(splash, os.path.join(out_dir, "presplash.png"))


if __name__ == "__main__":
    main(sys.argv[1])

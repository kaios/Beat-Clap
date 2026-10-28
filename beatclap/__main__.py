import argparse

from .audio import list_devices


def main():
    p = argparse.ArgumentParser(prog="beatclap", description="Clap the syllables of English words at 100 BPM.")
    p.add_argument("--device", type=int, default=None, help="input device index (see --list-devices)")
    p.add_argument("--list-devices", action="store_true", help="print audio devices and exit")
    p.add_argument("--lang", choices=("en", "ja"), default=None, help="UI language (default: last used)")
    p.add_argument("--words", type=int, default=8, help="words per stage")
    args = p.parse_args()

    if args.list_devices:
        print(list_devices())
        return

    from .game import Game
    Game(device=args.device, lang=args.lang, num_words=args.words).run()


if __name__ == "__main__":
    main()

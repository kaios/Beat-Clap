"""Pre-render the game's voice with Kokoro (https://huggingface.co/hexgrad/Kokoro-82M, Apache-2.0)
into beatclap/voice_clips.npz. Developer tool only: the game just loads the result.

    pip install kokoro-onnx==0.4.9
    # model files: https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0
    python tools/generate_voice.py --model kokoro-v1.0.onnx --voices voices-v1.0.bin \\
        [--espeak-data DIR]

--espeak-data: a real (not symlinked) copy of espeakng_loader's espeak-ng-data folder at
a path shorter than ~150 characters, if espeak-ng can't find its data in a deep venv.
"""
import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from beatclap.words import WORDS, spoken_syllables  # noqa: E402

# Respellings that espeak's phonemizer gets wrong in isolation, given as phonemes instead.
PHONEMES = {
    "myoo": "mjˈuː", "pyoo": "pjˈuː", "byoo": "bjˈuː", "kyuh": "kjˈʊ",
    "ih": "ˈɪ", "vej": "vˈɛdʒ",
}
COUNT = ["one", "two", "three", "four"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--voices", required=True)
    ap.add_argument("--espeak-data")
    ap.add_argument("--voice", default="af_heart")
    ap.add_argument("--out", default=os.path.join("beatclap", "voice_clips.npz"))
    args = ap.parse_args()

    from kokoro_onnx import EspeakConfig, Kokoro
    cfg = EspeakConfig(data_path=args.espeak_data) if args.espeak_data else None
    kokoro = Kokoro(args.model, args.voices, espeak_config=cfg)

    def say(text):
        # A closing period gives a clean, falling end; without it Kokoro sometimes trails
        # an extra vowel onto short words ("dog" came out as "doggy").
        if text in PHONEMES:
            x, sr = kokoro.create(PHONEMES[text] + ".", voice=args.voice, is_phonemes=True)
        else:
            x, sr = kokoro.create(text + ".", voice=args.voice)
        assert sr == 24000, sr
        return (np.clip(x, -1, 1) * 32767).astype(np.int16)

    clips = {}
    for n, word in enumerate(WORDS, 1):
        print(f"[{n}/{len(WORDS)}] {word}", flush=True)
        clips[f"w:{word}"] = say(word.replace("-", "").lower())
        for i, syl in enumerate(spoken_syllables(word)):
            clips[f"s:{word}:{i}"] = say(syl)
    for i, w in enumerate(COUNT, 1):
        clips[f"c:{i}"] = say(w)

    np.savez_compressed(args.out, sr=np.array(24000), voice=np.array(args.voice), **clips)
    print(f"wrote {len(clips)} clips to {args.out} ({os.path.getsize(args.out) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()

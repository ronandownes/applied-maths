#!/usr/bin/env python3
import subprocess
from pathlib import Path

BASE = Path(__file__).parent           # folder where this script lives
PAGES_DIR = BASE / "pages"             # input images
THUMBS_DIR = BASE / "thumbs"           # output thumbnails

SIZE = "300x300"                       # max width/height

# Which extensions to process
EXTS = [".webp"]

def run(cmd):
    print("Running:", " ".join(map(str, cmd)))
    subprocess.run(cmd, check=True)

def make_dirs():
    THUMBS_DIR.mkdir(exist_ok=True, parents=True)

def make_thumbs():
    make_dirs()
    if not PAGES_DIR.exists():
        print("No 'pages' folder found at", PAGES_DIR)
        return

    files = [f for f in PAGES_DIR.iterdir()
             if f.is_file() and f.suffix.lower() in EXTS]

    if not files:
        print("No images found in", PAGES_DIR)
        return

    for src in sorted(files):
        dst = THUMBS_DIR / src.name
        run([
            "magick",
            str(src),
            "-resize", SIZE,
            str(dst),
        ])

if __name__ == "__main__":
    print("Script folder:", BASE)
    print("Source (pages):", PAGES_DIR)
    print("Output (thumbs):", THUMBS_DIR)
    make_thumbs()
    print("Done.")


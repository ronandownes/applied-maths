#!/usr/bin/env python3
"""
build.py - Generate viewer.html for each book folder in ./books
Portable: no hardcoded drive paths. Root is auto-detected from this script location.
"""

import json
import re
from pathlib import Path
from typing import List, Optional

IMAGE_EXTS = {".webp", ".jpg", ".jpeg", ".png", ".gif"}


def find_site_root(start: Path) -> Path:
    """
    Walk upward from 'start' and find a repo/site root.

    Detection order:
      1) .git folder (best, real repo root)
      2) books folder (good for copied folders without git metadata)
    """
    for p in [start, *start.parents]:
        if (p / ".git").exists():
            return p
        if (p / "books").exists():
            return p
    raise RuntimeError("Could not find site root (no .git/ or books/ found).")


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = find_site_root(SCRIPT_DIR)

BOOKS_ROOT = ROOT / "books"
TEMPLATE_FILE = ROOT / "viewer-template.html"


def find_images(folder: Path) -> List[Path]:
    if not folder.exists():
        return []

    images = [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTS]

    def num_key(p: Path):
        m = re.search(r"(\d+)", p.name)
        return (int(m.group(1)), p.name.lower()) if m else (999999, p.name.lower())

    images.sort(key=num_key)
    return images


def find_pages_folder(book_dir: Path) -> Optional[Path]:
    # If images are directly in the book folder, use it.
    if find_images(book_dir):
        return book_dir

    # Otherwise look for the first subfolder (excluding thumbs-like folders) containing images.
    if not book_dir.exists():
        return None

    for sub in book_dir.iterdir():
        if sub.is_dir() and sub.name.lower() not in {"thumbs", "thumb", "thumbnails", "tn"}:
            if find_images(sub):
                return sub

    return None


def find_toc_file(book_dir: Path) -> Optional[Path]:
    txt_files = list(book_dir.glob("*.txt"))
    if not txt_files:
        return None

    # Prefer files containing 'toc' in the name, else take first .txt
    for f in txt_files:
        if "toc" in f.name.lower():
            return f
    return txt_files[0]


def parse_toc(toc_file: Optional[Path]):
    """
    Parse TOC file into chapters and sections.

    Format supported (pipe-delimited):
      OFFSET|2
      CHAPTER|2.1|Kinematics|start=1|end=12
      SECTION|2.1.1|SUVAT|start=1|end=4

    Returns: (toc_data, offset)
      toc_data = {"chapters":[{code,title,start,end,sections:[...]}]}
    """
    result = {"chapters": []}
    offset = 0

    if not toc_file or not toc_file.exists():
        return result, offset

    current_chapter = None

    for raw in toc_file.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        parts = [p.strip() for p in line.split("|") if p.strip() != ""]
        if not parts:
            continue

        kind = parts[0].upper()

        if kind == "OFFSET" and len(parts) >= 2:
            try:
                offset = int(parts[1])
            except ValueError:
                pass
            continue

        if kind == "CHAPTER" and len(parts) >= 3:
            kv = {}
            for p in parts[3:]:
                if "=" in p:
                    k, v = p.split("=", 1)
                    v = v.strip()
                    kv[k.strip()] = int(v) if v.isdigit() else v

            current_chapter = {
                "code": parts[1],
                "title": parts[2],
                "start": kv.get("start", 1),
                "end": kv.get("end", kv.get("start", 1)),
                "sections": [],
            }
            result["chapters"].append(current_chapter)
            continue

        if kind == "SECTION" and len(parts) >= 3 and current_chapter:
            kv = {}
            for p in parts[3:]:
                if "=" in p:
                    k, v = p.split("=", 1)
                    v = v.strip()
                    kv[k.strip()] = int(v) if v.isdigit() else v

            current_chapter["sections"].append(
                {
                    "code": parts[1],
                    "title": parts[2],
                    "start": kv.get("start", 1),
                    "end": kv.get("end", kv.get("start", 1)),
                }
            )

    return result, offset


def discover_books() -> List[Path]:
    if not BOOKS_ROOT.exists():
        return []

    # Only include dirs that contain images (directly or in a subfolder)
    books = []
    for d in BOOKS_ROOT.iterdir():
        if d.is_dir() and not d.name.startswith(".") and find_pages_folder(d):
            books.append(d)

    return sorted(books, key=lambda p: p.name.lower())


def build_viewer(book_dir: Path) -> bool:
    print(f"\nProcessing: {book_dir.name}")

    pages_folder = find_pages_folder(book_dir)
    if not pages_folder:
        print("  ✗ No pages folder found")
        return False

    images = find_images(pages_folder)
    if not images:
        print("  ✗ No images found")
        return False

    # If pages are in a subfolder, pass the folder name to the template; else empty string.
    img_base = "" if pages_folder == book_dir else pages_folder.name

    toc_data, page_offset = parse_toc(find_toc_file(book_dir))

    if not TEMPLATE_FILE.exists():
        print(f"  ✗ Template not found: {TEMPLATE_FILE}")
        return False

    template = TEMPLATE_FILE.read_text(encoding="utf-8", errors="replace")

    viewer_html = template.replace("__BOOK_NAME__", book_dir.name)
    viewer_html = viewer_html.replace("__IMG_BASE__", json.dumps(img_base))
    viewer_html = viewer_html.replace("__PAGES__", json.dumps([img.name for img in images]))
    viewer_html = viewer_html.replace("__TOC__", json.dumps(toc_data))
    viewer_html = viewer_html.replace("__PAGE_OFFSET__", str(page_offset))

    (book_dir / "viewer.html").write_text(viewer_html, encoding="utf-8")
    print(f"  ✓ {len(images)} pages, {len(toc_data['chapters'])} chapters, offset={page_offset}")
    return True


def main() -> int:
    print("=" * 58)
    print("APPLIED-MATHS BOOK VIEWER BUILDER")
    print(f"Root:  {ROOT}")
    print(f"Books: {BOOKS_ROOT}")
    print("=" * 58)

    books = discover_books()
    if not books:
        print("\n✗ No books found. Ensure you have: ./books/<BookName>/pages...")
        return 1

    print(f"\nFound {len(books)} books")
    success = 0
    for book in books:
        if build_viewer(book):
            success += 1

    print("\n" + "=" * 58)
    print(f"✓ Built {success}/{len(books)} viewers")
    print("=" * 58)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from pathlib import Path

def find_gallery_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / "gallery" / "books").exists():
            return p / "gallery"
    raise RuntimeError("Could not find gallery/books")

BASE = find_gallery_root(Path.cwd())
BOOKS = BASE / "books"
OUT = BASE / "index.html"

tiles = []

for book in sorted(BOOKS.iterdir()):
    if not book.is_dir():
        continue

    thumb = book / "thumbs" / "001.webp"
    viewer = book / "viewer.html"

    if thumb.exists() and viewer.exists():
        tiles.append(f"""
    <a href="books/{book.name}/viewer.html" class="tile">
      <img src="books/{book.name}/thumbs/001.webp" alt="">
    </a>
        """)

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  body {{
    margin: 0;
    padding: 40px;
    background: #f5f5f5;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 40px;
  }}

  .tile {{
    display: block;
    transition: transform 0.25s ease, box-shadow 0.25s ease;
  }}

  .tile:hover {{
    transform: scale(1.12);
    box-shadow: 0 18px 36px rgba(0,0,0,0.25);
  }}

  img {{
    width: 100%;
    height: auto;
    display: block;
  }}
</style>
</head>
<body>
{''.join(tiles)}
</body>
</html>
"""

OUT.write_text(html, encoding="utf-8")
print(f"✓ Built index with {len(tiles)} books → {OUT}")

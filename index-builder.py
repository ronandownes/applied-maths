#!/usr/bin/env python3
"""
index-builder.py
Builds ./index.html with:
  - branded header (logo mark + your name)
  - root-level HTML apps grouped by TOPIC (optional metadata)
  - book tiles discovered in ./books/<book>/viewer.html
Portable: root auto-detected.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


# ------------ Edit these ------------
SITE_TITLE = "Applied Maths"
SITE_OWNER = "Ronan Downes"
TAGLINE = "Interactive explorations, notes, and book viewers"
# ----------------------------------


def find_site_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / ".git").exists():
            return p
        if (p / "books").exists():
            return p
    raise RuntimeError("Could not find site root (no .git/ or books/ found).")


ROOT = find_site_root(Path(__file__).resolve().parent)
BOOKS_DIR = ROOT / "books"
OUT = ROOT / "index.html"

IGNORE_ROOT_HTML = {
    "index.html",
    "viewer-template.html",
}
IGNORE_PREFIXES = ("_", ".")
IMAGE_EXTS = (".webp", ".png", ".jpg", ".jpeg")


@dataclass
class AppLink:
    href: str
    title: str
    topic: str
    desc: str


@dataclass
class BookTile:
    viewer_href: str
    cover_src: str
    name: str


def extract_title(html_text: str) -> Optional[str]:
    m = re.search(r"<title>(.*?)</title>", html_text, flags=re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    return re.sub(r"\s+", " ", m.group(1)).strip() or None


def extract_meta_comment(html_text: str, key: str) -> Optional[str]:
    m = re.search(rf"<!--\s*{re.escape(key)}\s*:\s*(.*?)\s*-->", html_text, flags=re.IGNORECASE)
    return (m.group(1).strip() if m else None) or None


def label_from_filename(p: Path) -> str:
    stem = p.stem.replace("-", " ").replace("_", " ").strip()
    return stem.title() if stem else p.name


def collect_root_apps() -> Dict[str, List[AppLink]]:
    groups: Dict[str, List[AppLink]] = {}

    for f in sorted(ROOT.iterdir(), key=lambda p: p.name.lower()):
        if not f.is_file():
            continue
        if f.suffix.lower() != ".html":
            continue
        if f.name.lower() in IGNORE_ROOT_HTML:
            continue
        if f.name.startswith(IGNORE_PREFIXES):
            continue

        text = f.read_text(encoding="utf-8", errors="replace")

        topic = extract_meta_comment(text, "TOPIC") or "Unsorted"
        desc = extract_meta_comment(text, "DESC") or ""
        title = extract_title(text) or label_from_filename(f)

        groups.setdefault(topic, []).append(AppLink(href=f.name, title=title, topic=topic, desc=desc))

    for t in groups:
        groups[t].sort(key=lambda a: a.title.lower())

    # ordered topics, with Unsorted last
    ordered: Dict[str, List[AppLink]] = {}
    for t in sorted([k for k in groups.keys() if k.lower() != "unsorted"], key=str.lower):
        ordered[t] = groups[t]
    if "Unsorted" in groups:
        ordered["Unsorted"] = groups["Unsorted"]

    return ordered


def first_existing_cover(book_dir: Path) -> Optional[Path]:
    """
    Cover preference:
      1) pages/001.webp (or any ext)
      2) thumbs/001.webp (or any ext)
    """
    for base in [book_dir / "pages", book_dir / "thumbs"]:
        for ext in IMAGE_EXTS:
            candidate = base / f"001{ext}"
            if candidate.exists():
                return candidate
    return None


def collect_books() -> List[BookTile]:
    if not BOOKS_DIR.exists():
        return []

    tiles: List[BookTile] = []
    for book in sorted(BOOKS_DIR.iterdir(), key=lambda p: p.name.lower()):
        if not book.is_dir():
            continue

        viewer = book / "viewer.html"
        if not viewer.exists():
            continue

        cover = first_existing_cover(book)
        if not cover:
            # If no cover found, still list it (text-only tile fallback)
            tiles.append(BookTile(viewer_href=f"books/{book.name}/viewer.html", cover_src="", name=book.name))
            continue

        tiles.append(
            BookTile(
                viewer_href=f"books/{book.name}/viewer.html",
                cover_src=str(cover.relative_to(ROOT)).replace("\\", "/"),
                name=book.name,
            )
        )

    return tiles


def build_index_html(app_groups: Dict[str, List[AppLink]], books: List[BookTile]) -> str:
    logo_svg = r"""
<svg width="44" height="44" viewBox="0 0 44 44" aria-hidden="true">
  <rect x="2" y="2" width="40" height="40" rx="12" fill="rgba(255,255,255,0.06)" stroke="rgba(255,255,255,0.10)"/>
  <circle cx="16" cy="16" r="4" fill="white" opacity="0.90"/>
  <circle cx="28" cy="16" r="4" fill="white" opacity="0.70"/>
  <circle cx="16" cy="28" r="4" fill="white" opacity="0.70"/>
  <circle cx="28" cy="28" r="4" fill="white" opacity="0.90"/>
</svg>
""".strip()

    # Apps section
    apps_html = ""
    if app_groups:
        topic_blocks = []
        for topic, apps in app_groups.items():
            cards = []
            for a in apps:
                desc_html = f"<p class='muted'>{a.desc}</p>" if a.desc else "<p class='muted'>&nbsp;</p>"
                cards.append(f"""
<a class="card" href="{a.href}">
  <div class="card-title">{a.title}</div>
  {desc_html}
  <div class="chip">{topic}</div>
</a>
""".strip())
            topic_blocks.append(f"""
<section class="block">
  <div class="block-head">
    <h2>{topic}</h2>
    <div class="count">{len(apps)} app{"s" if len(apps)!=1 else ""}</div>
  </div>
  <div class="grid">
    {''.join(cards)}
  </div>
</section>
""".strip())
        apps_html = f"""
<section class="section">
  <div class="section-head">
    <h1>Apps</h1>
    <p class="muted">Drop any <code>.html</code> file into the site root and it appears here automatically.</p>
  </div>
  {''.join(topic_blocks)}
</section>
""".strip()

    # Books section
    book_tiles = []
    for b in books:
        if b.cover_src:
            book_tiles.append(f"""
<a href="{b.viewer_href}" class="tile" title="{b.name}">
  <img src="{b.cover_src}" alt="{b.name}">
  <div class="tile-label">{b.name}</div>
</a>
""".strip())
        else:
            # text-only fallback
            book_tiles.append(f"""
<a href="{b.viewer_href}" class="tile tile-text" title="{b.name}">
  <div class="tile-label">{b.name}</div>
</a>
""".strip())

    books_html = ""
    if books:
        books_html = f"""
<section class="section">
  <div class="section-head">
    <h1>Books</h1>
    <p class="muted">Viewer pages are discovered in <code>books/&lt;book&gt;/viewer.html</code>.</p>
  </div>
  <div class="tiles">
    {''.join(book_tiles)}
  </div>
</section>
""".strip()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{SITE_OWNER} • {SITE_TITLE}</title>
<style>
  :root {{
    --bg: #0b0d10;
    --panel: rgba(255,255,255,0.06);
    --panel2: rgba(255,255,255,0.04);
    --stroke: rgba(255,255,255,0.10);
    --text: rgba(255,255,255,0.92);
    --muted: rgba(255,255,255,0.65);
    --shadow: 0 24px 60px rgba(0,0,0,0.45);
    --r: 18px;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial;
    background: radial-gradient(1200px 600px at 20% 0%, rgba(255,255,255,0.08), transparent 50%),
                radial-gradient(900px 500px at 90% 10%, rgba(255,255,255,0.06), transparent 55%),
                var(--bg);
    color: var(--text);
  }}
  .wrap {{
    max-width: 1100px;
    margin: 0 auto;
    padding: 28px 18px 60px;
  }}
  header {{
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 18px 18px;
    border: 1px solid var(--stroke);
    background: var(--panel);
    border-radius: var(--r);
    box-shadow: var(--shadow);
  }}
  .brand {{
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 0;
  }}
  .brand h1 {{
    font-size: 18px;
    margin: 0;
    letter-spacing: 0.2px;
  }}
  .brand p {{
    margin: 2px 0 0;
    color: var(--muted);
    font-size: 13px;
  }}
  .spacer {{ flex: 1; }}
  .pill {{
    border: 1px solid var(--stroke);
    background: var(--panel2);
    border-radius: 999px;
    padding: 8px 12px;
    color: var(--muted);
    font-size: 13px;
    white-space: nowrap;
  }}
  .section {{
    margin-top: 22px;
    padding: 18px;
    border: 1px solid var(--stroke);
    background: var(--panel2);
    border-radius: var(--r);
  }}
  .section-head h1 {{
    font-size: 16px;
    margin: 0 0 6px;
  }}
  .muted {{
    color: var(--muted);
    margin: 0;
    font-size: 13px;
    line-height: 1.35;
  }}
  code {{
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
    font-size: 12px;
    color: rgba(255,255,255,0.82);
    background: rgba(0,0,0,0.25);
    padding: 2px 6px;
    border-radius: 8px;
    border: 1px solid rgba(255,255,255,0.08);
  }}
  .block {{ margin-top: 16px; }}
  .block-head {{
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 10px;
  }}
  .block-head h2 {{
    font-size: 14px;
    margin: 0;
    color: rgba(255,255,255,0.88);
  }}
  .count {{ color: var(--muted); font-size: 12px; }}
  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 12px;
  }}
  .card {{
    display: block;
    text-decoration: none;
    color: inherit;
    padding: 14px 14px 12px;
    border-radius: 16px;
    border: 1px solid var(--stroke);
    background: rgba(0,0,0,0.18);
    transition: transform 120ms ease, background 120ms ease, border-color 120ms ease;
  }}
  .card:hover {{
    transform: translateY(-2px);
    background: rgba(0,0,0,0.25);
    border-color: rgba(255,255,255,0.18);
  }}
  .card-title {{
    font-size: 14px;
    margin: 0 0 6px;
    letter-spacing: 0.1px;
  }}
  .chip {{
    display: inline-block;
    margin-top: 10px;
    font-size: 11px;
    color: rgba(255,255,255,0.72);
    border: 1px solid rgba(255,255,255,0.10);
    background: rgba(255,255,255,0.05);
    padding: 4px 8px;
    border-radius: 999px;
  }}
  .tiles {{
    margin-top: 10px;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 16px;
  }}
  .tile {{
    display: block;
    text-decoration: none;
    color: inherit;
    border-radius: 16px;
    overflow: hidden;
    border: 1px solid var(--stroke);
    background: rgba(0,0,0,0.20);
    transition: transform 120ms ease, border-color 120ms ease;
    min-height: 60px;
  }}
  .tile:hover {{
    transform: translateY(-2px);
    border-color: rgba(255,255,255,0.18);
  }}
  .tile img {{
    width: 100%;
    height: 140px;
    object-fit: cover;
    object-position: top;
    display: block;
  }}
  .tile-label {{
    padding: 10px 12px;
    font-size: 13px;
    color: rgba(255,255,255,0.82);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
  .tile.tile-text {{
    display: flex;
    align-items: center;
  }}
  footer {{
    margin-top: 22px;
    text-align: center;
    color: rgba(255,255,255,0.50);
    font-size: 12px;
  }}
</style>
</head>
<body>
  <div class="wrap">
    <header>
      <div class="brand">
        {logo_svg}
        <div>
          <h1>{SITE_OWNER} • {SITE_TITLE}</h1>
          <p>{TAGLINE}</p>
        </div>
      </div>
      <div class="spacer"></div>
      <div class="pill">Auto-indexed • apps + books</div>
    </header>

    {apps_html}
    {books_html}

    <footer>
      Built by index-builder.py • Drop apps in root • Book viewers in books/&lt;book&gt;/
    </footer>
  </div>
</body>
</html>
"""


def main() -> int:
    app_groups = collect_root_apps()
    books = collect_books()

    html = build_index_html(app_groups, books)
    OUT.write_text(html, encoding="utf-8")

    apps_count = sum(len(v) for v in app_groups.values())
    print(f"✓ Built {OUT}")
    print(f"  Apps:  {apps_count} (topics: {len(app_groups)})")
    print(f"  Books: {len(books)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

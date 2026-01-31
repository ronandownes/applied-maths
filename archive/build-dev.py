#!/usr/bin/env python3
"""
build-dev.py - Generate viewer-dev.html for each book folder
"""

import json
import re
from pathlib import Path
from typing import List, Optional, Dict, Any

# Configuration
BOOKS_ROOT = Path("E:/gallery/books")
SCRIPT_DIR = Path(__file__).parent
TEMPLATE_FILE = SCRIPT_DIR / "viewer-template-dev.html"

IMAGE_EXTS = {".webp", ".jpg", ".jpeg", ".png", ".gif"}


def find_images(folder: Path) -> List[Path]:
    """Find all image files in a folder, sorted numerically."""
    if not folder.exists():
        return []
    
    images = [f for f in folder.iterdir() 
              if f.is_file() and f.suffix.lower() in IMAGE_EXTS]
    
    def num_key(p: Path) -> tuple:
        m = re.search(r'(\d+)', p.name)
        return (int(m.group(1)), p.name.lower()) if m else (999999, p.name.lower())
    
    images.sort(key=num_key)
    return images


def find_pages_folder(book_dir: Path) -> Optional[Path]:
    """Find the folder containing page images."""
    if find_images(book_dir):
        return book_dir
    
    for subfolder in book_dir.iterdir():
        if not subfolder.is_dir():
            continue
        if subfolder.name.lower() in {"thumbs", "thumb", "thumbnails", "tn"}:
            continue
        images = find_images(subfolder)
        if images:
            return subfolder
    
    return None


def find_toc_file(book_dir: Path) -> Optional[Path]:
    """Find TOC text file in book folder."""
    txt_files = list(book_dir.glob("*.txt"))
    
    if not txt_files:
        return None
    
    for f in txt_files:
        if 'toc' in f.name.lower():
            return f
    
    return txt_files[0]


def parse_toc(toc_file: Optional[Path]) -> Dict[str, Any]:
    """Parse TOC file into chapters and sections."""
    result = {"chapters": []}
    
    if not toc_file or not toc_file.exists():
        return result
    
    current_chapter = None
    
    for line in toc_file.read_text(encoding='utf-8', errors='replace').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        parts = [p.strip() for p in line.split('|')]
        if not parts:
            continue
        
        kind = parts[0].upper()
        
        if kind == "CHAPTER" and len(parts) >= 3:
            code = parts[1]
            title = parts[2]
            
            kv = {}
            for p in parts[3:]:
                if '=' in p:
                    k, v = p.split('=', 1)
                    k, v = k.strip(), v.strip()
                    kv[k] = int(v) if v.isdigit() else v
            
            current_chapter = {
                "code": code,
                "title": title,
                "start": kv.get("start", 1),
                "end": kv.get("end", kv.get("start", 1)),
                "sections": []
            }
            result["chapters"].append(current_chapter)
        
        elif kind == "SECTION" and len(parts) >= 3:
            if current_chapter is None:
                continue
            
            code = parts[1]
            title = parts[2]
            
            kv = {}
            for p in parts[3:]:
                if '=' in p:
                    k, v = p.split('=', 1)
                    k, v = k.strip(), v.strip()
                    kv[k] = int(v) if v.isdigit() else v
            
            current_chapter["sections"].append({
                "code": code,
                "title": title,
                "start": kv.get("start", 1),
                "end": kv.get("end", kv.get("start", 1))
            })
    
    return result


def discover_books() -> List[Path]:
    """Find all book folders."""
    if not BOOKS_ROOT.exists():
        return []
    
    books = []
    for folder in BOOKS_ROOT.iterdir():
        if folder.is_dir() and not folder.name.startswith('.'):
            if find_pages_folder(folder):
                books.append(folder)
    
    return sorted(books, key=lambda p: p.name.lower())


def build_viewer(book_dir: Path) -> bool:
    """Generate viewer-dev.html for a single book."""
    print(f"\nProcessing: {book_dir.name}")
    
    pages_folder = find_pages_folder(book_dir)
    if not pages_folder:
        print(f"  ✗ No pages found")
        return False
    
    images = find_images(pages_folder)
    if not images:
        print(f"  ✗ No images found")
        return False
    
    img_base = "" if pages_folder == book_dir else pages_folder.name.lower()
    
    toc_file = find_toc_file(book_dir)
    toc_data = parse_toc(toc_file)
    
    template = TEMPLATE_FILE.read_text(encoding='utf-8')
    
    viewer_html = template.replace('__BOOK_NAME__', book_dir.name)
    viewer_html = viewer_html.replace('__IMG_BASE__', json.dumps(img_base))
    viewer_html = viewer_html.replace('__PAGES__', json.dumps([img.name for img in images]))
    viewer_html = viewer_html.replace('__TOC__', json.dumps(toc_data))
    
    output_file = book_dir / "viewer-dev.html"
    output_file.write_text(viewer_html, encoding='utf-8')
    
    print(f"  ✓ {len(images)} pages, {len(toc_data['chapters'])} chapters")
    print(f"  ✓ viewer-dev.html created")
    
    return True


def main():
    print("=" * 60)
    print("BOOK VIEWER DEV BUILDER")
    print("=" * 60)
    
    if not TEMPLATE_FILE.exists():
        print(f"\n✗ Template not found: {TEMPLATE_FILE}")
        return 1
    
    books = discover_books()
    
    if not books:
        print(f"\n✗ No books found in: {BOOKS_ROOT}")
        return 1
    
    print(f"\nFound {len(books)} books")
    
    success = sum(1 for book in books if build_viewer(book))
    
    print("\n" + "=" * 60)
    print(f"✓ Built {success}/{len(books)} dev viewers")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    exit(main())

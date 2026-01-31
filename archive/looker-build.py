#!/usr/bin/env python3
"""
looker-build.py - Generate looker.html for each book folder
Independent testing version - creates looker.html files without breaking existing viewer.html
"""

import json
import re
from pathlib import Path
from typing import List, Optional, Dict, Any

# Configuration
BOOKS_ROOT = Path("E:/gallery/books")
SCRIPT_DIR = Path(__file__).parent
TEMPLATE_FILE = SCRIPT_DIR / "looker-template.html"  # Changed to looker-template.html

IMAGE_EXTS = {".webp", ".jpg", ".jpeg", ".png", ".gif"}
TOC_EXTS = {".txt", ".text"}


def find_images(folder: Path) -> List[Path]:
    """Find all image files in a folder, sorted numerically."""
    if not folder.exists():
        return []
    
    images = [f for f in folder.iterdir() 
              if f.is_file() and f.suffix.lower() in IMAGE_EXTS]
    
    # Sort by numeric prefix
    def num_key(p: Path) -> tuple:
        m = re.search(r'(\d+)', p.name)
        return (int(m.group(1)), p.name.lower()) if m else (999999, p.name.lower())
    
    images.sort(key=num_key)
    return images


def find_pages_folder(book_dir: Path) -> Optional[Path]:
    """Find the folder containing page images."""
    # Check book folder itself first
    if find_images(book_dir):
        return book_dir
    
    # Look for any subfolder with images
    for subfolder in book_dir.iterdir():
        if not subfolder.is_dir():
            continue
        images = find_images(subfolder)
        if images:
            return subfolder
    
    return None


def find_toc_file(book_dir: Path) -> Optional[Path]:
    """Find TOC text file in book folder."""
    # Look for any .txt file
    txt_files = list(book_dir.glob("*.txt"))
    
    if not txt_files:
        return None
    
    # Prefer files with 'toc' in name
    for f in txt_files:
        if 'toc' in f.name.lower():
            return f
    
    # Return first .txt file found
    return txt_files[0]


def parse_toc(toc_file: Optional[Path]) -> Dict[str, Any]:
    """Parse TOC file into chapters and sections."""
    result = {"chapters": [], "offset": 0}
    
    if not toc_file or not toc_file.exists():
        return result
    
    lines = toc_file.read_text(encoding='utf-8', errors='replace').splitlines()
    
    # First, look for offset comment
    offset = 0
    for line in lines:
        line = line.strip()
        if line.startswith('# offset='):
            try:
                offset = int(line.split('=')[1].strip())
                result["offset"] = offset
            except (ValueError, IndexError):
                pass
    
    current_chapter = None
    
    for line in lines:
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
            
            # Parse key-value pairs
            kv = {}
            for p in parts[3:]:
                if '=' in p:
                    k, v = p.split('=', 1)
                    k, v = k.strip(), v.strip()
                    try:
                        kv[k] = int(v)
                    except ValueError:
                        kv[k] = v
            
            start_page = kv.get("start", 1)
            book_start_page = start_page - offset  # Apply offset
            
            current_chapter = {
                "code": code,
                "title": title,
                "start": book_start_page,
                "end": kv.get("end", start_page) - offset,
                "sections": []
            }
            result["chapters"].append(current_chapter)
        
        elif kind == "SECTION" and len(parts) >= 3:
            if current_chapter is None:
                continue
            
            code = parts[1]
            title = parts[2]
            
            # Parse key-value pairs
            kv = {}
            for p in parts[3:]:
                if '=' in p:
                    k, v = p.split('=', 1)
                    k, v = k.strip(), v.strip()
                    try:
                        kv[k] = int(v)
                    except ValueError:
                        kv[k] = v
            
            section_start = kv.get("start", 1)
            book_section_start = section_start - offset
            
            current_chapter["sections"].append({
                "code": code,
                "title": title,
                "start": book_section_start,
                "end": kv.get("end", section_start) - offset
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


def build_looker(book_dir: Path) -> bool:
    """Generate looker.html for a single book."""
    print(f"\nProcessing: {book_dir.name}")
    
    # Find pages
    pages_folder = find_pages_folder(book_dir)
    if not pages_folder:
        print(f"  ✗ No pages found")
        return False
    
    images = find_images(pages_folder)
    if not images:
        print(f"  ✗ No images found")
        return False
    
    # Get relative path for images
    if pages_folder == book_dir:
        img_base = ""
    else:
        img_base = pages_folder.name.lower()
    
    # Parse TOC
    toc_file = find_toc_file(book_dir)
    toc_data = parse_toc(toc_file)
    
    # Create page info with book page numbers
    page_info = []
    for i, img in enumerate(images):
        # Apply offset to all pages
        book_page = i + 1 - toc_data.get("offset", 0)
        
        # Check if this image corresponds to a TOC marker
        for chapter in toc_data["chapters"]:
            if chapter["start"] == book_page:
                break
        
        page_info.append({
            "image_index": i,
            "book_page": book_page
        })
    
    # Load template
    try:
        template = TEMPLATE_FILE.read_text(encoding='utf-8')
    except FileNotFoundError:
        print(f"  ✗ Template not found: {TEMPLATE_FILE}")
        print(f"    Please make sure looker-template.html is in the same directory")
        return False
    
    # Inject data
    viewer_html = template.replace('__BOOK_NAME__', book_dir.name)
    viewer_html = viewer_html.replace('__IMG_BASE__', json.dumps(img_base))
    viewer_html = viewer_html.replace('__PAGES__', json.dumps([img.name for img in images]))
    viewer_html = viewer_html.replace('__PAGE_INFO__', json.dumps(page_info))
    viewer_html = viewer_html.replace('__TOC__', json.dumps(toc_data))
    viewer_html = viewer_html.replace('__OFFSET__', json.dumps(toc_data.get("offset", 0)))
    
    # Write as looker.html (CHANGED: not viewer.html)
    output_file = book_dir / "looker.html"
    output_file.write_text(viewer_html, encoding='utf-8')
    
    print(f"  ✓ {len(images)} pages, {len(toc_data['chapters'])} chapters")
    print(f"  ✓ Offset: {toc_data.get('offset', 0)}")
    print(f"  ✓ Book pages: {page_info[0]['book_page']} to {page_info[-1]['book_page']}")
    print(f"  ✓ looker.html created")  # CHANGED: Updated message
    
    return True


def main():
    """Main entry point."""
    print("=" * 70)
    print("LOOKER BUILDER - INDEPENDENT TESTING VERSION")
    print("=" * 70)
    
    if not TEMPLATE_FILE.exists():
        print(f"\n✗ Template not found: {TEMPLATE_FILE}")
        print(f"  Please create looker-template.html in the same directory")
        return 1
    
    books = discover_books()
    
    if not books:
        print(f"\n✗ No books found in: {BOOKS_ROOT}")
        return 1
    
    print(f"\nFound {len(books)} books")
    
    success = 0
    for book in books:
        if build_looker(book):
            success += 1
    
    print("\n" + "=" * 70)
    print(f"✓ Built {success}/{len(books)} looker.html files")
    print("Note: Files saved as looker.html (not viewer.html)")
    print("Test with: http://yourserver/books/bookname/looker.html")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    exit(main())
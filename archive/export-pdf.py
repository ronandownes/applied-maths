#!/usr/bin/env python3
"""
export-pdf.py - Export page range to PDF
Usage: python export-pdf.py <book-folder> <from> <to>
       python export-pdf.py <book-folder> <from> <to> <output.pdf>
"""

import sys
import re
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Installing Pillow...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
    from PIL import Image

IMAGE_EXTS = {".webp", ".jpg", ".jpeg", ".png", ".gif"}


def find_pages_folder(book_dir: Path) -> Path:
    """Find folder containing page images."""
    # Check for pages subfolder first
    for name in ["pages", "Pages", "PAGES"]:
        p = book_dir / name
        if p.exists() and any(f.suffix.lower() in IMAGE_EXTS for f in p.iterdir()):
            return p
    
    # Check book folder itself
    if any(f.suffix.lower() in IMAGE_EXTS for f in book_dir.iterdir() if f.is_file()):
        return book_dir
    
    # Check any subfolder (skip thumbs)
    for sub in book_dir.iterdir():
        if sub.is_dir() and sub.name.lower() not in {"thumbs", "thumb", "thumbnails"}:
            if any(f.suffix.lower() in IMAGE_EXTS for f in sub.iterdir() if f.is_file()):
                return sub
    
    return book_dir


def get_sorted_images(folder: Path) -> list:
    """Get images sorted numerically."""
    images = [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTS]
    
    def num_key(p):
        m = re.search(r'(\d+)', p.name)
        return (int(m.group(1)), p.name.lower()) if m else (999999, p.name.lower())
    
    return sorted(images, key=num_key)


def export_pdf(book_path: str, from_page: int, to_page: int, output: str = None):
    """Export page range to PDF."""
    book_dir = Path(book_path)
    
    if not book_dir.exists():
        print(f"Error: Book folder not found: {book_dir}")
        return 1
    
    pages_folder = find_pages_folder(book_dir)
    images = get_sorted_images(pages_folder)
    
    if not images:
        print(f"Error: No images found in {pages_folder}")
        return 1
    
    total = len(images)
    print(f"Found {total} pages in {pages_folder.name}/")
    
    # Validate range
    from_page = max(1, min(total, from_page))
    to_page = max(from_page, min(total, to_page))
    
    selected = images[from_page - 1 : to_page]
    print(f"Exporting pages {from_page}-{to_page} ({len(selected)} pages)")
    
    # Output filename
    if output is None:
        output = book_dir / f"pages-{from_page}-{to_page}.pdf"
    else:
        output = Path(output)
    
    # Convert to RGB and save as PDF
    pdf_images = []
    for i, img_path in enumerate(selected):
        print(f"  Processing {i + 1}/{len(selected)}: {img_path.name}")
        img = Image.open(img_path)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        pdf_images.append(img)
    
    if pdf_images:
        pdf_images[0].save(
            output,
            "PDF",
            save_all=True,
            append_images=pdf_images[1:] if len(pdf_images) > 1 else [],
            resolution=100.0
        )
        print(f"\n✓ Saved: {output}")
        print(f"  Size: {output.stat().st_size / 1024 / 1024:.1f} MB")
    
    return 0


def main():
    if len(sys.argv) < 4:
        print("Usage: python export-pdf.py <book-folder> <from> <to> [output.pdf]")
        print("Example: python export-pdf.py \"E:/gallery/books/MyBook\" 1 10")
        print("         python export-pdf.py . 5 20 chapter2.pdf")
        return 1
    
    book_path = sys.argv[1]
    from_page = int(sys.argv[2])
    to_page = int(sys.argv[3])
    output = sys.argv[4] if len(sys.argv) > 4 else None
    
    return export_pdf(book_path, from_page, to_page, output)


if __name__ == "__main__":
    sys.exit(main())

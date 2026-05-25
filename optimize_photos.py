#!/usr/bin/env python3
"""
optimize_photos.py — Сжатие и чистка фото для GitHub Pages

1. Находит UUID всех фото, реально используемых в HTML и base64 B данных
2. Соотносит с файлами на диске (регистронезависимо)
3. Удаляет неиспользуемые
4. Сжимает WebP до quality=80, max 2500px через cwebp
"""

import os
import re
import json
import base64
import subprocess
from pathlib import Path
from collections import defaultdict

PHOTOS_DIR = Path('photos')
HTML_DIR = Path('.')
DATA_DIR = Path('data')
MAX_SIZE = 2500
QUALITY = 80


def extract_uuids_from_html():
    """Extract all photo UUIDs from HTML files (direct /photos/ references)."""
    uuids = set()
    for hf in sorted(HTML_DIR.glob('*.html')):
        content = hf.read_text(errors='ignore')
        # Match /photos/image-<uuid> or /photos/upload-<uuid> (any extension)
        for m in re.finditer(r'/photos/([\w-]+)', content):
            filename = m.group(1).lower()
            # Extract UUID (it's the whole thing for Readymag)
            uuids.add(filename)
    return uuids


def extract_uuids_from_bdata():
    """Extract all photo URLs from base64 B data."""
    uuids = set()
    for df in sorted(DATA_DIR.glob('*-data.js')):
        content = df.read_text(errors='ignore')
        m = re.search(r"var B='([^']+)'", content)
        if not m:
            continue
        try:
            decoded = base64.b64decode(m.group(1))
            # Find all photo URLs in the JSON structure
            for ref in re.findall(rb'/photos/([\w.-]+)', decoded):
                uuids.add(ref.decode().lower())
        except Exception:
            pass
    return uuids


def compress_webp(path, quality=QUALITY, max_size=MAX_SIZE):
    """Re-compress WebP to reduce size."""
    temp_path = path.with_suffix('.tmp.webp')
    try:
        result = subprocess.run(
            ['cwebp', '-q', str(quality),
             '-resize', str(max_size), str(max_size),
             str(path), '-o', str(temp_path)],
            capture_output=True, timeout=30
        )
        if result.returncode == 0 and temp_path.exists():
            old_size = path.stat().st_size
            new_size = temp_path.stat().st_size
            if new_size < old_size * 0.95:  # At least 5% savings
                temp_path.replace(path)
                return old_size - new_size
            temp_path.unlink()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return 0


def main():
    print("=" * 60)
    print("Оптимизация фото для GitHub Pages")
    print("=" * 60)
    
    if not PHOTOS_DIR.exists():
        print("✗ photos/ не найдена")
        return
    
    all_photos = list(PHOTOS_DIR.iterdir())
    total = len(all_photos)
    total_size = sum(f.stat().st_size for f in all_photos if f.is_file())
    print(f"\nВсего файлов: {total}, размер: {total_size / 1024 / 1024:.0f} MB")
    
    # Collect all referenced UUIDs
    html_uuids = extract_uuids_from_html()
    bdata_uuids = extract_uuids_from_bdata()
    all_referenced = html_uuids | bdata_uuids
    
    print(f"Референсы из HTML: {len(html_uuids)}")
    print(f"Референсы из B данных: {len(bdata_uuids)}")
    print(f"Уникальных референсов: {len(all_referenced)}")
    
    # Map disk files to referenced UUIDs (case-insensitive)
    referenced_disk = set()
    for f in all_photos:
        if not f.is_file():
            continue
        # Normalize: remove extension, lowercase
        name_noext = f.stem.lower()
        if name_noext in all_referenced:
            referenced_disk.add(f.name)
    
    print(f"Найдено на диске из референсов: {len(referenced_disk)}")
    
    # Delete unreferenced photos
    deleted = 0
    deleted_size = 0
    for f in all_photos:
        if f.is_file() and f.name not in referenced_disk:
            deleted_size += f.stat().st_size
            f.unlink()
            deleted += 1
    
    print(f"Удалено неиспользуемых: {deleted} ({deleted_size / 1024 / 1024:.0f} MB)")
    
    # Re-compress remaining photos
    remaining = list(PHOTOS_DIR.iterdir())
    print(f"\nСжатие {len(remaining)} фото...")
    
    total_saved = 0
    compressed = 0
    
    for i, f in enumerate(sorted(remaining)):
        if not f.is_file():
            continue
        saved = compress_webp(f)
        if saved > 0:
            total_saved += saved
            compressed += 1
        if (i + 1) % 50 == 0:
            print(f"  ...обработано {i + 1}/{len(remaining)}")
    
    final_size = sum(f.stat().st_size for f in PHOTOS_DIR.iterdir() if f.is_file())
    final_count = len(list(PHOTOS_DIR.iterdir()))
    
    print(f"\n{'=' * 60}")
    print(f"Итого:")
    print(f"  Файлов: {final_count}")
    print(f"  Размер: {final_size / 1024 / 1024:.0f} MB")
    print(f"  Сэкономлено: {(deleted_size + total_saved) / 1024 / 1024:.0f} MB")
    print(f"  Дополнительно сжато: {compressed} файлов, -{total_saved / 1024 / 1024:.1f} MB")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
optimize_photos.py v2 — Сжатие и чистка фото для GitHub Pages

Исправлено: сравнение идёт по UUID без расширения (Path().stem)
- B данные ссылаются на /photos/Image-xxx.webp
- На диске файлы Image-xxx.webp
- Сравниваем stem (Image-xxx) регистронезависимо
"""

import re
import json
import base64
import subprocess
from pathlib import Path

PHOTOS_DIR = Path('photos')
HTML_DIR = Path('.')
DATA_DIR = Path('data')
MAX_SIZE = 2500
QUALITY = 80


def get_referenced_uuids():
    """Get ALL photo UUIDs referenced by any B data or HTML.
    
    Нормализует: убирает расширение и trailing dots, lowercase.
    """
    uuids = set()
    
    # From B data files
    for df in sorted(DATA_DIR.glob('*-data.js')):
        content = df.read_text(errors='ignore')
        m = re.search(r"var B='([^']+)'", content)
        if not m:
            continue
        try:
            decoded = base64.b64decode(m.group(1))
            for ref in re.findall(rb'/photos/([\w.-]+)', decoded):
                ref = ref.decode()
                uuid = Path(ref).stem  # removes .webp, .jpg, .png
                uuids.add(uuid.lower())
        except Exception:
            pass
    
    # From HTML direct references  
    for hf in sorted(HTML_DIR.glob('*.html')):
        content = hf.read_text(errors='ignore')
        for m in re.finditer(r'/photos/([\w.-]+)', content):
            ref = m.group(1)
            uuid = Path(ref).stem  # removes trailing dot or extension
            uuids.add(uuid.lower())
    
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
            if new_size < old_size * 0.95:
                temp_path.replace(path)
                return old_size - new_size
            temp_path.unlink()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return 0


def main():
    print("=" * 60)
    print("Оптимизация фото для GitHub Pages (v2)")
    print("=" * 60)
    
    if not PHOTOS_DIR.exists():
        print("✗ photos/ не найдена")
        return
    
    all_photos = sorted(PHOTOS_DIR.iterdir())
    total = len(all_photos)
    total_size = sum(f.stat().st_size for f in all_photos if f.is_file())
    print(f"\nВсего файлов: {total}, размер: {total_size / 1024 / 1024:.0f} MB")
    
    # Get referenced UUIDs
    referenced = get_referenced_uuids()
    print(f"Уникальных UUID в референсах: {len(referenced)}")
    
    # Match disk files to references (by stem, case-insensitive)
    referenced_disk = set()
    for f in all_photos:
        if not f.is_file():
            continue
        uuid = f.stem.lower()
        if uuid in referenced:
            referenced_disk.add(f.name)
    
    print(f"Найдено на диске из референсов: {len(referenced_disk)}")
    print(f"Неиспользуемых на диске: {total - len(referenced_disk)}")
    
    # Delete unreferenced photos
    deleted = 0
    deleted_size = 0
    for f in all_photos:
        if f.is_file() and f.name not in referenced_disk:
            deleted_size += f.stat().st_size
            f.unlink()
            deleted += 1
    
    print(f"\nУдалено неиспользуемых: {deleted} ({deleted_size / 1024 / 1024:.0f} MB)")
    
    # Re-compress remaining photos with cwebp
    remaining = list(PHOTOS_DIR.iterdir())
    if remaining:
        print(f"\nСжатие {len(remaining)} фото через cwebp (quality={QUALITY}, max={MAX_SIZE}px)...")
    
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
    print(f"  Доп. сжато: {compressed} файлов, -{total_saved / 1024 / 1024:.1f} MB")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()

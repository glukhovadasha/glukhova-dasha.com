#!/usr/bin/env python3
"""
extract_b_data.py v4 — Вынос inline B-данных из HTML в отдельные JS файлы

Readymag-экспорт: var B='<base64>',W=JSON.parse('...'),F=...
B не заканчивается на '; — он заканчивается на ', (запятая, цепочка к W).
Поэтому регекс должен искать var B='<content>' (без '; в конце).
"""

import os
import re
from pathlib import Path

HTML_DIR = Path('.')
DATA_DIR = Path('./data')

def main():
    print("=" * 60)
    print("Вынос B-данных из HTML в отдельные JS файлы (v4)")
    print("=" * 60)
    
    DATA_DIR.mkdir(exist_ok=True)
    
    html_files = sorted(HTML_DIR.glob('*.html'))
    print(f"\nНайдено HTML файлов: {len(html_files)}")
    
    total_saved = 0
    processed = 0
    
    for hf in html_files:
        content = hf.read_text(errors='ignore')
        
        # Find var B='...' — НЕ ищем '; в конце, так как B заканчивается на ',W=
        # Используем [^']+ чтобы остановиться на первом ' после начала B значения
        match = re.search(r"var B='([^']+)'", content)
        
        if not match:
            print(f"  ⚠ {hf.name}: B-данные не найдены")
            continue
        
        b_data = match.group(1)  # just the base64 content
        full_b = match.group(0)  # "var B='...'"
        b_pos = match.start()
        b_size = len(b_data.encode('utf-8'))
        page_name = hf.stem
        
        # Create JS file: var B='...'
        js_filename = f'{page_name}-data.js'
        js_path = DATA_DIR / js_filename
        js_path.write_text(f"var B='{b_data}';\n")
        
        # In the HTML, remove var B='...', (with trailing comma)
        # This leaves W=JSON.parse(...),F=... intact
        b_declaration = full_b + ','  # "var B='...',"
        content = content.replace(b_declaration, '', 1)
        
        # Find the <script> tag that contained this B data
        # Search backwards from the B position to find the opening <script>
        before_b = content[:b_pos]
        last_script_open = before_b.rfind('<script')
        if last_script_open == -1:
            print(f"  ✗ {hf.name}: не найден <script> тег")
            continue
        
        # Insert external script BEFORE this <script> tag
        external_tag = f'<script src="data/{js_filename}"></script>\n'
        content = content[:last_script_open] + external_tag + content[last_script_open:]
        
        hf.write_text(content)
        
        total_saved += b_size
        processed += 1
        
        print(f"  ✓ {hf.name}: {b_size/1024:.0f}KB → data/{js_filename}")
    
    print(f"\n{'=' * 60}")
    print(f"Обработано: {processed} файлов")
    print(f"Данных вынесено: {total_saved / 1024 / 1024:.1f} MB")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()

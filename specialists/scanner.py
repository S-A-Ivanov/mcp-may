import os
import uuid
from pathlib import Path
from specialists.inventory import FileInventory

# [⚙] СКАНЕР: Рекурсивный обход директории
def scan_directory(directory: str, max_files: int = 100):
    """
    #S_EN: [SCANNER] Рекурсивно находит файлы для индексации.
    Returns: (List of file_info, scanned_count, skipped_count)
    """
    root_path = Path(directory).resolve()
    
    # Расширения и исключения (можно вынести в начало файла)
    SUPPORTED = {'.py', '.md', '.yaml', '.yml', '.txt', '.json'}
    EXCLUDED = {'venv', '.git', 'chroma_db', '__pycache__', '.idea', '.vscode', 'inventory.db','.vault_internal'}

    results = []
    scanned = 0
    skipped = 0

    print(f"🔍 Мэй начинает обход: {directory}")

    # Используем rglob для глубокого поиска
    for filepath in root_path.rglob('*'):
        if scanned >= max_files: break
        
        if not filepath.is_file(): continue

        # ⟦🛡⟧ Проверка на черные списки папок
        if any(part in EXCLUDED for part in filepath.parts):
            skipped += 1
            continue

        # ⟦🛡⟧ Проверка расширения
        if filepath.suffix.lower() not in SUPPORTED:
            skipped += 1
            continue

        # Формируем информацию для выдачи
        results.append({
            'path': str(filepath.relative_to(root_path)),
            'extension': filepath.suffix.lower()
        })
        scanned += 1

    return results, scanned, skipped

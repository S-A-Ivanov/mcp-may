"""
#S_EN: [CORE] Утилиты для работы с файлами и путями.

Централизует всю низкоуровневую работу с файловой системой.
"""

import os
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any, Set, Tuple
import yaml


class FileSystemUtils:
    """#S_EN: [FS_UTILS] Утилиты для работы с файловой системой.
    
    Предоставляет методы для:
    - Нормализации путей
    - Проверки прав доступа
    - Атомарной записи файлов
    - Вычисления хэшей
    - Сканирования директорий
    """
    
    DEFAULT_SUPPORTED_EXTENSIONS = {'.py', '.md', '.yaml', '.yml', '.txt', '.json'}
    DEFAULT_EXCLUDED_DIRS = {
        'venv', '.git', 'chroma_db', '__pycache__', 
        '.idea', '.vscode', 'node_modules', '.vault_internal'
    }
    
    def __init__(
        self,
        supported_extensions: Optional[Set[str]] = None,
        excluded_dirs: Optional[Set[str]] = None
    ):
        """Инициализация утилит файловой системы.
        
        Args:
            supported_extensions: Поддерживаемые расширения файлов.
            excluded_dirs: Исключаемые директории.
        """
        self.supported_extensions = supported_extensions or self.DEFAULT_SUPPORTED_EXTENSIONS
        self.excluded_dirs = excluded_dirs or self.DEFAULT_EXCLUDED_DIRS
    
    @staticmethod
    def normalize_path(path: str | Path) -> Path:
        """Нормализует путь к файлу или директории.
        
        Args:
            path: Путь для нормализации.
            
        Returns:
            Нормализованный абсолютный путь.
        """
        if isinstance(path, str):
            path = Path(path)
        return path.resolve()
    
    @staticmethod
    def get_file_hash(file_path: Path, algorithm: str = 'md5') -> Optional[str]:
        """Вычисляет хэш файла.
        
        Args:
            file_path: Путь к файлу.
            algorithm: Алгоритм хэширования (md5, sha256).
            
        Returns:
            Хэш файла или None при ошибке.
        """
        try:
            if algorithm == 'md5':
                hasher = hashlib.md5()
            elif algorithm == 'sha256':
                hasher = hashlib.sha256()
            else:
                raise ValueError(f"Неподдерживаемый алгоритм: {algorithm}")
            
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return None
    
    @staticmethod
    def get_file_content(
        file_path: Path, 
        encoding: str = 'utf-8',
        errors: str = 'ignore'
    ) -> Optional[str]:
        """Читает содержимое файла.
        
        Args:
            file_path: Путь к файлу.
            encoding: Кодировка файла.
            errors: Обработка ошибок кодировки.
            
        Returns:
            Содержимое файла или None при ошибке.
        """
        try:
            with open(file_path, 'r', encoding=encoding, errors=errors) as f:
                return f.read()
        except Exception:
            return None
    
    @staticmethod
    def read_lines(
        file_path: Path,
        encoding: str = 'utf-8',
        errors: str = 'ignore'
    ) -> Optional[List[str]]:
        """Читает файл построчно.
        
        Args:
            file_path: Путь к файлу.
            encoding: Кодировка.
            errors: Обработка ошибок.
            
        Returns:
            Список строк или None при ошибке.
        """
        try:
            with open(file_path, 'r', encoding=encoding, errors=errors) as f:
                return f.readlines()
        except Exception:
            return None
    
    def scan_directory(
        self,
        directory: Path | str,
        max_files: int = 100,
        recursive: bool = True
    ) -> Tuple[List[Dict[str, str]], int, int]:
        """Сканирует директорию на наличие файлов.
        
        Args:
            directory: Корневая директория для сканирования.
            max_files: Максимальное количество файлов.
            recursive: Рекурсивное сканирование.
            
        Returns:
            Кортеж (список файлов, количество просканировано, количество пропущено).
        """
        if isinstance(directory, str):
            directory = Path(directory)
        root_path = directory.resolve()
        results = []
        scanned = 0
        skipped = 0
        
        # Выбираем метод обхода
        glob_method = root_path.rglob if recursive else root_path.glob
        
        for filepath in glob_method('*'):
            if scanned >= max_files:
                break
            
            if not filepath.is_file():
                continue
            
            # Проверка на исключенные директории
            if any(part in self.excluded_dirs for part in filepath.parts):
                skipped += 1
                continue
            
            # Проверка расширения
            if filepath.suffix.lower() not in self.supported_extensions:
                skipped += 1
                continue
            
            results.append({
                'path': str(filepath.relative_to(root_path)),
                'extension': filepath.suffix.lower(),
                'full_path': str(filepath)
            })
            scanned += 1
        
        return results, scanned, skipped
    
    @staticmethod
    def ensure_directory(dir_path: Path) -> bool:
        """Создает директорию если она не существует.
        
        Args:
            dir_path: Путь к директории.
            
        Returns:
            True если директория существует или создана.
        """
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception:
            return False
    
    @staticmethod
    def save_yaml(file_path: Path, data: Dict[str, Any]) -> bool:
        """Сохраняет данные в YAML файл атомарно.
        
        Args:
            file_path: Путь к файлу.
            data: Данные для сохранения.
            
        Returns:
            True если успешно.
        """
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            # Атомарная запись через временный файл
            temp_path = file_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True, sort_keys=False)
            temp_path.replace(file_path)
            return True
        except Exception:
            return False
    
    @staticmethod
    def load_yaml(file_path: Path) -> Optional[Dict[str, Any]]:
        """Загружает данные из YAML файла.
        
        Args:
            file_path: Путь к файлу.
            
        Returns:
            Данные или None при ошибке.
        """
        try:
            if not file_path.exists():
                return None
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception:
            return None
    
    @staticmethod
    def is_readable(file_path: Path) -> bool:
        """Проверяет доступность файла для чтения.
        
        Args:
            file_path: Путь к файлу.
            
        Returns:
            True если файл доступен для чтения.
        """
        try:
            return file_path.exists() and os.access(file_path, os.R_OK)
        except Exception:
            return False
    
    @staticmethod
    def is_writable(file_path: Path) -> bool:
        """Проверяет доступность файла для записи.
        
        Args:
            file_path: Путь к файлу.
            
        Returns:
            True если файл доступен для записи.
        """
        try:
            parent = file_path.parent
            return parent.exists() and os.access(parent, os.W_OK)
        except Exception:
            return False


# Глобальный экземпляр для удобства
fs_utils = FileSystemUtils()

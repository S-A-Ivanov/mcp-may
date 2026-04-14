"""
#S_EN: [SESSION] Менеджер сессий и управления файлами.

Обеспечивает:
1. Изоляцию сессий (каждая сессия работает со своей директорией)
2. Централизованное управление файловыми операциями
3. Кэширование и отслеживание состояния для каждой сессии
4. Уменьшение дублирования кода в проекте
"""

import os
import hashlib
import time
import uuid
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
import yaml


logger = logging.getLogger(__name__)


@dataclass
class SessionContext:
    """Контекст одной сессии работы с директорией.
    
    Attributes:
        session_id: Уникальный идентификатор сессии.
        root_path: Корневая директория для этой сессии.
        created_at: Время создания сессии.
        last_active: Время последней активности.
        file_cache: Кэш информации о файлах в этой сессии.
        processed_files: Множество обработанных файлов.
        lock: Асинхронная блокировка для потокобезопасности.
    """
    session_id: str
    root_path: Path
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    file_cache: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    processed_files: Set[str] = field(default_factory=set)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    
    def __post_init__(self):
        # Преобразуем строку в Path если нужно
        if isinstance(self.root_path, str):
            self.root_path = Path(self.root_path)
    
    def update_activity(self):
        """Обновляет время последней активности."""
        self.last_active = time.time()
    
    def is_expired(self, timeout: float = 3600) -> bool:
        """Проверяет, истекло ли время жизни сессии.
        
        Args:
            timeout: Таймаут в секундах (по умолчанию 1 час).
            
        Returns:
            True если сессия устарела.
        """
        return (time.time() - self.last_active) > timeout


class FileManager:
    """#S_EN: [FILE_OPS] Универсальный менеджер файловых операций.
    
    Централизует всю работу с файлами, уменьшая дублирование кода.
    """
    
    # Расширения файлов и исключения (конфигурируемые)
    DEFAULT_SUPPORTED_EXTENSIONS = {'.py', '.md', '.yaml', '.yml', '.txt', '.json'}
    DEFAULT_EXCLUDED_DIRS = {
        'venv', '.git', 'chroma_db', '__pycache__', 
        '.idea', '.vscode', 'inventory.db', '.vault_internal', 'node_modules'
    }
    
    def __init__(
        self,
        supported_extensions: Optional[Set[str]] = None,
        excluded_dirs: Optional[Set[str]] = None
    ):
        """Инициализация менеджера файлов.
        
        Args:
            supported_extensions: Поддерживаемые расширения файлов.
            excluded_dirs: Исключаемые директории.
        """
        self.supported_extensions = supported_extensions or self.DEFAULT_SUPPORTED_EXTENSIONS
        self.excluded_dirs = excluded_dirs or self.DEFAULT_EXCLUDED_DIRS
        self.logger = logging.getLogger("mcp_may.file_manager")
    
    def get_file_hash(self, file_path: Path) -> Optional[str]:
        """Вычисляет MD5 хэш файла.
        
        Args:
            file_path: Путь к файлу.
            
        Returns:
            MD5 хэш или None если файл не доступен.
        """
        try:
            hasher = hashlib.md5()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            self.logger.error(f"❌ Ошибка вычисления хэша {file_path}: {e}")
            return None
    
    def get_file_content(
        self, 
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
        except Exception as e:
            self.logger.error(f"❌ Ошибка чтения {file_path}: {e}")
            return None
    
    def read_lines(
        self,
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
        except Exception as e:
            self.logger.error(f"❌ Ошибка чтения строк {file_path}: {e}")
            return None
    
    def scan_directory(
        self,
        directory: Path | str,
        max_files: int = 100,
        recursive: bool = True
    ) -> tuple[List[Dict[str, str]], int, int]:
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
        
        self.logger.info(f"🔍 Сканирование директории: {directory}")
        
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
    
    def save_yaml(self, file_path: Path, data: Dict[str, Any]) -> bool:
        """Сохраняет данные в YAML файл.
        
        Args:
            file_path: Путь к файлу.
            data: Данные для сохранения.
            
        Returns:
            True если успешно.
        """
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True, sort_keys=False)
            self.logger.info(f"📝 Сохранено: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Ошибка записи YAML {file_path}: {e}")
            return False
    
    def load_yaml(self, file_path: Path) -> Optional[Dict[str, Any]]:
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
        except Exception as e:
            self.logger.error(f"❌ Ошибка чтения YAML {file_path}: {e}")
            return None
    
    def ensure_directory(self, dir_path: Path) -> bool:
        """Создает директорию если она не существует.
        
        Args:
            dir_path: Путь к директории.
            
        Returns:
            True если директория существует или создана.
        """
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            self.logger.error(f"❌ Ошибка создания директории {dir_path}: {e}")
            return False


class SessionManager:
    """#S_EN: [SESSION_MGR] Менеджер сессий для изоляции работы с директориями.
    
    Позволяет нескольким сессиям одновременно работать с разными директориями,
    обеспечивая полную изоляцию контекстов.
    
    Пример использования:
        session_mgr = SessionManager()
        
        # Создание сессии
        async with session_mgr.create_session("/path/to/dir1") as session:
            # Работа с первой директорией
            files = await session_mgr.scan_files(session.session_id)
            
        # Вторая сессия может работать с другой директорией параллельно
        async with session_mgr.create_session("/path/to/dir2") as session2:
            files2 = await session_mgr.scan_files(session2.session_id)
    """
    
    def __init__(
        self,
        session_timeout: float = 3600,
        cleanup_interval: float = 600
    ):
        """Инициализация менеджера сессий.
        
        Args:
            session_timeout: Время жизни сессии в секундах.
            cleanup_interval: Интервал очистки старых сессий.
        """
        self.sessions: Dict[str, SessionContext] = {}
        self.file_manager = FileManager()
        self.session_timeout = session_timeout
        self.cleanup_interval = cleanup_interval
        self.logger = logging.getLogger("mcp_may.session_manager")
        self._lock = asyncio.Lock()
        
        # Запускаем фоновую задачу очистки
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def start_cleanup_task(self):
        """Запускает фоновую задачу очистки устаревших сессий."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            self.logger.info("🧹 Задача очистки сессий запущена")
    
    async def stop_cleanup_task(self):
        """Останавливает задачу очистки."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
    
    async def _cleanup_loop(self):
        """Фоновый цикл очистки устаревших сессий."""
        try:
            while True:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_expired_sessions()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            self.logger.error(f"❌ Ошибка в цикле очистки: {e}")
    
    async def _cleanup_expired_sessions(self):
        """Очищает устаревшие сессии."""
        async with self._lock:
            expired = [
                sid for sid, ctx in self.sessions.items()
                if ctx.is_expired(self.session_timeout)
            ]
            for sid in expired:
                del self.sessions[sid]
                self.logger.info(f"🗑️ Сессия {sid} удалена по таймауту")
    
    @asynccontextmanager
    async def create_session(self, directory: str):
        """Создает новую сессию для работы с директорией.
        
        Используется как контекстный менеджер:
            async with session_mgr.create_session("/path") as session:
                # работа с сессией
        
        Args:
            directory: Путь к директории для сессии.
            
        Yields:
            SessionContext: Контекст сессии.
        """
        session_id = str(uuid.uuid4())
        root_path = Path(directory).resolve()
        
        if not root_path.exists():
            raise ValueError(f"Директория не существует: {directory}")
        
        context = SessionContext(
            session_id=session_id,
            root_path=root_path
        )
        
        async with self._lock:
            self.sessions[session_id] = context
        
        self.logger.info(f"🆕 Сессия {session_id} создана для {directory}")
        
        try:
            yield context
        finally:
            # Опционально: можно удалять сессию после выхода из контекста
            # или оставить её для повторного использования
            async with self._lock:
                if session_id in self.sessions:
                    del self.sessions[session_id]
            self.logger.info(f"🚫 Сессия {session_id} завершена")
    
    def get_session(self, session_id: str) -> Optional[SessionContext]:
        """Получает контекст сессии по ID.
        
        Args:
            session_id: Идентификатор сессии.
            
        Returns:
            SessionContext или None если сессия не найдена.
        """
        return self.sessions.get(session_id)
    
    async def scan_files(
        self,
        session_id: str,
        max_files: int = 100
    ) -> List[Dict[str, str]]:
        """Сканирует файлы в директории сессии.
        
        Args:
            session_id: Идентификатор сессии.
            max_files: Максимальное количество файлов.
            
        Returns:
            Список файлов.
            
        Raises:
            ValueError: Если сессия не найдена.
        """
        context = self.get_session(session_id)
        if not context:
            raise ValueError(f"Сессия {session_id} не найдена")
        
        async with context.lock:
            context.update_activity()
            files, _, _ = self.file_manager.scan_directory(
                context.root_path,
                max_files=max_files
            )
            context.file_cache['files'] = files
            return files
    
    async def get_file_info(
        self,
        session_id: str,
        relative_path: str
    ) -> Optional[Dict[str, Any]]:
        """Получает информацию о файле в сессии.
        
        Args:
            session_id: Идентификатор сессии.
            relative_path: Относительный путь к файлу.
            
        Returns:
            Информация о файле или None.
        """
        context = self.get_session(session_id)
        if not context:
            return None
        
        async with context.lock:
            context.update_activity()
            full_path = context.root_path / relative_path
            
            if not full_path.exists():
                return None
            
            file_hash = self.file_manager.get_file_hash(full_path)
            content = self.file_manager.get_file_content(full_path)
            
            info = {
                'relative_path': relative_path,
                'full_path': str(full_path),
                'hash': file_hash,
                'size': full_path.stat().st_size,
                'modified': full_path.stat().st_mtime
            }
            
            context.file_cache[relative_path] = info
            return info
    
    async def read_file(
        self,
        session_id: str,
        relative_path: str
    ) -> Optional[str]:
        """Читает содержимое файла в сессии.
        
        Args:
            session_id: Идентификатор сессии.
            relative_path: Относительный путь к файлу.
            
        Returns:
            Содержимое файла или None.
        """
        context = self.get_session(session_id)
        if not context:
            return None
        
        async with context.lock:
            context.update_activity()
            full_path = context.root_path / relative_path
            return self.file_manager.get_file_content(full_path)
    
    async def mark_processed(self, session_id: str, file_path: str):
        """Отмечает файл как обработанный в сессии.
        
        Args:
            session_id: Идентификатор сессии.
            file_path: Путь к файлу.
        """
        context = self.get_session(session_id)
        if context:
            async with context.lock:
                context.processed_files.add(file_path)
                context.update_activity()
    
    def is_processed(self, session_id: str, file_path: str) -> bool:
        """Проверяет, был ли файл обработан в сессии.
        
        Args:
            session_id: Идентификатор сессии.
            file_path: Путь к файлу.
            
        Returns:
            True если файл обработан.
        """
        context = self.get_session(session_id)
        return context and file_path in context.processed_files
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Получает статистику по всем сессиям.
        
        Returns:
            Статистика сессий.
        """
        return {
            'active_sessions': len(self.sessions),
            'sessions': {
                sid: {
                    'root_path': str(ctx.root_path),
                    'created': ctx.created_at,
                    'last_active': ctx.last_active,
                    'cached_files': len(ctx.file_cache),
                    'processed_files': len(ctx.processed_files)
                }
                for sid, ctx in self.sessions.items()
            }
        }


# Глобальный экземпляр для использования в tools.py
session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Получает глобальный экземпляр SessionManager.
    
    Returns:
        SessionManager: Экземпляр менеджера сессий.
    """
    global session_manager
    if session_manager is None:
        session_manager = SessionManager()
    return session_manager

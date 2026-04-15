import os
import time
import uuid
import logging
import requests
import chromadb
from pathlib import Path
from typing import List, Union, Optional, Dict, Any
import asyncio


def get_event_loop() -> asyncio.AbstractEventLoop:
    """Получает или создает event loop для асинхронных операций."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


# 1. Сначала создаем универсальный шлюз (он прочитает config.yaml)
from specialists.gateway import UniversalGateway
gateway = UniversalGateway()

# 3. МЕНЕДЖЕР СЕССИЙ И ФАЙЛОВ (для уменьшения дублирования кода)
from specialists.session import get_session_manager, SessionManager, FileManager
session_manager = get_session_manager()
file_manager = FileManager()

# 🔥 Запускаем event loop и фоновую очистку сессий
loop = get_event_loop()
loop.create_task(session_manager.start_cleanup_task())

# 2. ДИРИЖЕР ВЫЧИСЛЕНИЙ (нужен session_manager для обработки задач)
from specialists.orchestrator import ComputeOrchestrator
orchestrator = ComputeOrchestrator(gateway=gateway, session_manager=session_manager)

# 🔥 Запускаем диспетчер в фоне
loop.create_task(orchestrator.start_dispatcher())


# Настройка логирования
def setup_logging(level: str = "INFO") -> None:
    """Настраивает базовое логирование для приложения."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )

setup_logging("INFO")
logger = logging.getLogger(__name__)

# 2. 🧬 Универсальные эмбеддинги
from specialists.embeddings import UniversalEmbeddingFunction
# Берем модель из конфига через шлюз
emb_fn = UniversalEmbeddingFunction(gateway=gateway)

# 3. 💾 Инициализация Базы данных (всё из конфига)
db_cfg = gateway.cfg.get('storage', {})
chroma_client = chromadb.PersistentClient(path=db_cfg.get('db_path', "./data/chroma_db"))
collection = chroma_client.get_or_create_collection(
    name=db_cfg.get('collection_name', "mcp_knowledge"),
    embedding_function=emb_fn
)

# 4. 🗄️ Инвентарь (SQLite путь тоже из конфига)
from specialists.inventory import FileInventory
inv = FileInventory(db_path=db_cfg.get('inventory_path', "./data/inventory.db"))

# 5. 🏢 Расселение Специалистов (Инъекция зависимостей)
from specialists.semantic import SemanticDirector
from specialists.librarian import Librarian
from specialists.reporter import Reporter

director = SemanticDirector(gateway=gateway)
lib = Librarian(collection, inv, gateway, director, orchestrator)
reporter = Reporter(gateway=gateway)

# ОФФЛАЙН флаги (можно тоже в конфиг, но пока оставим тут)
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_HUB_OFFLINE'] = '1'

def register_tools(mcp) -> None:
    """Регистрация инструментов в объекте FastMCP.
    
    Args:
        mcp: Экземпляр FastMCP для регистрации инструментов.
    """
    
    @mcp.tool()
    async def add_evidence(text: str, status: str = "fact") -> str:
        """#S_EN: [TOOL] Запись разового факта или наблюдения в базу знаний.
        
        Args:
            text: Текст факта или наблюдения.
            status: Статус записи (по умолчанию "fact").
            
        Returns:
            Результат операции записи.
        """
        return await orchestrator.add_task(
            task_type="add_evidence",
            priority=3,
            prompt=text,
            schema="text"
        )
 
    @mcp.tool()
    async def get_verified_brief(query: str, include_gossip: bool = False) -> str:
        """#S_EN: [SECRETARY] Поиск фактов и отдача ГОТОВОГО отчета Боссу.
        
        Args:
            query: Поисковый запрос.
            include_gossip: Включать ли непроверенные данные (по умолчанию False).
            
        Returns:
            Сформированный отчет по запросу.
        """
        return await orchestrator.add_task(
            task_type="coordinated_brief",
            priority=1,
            prompt=query,
            schema="text"
        )

    @mcp.tool()
    async def get_db_stats() -> str:
        """Получение статистики базы данных.
        
        Returns:
            Строка со статистикой по базе знаний.
        """
        return await orchestrator.add_task(
            task_type="get_db_stats",
            priority=3,
            prompt="",
            schema="text"
        )
    
    @mcp.tool()
    async def clear_collection() -> str:
        """Очистка коллекции базы данных.
        
        Returns:
            Результат операции очистки.
        """
        return await orchestrator.add_task(
            task_type="clear_collection",
            priority=3,
            prompt="",
            schema="text"
        )
    
    @mcp.tool()
    async def scan_directory_tool(directory: str, max_files: int = 50) -> str:
        """#S_EN: [SCANNER] Сканирование директории и индексация файлов.
        
        Args:
            directory: Путь к директории для сканирования.
            max_files: Максимальное количество файлов для обработки (по умолчанию 50).
            
        Returns:
            Статус запуска процесса сканирования.
        """
        return await orchestrator.add_task(
            task_type="deep_index",
            priority=2,
            prompt=f"Scan directory: {directory}, max_files: {max_files}",
            schema="text"
        )

    @mcp.tool()
    async def get_session_stats() -> str:
        """#S_EN: [SESSION] Получение статистики по активным сессиям.
        
        Returns:
            Строка со статистикой сессий.
        """
        return await orchestrator.add_task(
            task_type="get_session_stats",
            priority=3,
            prompt="",
            schema="text"
        )

    @mcp.tool()
    async def ingest_chunk(content: str, metadata: dict) -> str:
        """#S_EN: [TOOL] Прием умного чанка от внешнего Специалиста.
        
        Args:
            content: Содержимое чанка для индексации.
            metadata: Метаданные чанка.
            
        Returns:
            Результат операции индексации.
        """
        return await orchestrator.add_task(
            task_type="ingest_chunk",
            priority=3,
            prompt=f"Content: {content}, Metadata: {metadata}",
            schema="text"
        )

  
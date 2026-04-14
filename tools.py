import os
import time
import uuid
import logging
import requests
import chromadb
from pathlib import Path
from typing import List, Union
import asyncio


# 1. Сначала создаем универсальный шлюз (он прочитает config.yaml)
from specialists.gateway import UniversalGateway
gateway = UniversalGateway()

# 2. ДИРИЖЕР ВЫЧИСЛЕНИЙ
from specialists.orchestrator import ComputeOrchestrator
orchestrator = ComputeOrchestrator(gateway=gateway)

# 🔥 Запускаем диспетчер в фоне. В асинхронной среде Python это абсолютно легально:
asyncio.get_event_loop().create_task(orchestrator.start_dispatcher())


# Настройка логирования
def setup_logging(level="INFO"):
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
    name=db_cfg.get('collection_name', "mcp_knowledge"), # Добавили дефолт
    embedding_function=emb_fn
)


# 4. 🗄️ Инвентарь (SQLite путь тоже из конфига)
from specialists.inventory import FileInventory
inv = FileInventory(db_path=db_cfg.get('inventory_path', "./data/inventory.db"))

# 5. 🏢 Расселение Специалистов (Инъекция зависимостей)
from specialists.semantic import SemanticDirector
from specialists.librarian import Librarian
from specialists.reporter import Reporter
from specialists.navigator import Navigator

director = SemanticDirector(gateway=gateway)
lib = Librarian(collection, inv, gateway,director, orchestrator)
reporter = Reporter(gateway=gateway) 
navigator = Navigator(gateway=gateway, orchestrator=orchestrator)

# ОФФЛАЙН флаги (можно тоже в конфиг, но пока оставим тут)
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_HUB_OFFLINE'] = '1'

# 🔗 Связываем их с Дирижером!
orchestrator.navigator = navigator
orchestrator.lib = lib
orchestrator.reporter = reporter


def register_tools(mcp):
    """Регистрация инструментов в объекте FastMCP"""
    
    @mcp.tool()
    async def add_evidence(text: str, status: str = "fact") -> str:
        """#S_EN: [TOOL] Запись разового факта или наблюдения в базу знаний."""
        return lib.add_manual_fact(text, status)
 
    # @mcp.tool()
    # async def get_verified_brief(query: str, include_gossip: bool = False) -> str:
    #     """#S_EN: [SECRETARY] Поиск фактов и отдача ГОТОВОГО отчета Боссу."""
        
    #     # Инструмент ничего не знает про Штурмана и Референта. 
    #     # Он просто дергает Библиотекаря!
    #     return await lib.produce_coordinated_brief(query)

    # @mcp.tool()
    # async def get_verified_brief(query: str):
    #     return await lib.search_facts(query)
   
    # @mcp.tool()
    # async def get_verified_brief(query: str, include_gossip: bool = False) -> str:
    #     """#S_EN: [SECRETARY] Поиск фактов и отдача ГОТОВОГО отчета Боссу."""
        
    #     # Мы просто просим референта сделать всю работу!
    #     # Передаем объект библиотекаря (lib), который вы инициализировали в tools.py
    #     return await reporter.create_verified_brief(lib, query, include_gossip)
    
    @mcp.tool()
    async def get_verified_brief(query: str, include_gossip: bool = False) -> str:
        """#S_EN: [SECRETARY] Поиск фактов и отдача ГОТОВОГО отчета Боссу."""
        
        print("🎭 [TOOLS] Передаю задачу напрямую в Оркестратор...")
        
        # Вызываем метод напрямую без очередей и Future!
        try:
            result = await orchestrator.execute_pipeline_directly("coordinated_brief", query)
            return result
        except Exception as e:
            return f"❌ Ошибка выполнения пайплайна: {e}"

    # @mcp.tool()
    # async def get_verified_brief(query: str, include_gossip: bool = False) -> str:
    #     """#S_EN: [SECRETARY] Поиск фактов и отдача ГОТОВОГО отчета Боссу."""
        
    #     # ⚠️ УБИРАЕМ await перед orchestrator.add_task!
    #     # Функция add_task вернет объект Future мгновенно.
    #     task_future = await orchestrator.add_task(
    #         task_type="coordinated_brief",
    #         priority=3,
    #         prompt=query,
    #         schema="text"
    #     )
        
    #     # А вот здесь мы засыпаем и ждем, пока Дирижер выполнит задачу
    #     return await task_future
    
    # @mcp.tool()
    # async def get_verified_brief(query: str, include_gossip: bool = False) -> str:
    #     """#S_EN: [SECRETARY] Поиск фактов и отдача ГОТОВОГО отчета Боссу."""
        
    #     # Ставим задачу Дирижеру на выполнение комплексного пайплайна
    #     future = await orchestrator.add_task(
    #         task_type="coordinated_brief",
    #         priority=3,
    #         prompt=query,
    #         schema="text"
    #     )
    #     # Дожидаемся, пока Дирижер проведет задачу по всем агентам
    #     return await future

   
    # @mcp.tool()
    # async def get_verified_brief(query: str, include_gossip: bool = False) -> str:
    #     """#S_EN: [SECRETARY] Поиск фактов по Теневому Индексу (Proto-Data)."""
        
    #     # Вызов Библиотекаря (теперь метод get_search_context существует)
    #     results = lib.get_search_context(query, n_results=5)

    #     # Проверка на пустоту (ChromaDB возвращает [[], []] если ничего не найдено)
    #     if not results['documents'] or not results['documents'][0]:
    #         return f"🔍 По теме '{query}' в архивах Мэй ничего не найдено."

    #     report = f"⟦⚓⟧ ОТЧЕТ МЭЙ (Найдено атомов: {len(results['documents'][0])})\n"
        
    #     # Распаковываем первый уровень списков [0]
    #     for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
    #         report += "\n" + "─" * 60 + "\n"
    #         report += f"📡 [INDEX]: {doc}\n"
    #         report += f"📍 [UNIT]: {meta.get('header', 'Unknown')}\n"
    #         report += f"💻 [CODE]:\n{meta.get('code', 'N/A')}\n"
            
    #         # Выводим зависимости, если они есть
    #         reqs = meta.get('requires', 'none')
    #         if reqs and reqs != 'none':
    #             report += f"📦 [REQS]: {reqs}\n"
                
    #         report += "─" * 60

    #     return report

    @mcp.tool()
    async def get_db_stats():
        return lib.get_stats()
    
    @mcp.tool()
    async def clear_collection():
        return lib.reset_vault()
    
    @mcp.tool()
    async def scan_directory_tool(directory: str, max_files: int = 50) -> str:
        """#S_EN: [SCANNER] Сканирование директории и индексация файлов."""
        return await lib.scan_dir(directory, max_files)

    @mcp.tool()
    async def ingest_chunk(content: str, metadata: dict) -> str:
        """#S_EN: [TOOL] Прием умного чанка от внешнего Специалиста."""
        return lib.ingest_chunk(content, metadata)

    @mcp.tool()
    async def sync_project_folder(folder_path: str) -> str:
        """#S_EN: [TOOL] Запускает инкрементальную синхронизацию папки."""
        
        if not os.path.exists(folder_path):
            return f"⟦✗⟧ Путь {folder_path} не существует."
            
        # 🚀 1. Сначала привязываем Воркспейс!
        lib.set_workspace(folder_path)
        
        # 2. И только потом запускаем конвейер
        asyncio.create_task(lib.run_pipeline(Path(folder_path), max_files=50))
        
        return f"⟦✓⟧ Рабочее пространство создано в `{folder_path}/.mcp_vault`. Индексация запущена."

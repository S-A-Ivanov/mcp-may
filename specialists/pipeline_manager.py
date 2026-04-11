import asyncio
import logging
from pathlib import Path
import yaml

class PipelineManager:
    def __init__(self, librarian, director, orchestrator):
        self.lib = librarian
        self.director = director
        self.orch = orchestrator # Ссылка на Дирижера
        self.logger = logging.getLogger("mcp_may.pipeline")

    async def run_scenario_full_indexing(self, root_path: Path, files_data: list):
        """#S_EN: [SCENARIO] Полная трехфазная индексация."""
        
        # --- ФАЗА 1: РАЗВЕДКА ---
        self.logger.info("🌍 [PHASE 1] Сбор паспортов...")
        for f_info in files_data:
            path = root_path / f_info['path']
            # Вместо прямого вызова, мы просим Дирижера сделать это на GPU_0 (для Gemma)
            # или в Облаке, смотря что мы прописали в task_routing!
            response = await self.orch.add_task(
                task_type="text_slicing", # Дирижер сам решит, что это для GPU_0
                priority=10, # Низкий приоритет для фоновой задачи
                prompt=f"Проанализируй структуру файла {f_info['path']}...",
                schema="json"
            )
            # Сохраняем паспорт через библиотекаря...

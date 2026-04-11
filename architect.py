import time
import uuid
import logging
from pathlib import Path

class Architect:
    """#S_EN: [AGENT] Специалист по структуре кода и управлению задачами."""
    
    def __init__(self, collection, gateway=None): # 👈 Добавляем gateway
        self.collection = collection
        self.gateway = gateway # 👈 Сохраняем его для будущих умных промптов
        self.forge_path = "./.vault_internal/ai_forge"
        # Гарантируем наличие папки для кодинга
        import os
        os.makedirs(self.forge_path, exist_ok=True)

    def write_code(self, filename: str, content: str) -> str:
        """[TOOL_LOGIC] Запись кода в зону AI_FORGE."""
        try:
            self.forge_dir.mkdir(exist_ok=True)
            file_path = self.forge_dir / filename
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"⟨✓⟩: Код успешно выкован в {file_path}. ⟦HEALTHY⟧"
        except Exception as e:
            return f"❌ Ошибка ковки: {e}"

    def push_to_stack(self, task_name: str, task_body: str, priority: int = 1) -> str:
        """[TOOL_LOGIC] Единый метод записи задачи в Стек (ChromaDB)."""
        doc_id = str(uuid.uuid4())
        self.collection.add(
            documents=[task_body],
            metadatas=[{
                "status": "todo",
                "type": "task_stack",
                "task_name": task_name,
                "priority": priority,
                "timestamp": time.time()
            }],
            ids=[doc_id]
        )
        return f"⟨💾⟩: Задача '{task_name}' сохранена в Стек. Приоритет: {priority}."

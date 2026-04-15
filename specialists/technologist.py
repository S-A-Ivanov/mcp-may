import logging

logger = logging.getLogger("mcp_may.technologist")

class Technologist:
    """
    #S_EN: [ENGINEER] Технолог производства. 
    Хранит технологические карты (рецепты) выполнения сложных процессов.
    """
    def __init__(self):
        # 🗺️ Рецепты обработки задач
        self.recipes = {
            "coordinated_brief": [
                {"step": 1, "actor": "navigator", "action": "build_strategy", "output": "queries"},
                {"step": 2, "actor": "librarian", "action": "fetch_context", "output": "raw_data"},
                {"step": 3, "actor": "reporter", "action": "compile_final", "output": "final_text"}
            ],
            "deep_index": [
                {"step": 1, "actor": "scanner", "action": "scan_dir", "output": "file_list"},
                {"step": 2, "actor": "director", "action": "make_passport", "output": "passports"},
                {"step": 3, "actor": "librarian", "action": "ingest_chunks", "output": "atoms"}
            ],
            "get_db_stats": [
                {"step": 1, "actor": "librarian", "action": "get_stats", "output": "stats"}
            ],
            "clear_collection": [
                {"step": 1, "actor": "librarian", "action": "reset_vault", "output": "result"}
            ],
            "get_session_stats": [
                {"step": 1, "actor": "session_manager", "action": "get_stats", "output": "stats"}
            ]
        }

    def get_routing_card(self, task_type: str) -> list:
        """Выдает карту последовательности шагов для Дирижера."""
        return self.recipes.get(task_type, [])

import asyncio
import logging
from pathlib import Path
import uuid
import yaml


class Librarian:
    """#S_EN: [LIBRARIAN] Хранитель архива v1.0.

    Отвечает за физический поиск, запись в базу по планам и инвентарь [CHUNKING].
    """

    def __init__(self, collection, inventory, gateway, orchestrator):
        self.collection = collection
        self.inv = inventory
        self.gateway = gateway
        self.orchestrator = orchestrator  # Наш Дирижер
        self.logger = logging.getLogger("mcp_may.librarian")

    def save_atom_to_db(
        self, rel_path: str, chunk_content: str, atom_data: dict
    ):
        """#S_EN: [DB_WRITE] Прямая запись одного готового атома в ChromaDB."""
        search_index = f"{atom_data.get('proto', '[OP: None]')} {atom_data.get('intent', 'N/A')} {atom_data.get('tags', '')}"

        metadata = {
            "code": chunk_content,
            "header": f"[{rel_path}]",
            "file_path": rel_path,
            "status": "fact",
        }

        self.collection.add(
            documents=[search_index],
            metadatas=[metadata],
            ids=[str(uuid.uuid4())],
        )

    def get_search_context(self, query: str, n_results: int = 5):
        """#S_EN: [SEARCH] Поиск по базе знаний."""
        # 🛡️ ФИКС: Чтобы не падать на embed_query, мы просим Шлюз сделать это!
        query_vector = [self.gateway.get_embeddings(query)]

        results = self.collection.query(
            query_embeddings=query_vector,
            n_results=n_results,
            where={"status": "fact"},
        )
        return results

    def ingest_by_plan(self, filepath: Path, root_path: Path) -> str:
        """#S_EN: [PHASE_3] Нарезка строго по линиям разметки из планов Фазы 2 [CHUNKING]."""
        rel_path = str(filepath.relative_to(root_path))
        file_id = rel_path.replace("/", "_").replace(".", "_")

        plans_dir = (
            Path(self.gateway.cfg["storage"].get("vault_dir", "./.vault_internal"))
            / "plans"
        )
        plan_file = plans_dir / f"{file_id}_plan.yaml"

        # Если плана нет — берем весь файл как один чанк, чтобы не падать
        if not plan_file.exists():
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            proposed_chunks = [
                {
                    "label": "Full file (No Plan)",
                    "lines": f"1-{len(lines)}",
                    "core_responsibility": "All",
                }
            ]
        else:
            with open(plan_file, "r", encoding="utf-8") as f:
                plan_data = yaml.safe_load(f)
                proposed_chunks = plan_data.get("proposed_chunks", [])

            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

        docs, metas, ids = [], [], []
        self.collection.delete(where={"file_path": rel_path})

        for chunk in proposed_chunks:
            line_range = chunk.get("lines", "1-1")
            try:
                parts = line_range.split("-")
                start_l = max(1, int(parts[0]))
                end_l = min(
                    len(lines), int(parts[1]) if len(parts) > 1 else start_l
                )

                chunk_content = "".join(lines[start_l - 1 : end_l])
                if not chunk_content.strip():
                    continue

                # Вызов Фазы 3 через Директора
                atom = self.director.produce_atom(
                    chunk_content, rel_path, chunk.get("label", "Code")
                )

                search_index = f"{atom.get('proto', '[OP: None]')} {atom.get('intent', 'N/A')} {atom.get('tags', '')}"

                metadata = {
                    "code": chunk_content,
                    "header": f"[{rel_path}][Lines: {line_range}]",
                    "file_path": rel_path,
                    "status": "fact",
                }

                docs.append(search_index)
                metas.append(metadata)
                ids.append(str(uuid.uuid4()))

            except Exception as e:
                self.logger.error(
                    f"❌ Ошибка нарезки в {rel_path} ({line_range}): {e}"
                )

        if docs:
            self.collection.add(documents=docs, metadatas=metas, ids=ids)
            return f"SUCCESS: {len(docs)} атомов"

        return "FAIL"

    def save_file_passport(self, file_path: str, passport_data: dict):
        """#S_EN: [CHRONICLE] Физическое сохранение паспорта в YAML."""
        vault_base = Path(
            self.gateway.cfg["storage"].get("vault_dir", "./.vault_internal")
        )
        pass_dir = vault_base / "passports"
        pass_dir.mkdir(parents=True, exist_ok=True)

        file_id = str(file_path).replace("/", "_").replace(".", "_")
        f_path = pass_dir / f"{file_id}_passport.yaml"

        try:
            with open(f_path, "w", encoding="utf-8") as f:
                yaml.dump(passport_data, f, allow_unicode=True, sort_keys=False)
            self.logger.info(f"  📝 Паспорт выдан: {f_path.name}")
        except Exception as e:
            self.logger.error(f"❌ Ошибка записи паспорта {file_id}: {e}")

    async def scan_dir(self, directory: str, max_files: int = 50) -> str:
        """#S_EN: [TOOL_LOGIC] Точка входа для запуска Конвейера v1.0."""
        from pathlib import Path
        root_path = Path(directory).resolve()

        self.logger.info(f"🚀 Мэй: Команда принята. Запускаю конвейер для {directory}...")
        
        # 🎯 Просим оркестратор или менеджер запустить наш конвейер в фоне
        # Если мы не разделили файлы, вызываем run_pipeline:
        asyncio.create_task(self.run_pipeline(root_path, max_files))

        return f"⟦⚓⟧ Мэй: Конвейер запущен (Разведка -> Паспорта -> Атомы)."

    def get_stats(self) -> str:
        """#S_EN: [STATS] Статистика по Теневому Индексу."""
        count = self.collection.count()
        peek = self.collection.peek(limit=3)
        
        report = f"⟦⚓⟧ СТАТИСТИКА БАЗЫ МЭЙ:\n📊 Всего атомов в индексе: {count}\n"
        if count > 0 and peek.get('documents'):
            report += "\n🔍 Последние смыслы [PROTO]:\n"
            for doc in peek['documents']:
                report += f"- {doc[:100]}...\n"
        return report


    async def run_pipeline(self, root_path: Path, max_files: int):
        """#S_EN: [PIPELINE] Координация фаз."""
        try:
            from specialists.scanner import scan_directory
            files_data, _, _ = scan_directory(str(root_path), max_files)
            
            # --- ФАЗА 1: РАЗВЕДКА ---
            for f_info in files_data:
                path = root_path / f_info['path']
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                passport = self.director.analyze_architecture(content, f_info['path'])
                self.save_file_passport(f_info['path'], passport)
                await asyncio.sleep(0.1)

            # --- ФАЗА 1.5: МАНИФЕСТ ---
            # (Если мы его стерли, пока пропустим или вызовем старую функцию)

            # --- ФАЗА 3: НАВЕДЕНИЕ ПОРЯДКА ---
            for f_info in files_data:
                self.ingest_by_plan(root_path / f_info['path'], root_path)
                await asyncio.sleep(0.1)
                
            self.logger.info("✅ [PIPELINE] Конвейер успешно завершил работу.")

        except Exception as e:
            self.logger.error(f"🚨 [PIPELINE_ERROR]: {e}")

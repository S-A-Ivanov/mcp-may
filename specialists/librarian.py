import asyncio
from pathlib import Path
import uuid
import yaml
from typing import Any, Dict, Optional
from core.base import BaseSpecialist
from core.filesystem import fs_utils


class Librarian(BaseSpecialist):
    """#S_EN: [LIBRARIAN] Хранитель архива v1.0.

    Отвечает за физический поиск, запись в базу по планам и инвентарь [CHUNKING].
    Использует fs_utils из core для работы с файлами.
    
    Наследуется от BaseSpecialist для:
    - Единого логирования
    - Доступа к конфигурации через gateway
    - Стандартизированной инициализации
    """

    def __init__(
        self, 
        collection: Any, 
        inventory: Any, 
        gateway: Any, 
        director: Any, 
        orchestrator: Any
    ):
        """Инициализация Библиотекаря.
        
        Args:
            collection: ChromaDB коллекция для хранения атомов.
            inventory: Менеджер инвентаря файлов.
            gateway: Шлюз для доступа к LLM и конфигурации.
            director: Семантический директор для анализа.
            orchestrator: Оркестратор для фоновых задач.
        """
        super().__init__(name="librarian", gateway=gateway)
        
        self.collection = collection
        self.inv = inventory
        self.director = director
        self.orchestrator = orchestrator
        
        # fs_utils - глобальный экземпляр из core.filesystem
        # Не требует создания нового экземпляра

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
            lines = fs_utils.read_lines(filepath)
            if lines is None:
                lines = []
            proposed_chunks = [
                {
                    "label": "Full file (No Plan)",
                    "lines": f"1-{len(lines)}",
                    "core_responsibility": "All",
                }
            ]
        else:
            plan_data = fs_utils.load_yaml(plan_file)
            proposed_chunks = plan_data.get("proposed_chunks", []) if plan_data else []

            lines = fs_utils.read_lines(filepath)
            if lines is None:
                lines = []

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
            self.cfg["storage"].get("vault_dir", "./.vault_internal")
        )
        pass_dir = vault_base / "passports"
        
        # Используем fs_utils для создания директории и сохранения YAML
        fs_utils.ensure_directory(pass_dir)
        
        file_id = str(file_path).replace("/", "_").replace(".", "_")
        f_path = pass_dir / f"{file_id}_passport.yaml"

        if not fs_utils.save_yaml(f_path, passport_data):
            self.logger.error(f"❌ Ошибка записи паспорта {file_id}")

    async def scan_dir(self, directory: str, max_files: int = 50) -> str:
        """#S_EN: [TOOL_LOGIC] Точка входа для запуска Конвейера v1.0."""
        from pathlib import Path
        root_path = Path(directory).resolve()

        self.logger.info(f"🚀 Мэй: Команда принята. Запускаю конвейер для {directory}...")
        
        # 🎯 Просим оркестратор или менеджер запустить наш конвейер в фоне
        # Если мы не разделили файлы, вызываем run_pipeline:
        asyncio.create_task(self.run_pipeline(root_path, max_files))

        return f"⟦⚓⟧ Мэй: Конвейер запущен (Разведка -> Паспорта -> Атомы)."

    def process(self, *args, **kwargs) -> Any:
        """#S_EN: [PROCESS] Основной метод обработки (требуется BaseSpecialist).
        
        Для Librarian это метод scan_dir, который запускает конвейер.
        """
        return self.scan_dir(*args, **kwargs)
    
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

    def reset_vault(self) -> str:
        """#S_EN: [RESET] Очистка коллекции базы данных."""
        try:
            count = self.collection.count()
            self.collection.delete(where={})
            return f"⟦⚓⟧ БАЗА ОЧИЩЕНА: Удалено {count} атомов."
        except Exception as e:
            self.logger.error(f"Ошибка при очистке базы: {e}")
            return f"Ошибка при очистке базы: {str(e)}"


    async def run_pipeline(self, root_path: Path, max_files: int):
        """#S_EN: [PIPELINE] Координация фаз."""
        try:
            # Используем fs_utils для сканирования директории
            files_data, _, _ = fs_utils.scan_directory(str(root_path), max_files)

            # --- ФАЗА 1: РАЗВЕДКА ---
            self.logger.info("🔍 [PIPELINE] Фаза 1: Сбор паспортов файлов...")
            
            for f_info in files_data:
                rel_path = f_info['path']
                full_path = root_path / rel_path
                
                # 🛡️ Инвентарь сам всё проверит и обновит запись в БД, если файл новый
                if not self.inv.check_and_update(rel_path, str(full_path)):
                    self.logger.info(f"⏸ [PIPELINE] Пропуск (не изменился): {rel_path}")
                    continue
                
                self.logger.info(f"⚡ [PIPELINE] Обнаружены изменения в: {rel_path}")
                
                # Используем fs_utils для чтения файла
                content = fs_utils.get_file_content(full_path)
                if content is None:
                    self.logger.warning(f"⚠️ Не удалось прочитать {rel_path}, пропускаем")
                    continue
                
                # Запуск генерации паспорта
                passport = self.director.analyze_architecture(content, rel_path)
                self.save_file_passport(rel_path, passport)
                
                await asyncio.sleep(0.1)
                
            # --- ФАЗА 1.5: МАНИФЕСТ --- 
            self.logger.info("🌍 [PIPELINE] Фаза 1.5: Сборка Глобального Манифеста...")            
            self._compile_global_manifest()

            # Читаем только что созданный манифест для передачи в Фазу 2            
            manifest_path = Path(self.cfg['storage'].get('vault_dir', './.vault_internal')) / "GLOBAL_MANIFEST.yaml"
            global_manifest_content = ""
            if manifest_path.exists():
                m_data = fs_utils.load_yaml(manifest_path)
                if m_data:
                    global_manifest_content = m_data.get('architecture_summary', '')

            # --- ФАЗА 2: ПЛАНИРОВАНИЕ (Генерация планов нарезки) ---
            self.logger.info("✂️ [PIPELINE] Фаза 2: Планирование нарезки чанков...")
            plans_dir = Path(self.cfg['storage'].get('vault_dir', './.vault_internal')) / "plans"
            
            # Используем fs_utils для создания директории
            fs_utils.ensure_directory(plans_dir)

            for f_info in files_data:
                path = root_path / f_info['path']
                # Используем fs_utils для чтения файла
                content = fs_utils.get_file_content(path)
                if content is None:
                    self.logger.warning(f"⚠️ Не удалось прочитать {f_info['path']} для планирования")
                    continue
                
                # Вызываем метод plan_chunks и передаем туда Манифест!
                plan_result = self.director.plan_chunks(content, f_info['path'], global_manifest_content)
                
                # Сохраняем сгенерированный план в папку plans/ через fs_utils
                file_id = str(f_info['path']).replace("/", "_").replace(".", "_")
                plan_path = plans_dir / f"{file_id}_plan.yaml"
                fs_utils.save_yaml(plan_path, plan_result)
                    
                await asyncio.sleep(0.1)
            
             # --- ФАЗА 3: НАВЕДЕНИЕ ПОРЯДКА (НАРЕЗКА И ВЕКТОРИЗАЦИЯ) ---
            self.logger.info("💾 [PIPELINE] Фаза 3: Нарезка и запись в Теневой Индекс...")
            for f_info in files_data:
                # Метод ingest_by_plan сам прочитает созданный в Фазе 2 YAML-план!
                self.ingest_by_plan(root_path / f_info['path'], root_path)
                await asyncio.sleep(0.1)
            
                
            self.logger.info("✅ [PIPELINE] Конвейер успешно завершил работу.")

        except Exception as e:
            self.logger.error(f"🚨 [PIPELINE_ERROR]: {e}")


    def _compile_global_manifest(self):
        """#S_EN: [LAYER_0.5] Сшивка всех паспортов в единый Манифест."""
        import time
        
        cfg = self.cfg
        vault_base = Path(cfg.get('storage', {}).get('vault_dir', './.vault_internal'))
        pass_dir = vault_base / "passports"
        manifest_path = vault_base / "GLOBAL_MANIFEST.yaml"
        
        self.logger.info(f"🛠 Начинаю сборку Манифеста...")
        
        passport_files = list(pass_dir.glob("*_passport.yaml"))
        if not passport_files:
            self.logger.error("❌ Паспорта не найдены в директории паспортов!")
            return

        all_passports_summary = ""
        for pass_file in passport_files:
            # Используем fs_utils для загрузки YAML
            data = fs_utils.load_yaml(pass_file)
            if data:
                all_passports_summary += f"--- FILE: {pass_file.name} ---\n"
                # Читаем поля, которые генерирует ваша Фаза 1
                all_passports_summary += f"PURPOSE: {data.get('file_purpose', 'N/A')}\n"
                all_passports_summary += f"VERDICT: {data.get('architectural_verdict', 'N/A')}\n\n"

        # Вызываем метод Семантического Директора
        manifest_text = self.director.generate_global_manifest(all_passports_summary)

        # Физическая запись YAML через fs_utils
        manifest_data = {
            "project_name": cfg.get('project', {}).get('name', "NeuralVault"),
            "architecture_summary": manifest_text,
            "processed_files": [p.name for p in passport_files],
            "last_updated": time.ctime()
        }
        
        if not fs_utils.save_yaml(manifest_path, manifest_data):
            self.logger.error(f"❌ Ошибка записи GLOBAL_MANIFEST.yaml")

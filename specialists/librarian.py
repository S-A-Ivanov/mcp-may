import asyncio
import logging
from pathlib import Path
import uuid
import yaml


class Librarian:
    """#S_EN: [LIBRARIAN] Хранитель архива v1.0.

    Отвечает за физический поиск, запись в базу по планам и инвентарь [CHUNKING].
    """

    def __init__(self, collection, inventory, gateway, director, orchestrator):
        self.collection = collection
        self.inv = inventory
        self.gateway = gateway
        self.director = director
        self.orchestrator = orchestrator  
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

            # # --- ФАЗА 1: РАЗВЕДКА ---
            # for f_info in files_data:
            #     path = root_path / f_info['path']
            #     with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            #         content = f.read()
                
            #     passport = self.director.analyze_architecture(content, f_info['path'])
            #     self.save_file_passport(f_info['path'], passport)
            #     await asyncio.sleep(0.1)

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
                
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Запуск генерации паспорта
                passport = self.director.analyze_architecture(content, rel_path)
                self.save_file_passport(rel_path, passport)
                
                await asyncio.sleep(0.1)
            # --- ФАЗА 1.5: МАНИФЕСТ --- 
            self.logger.info("🌍 [PIPELINE] Фаза 1.5: Сборка Глобального Манифеста...")            
            self._compile_global_manifest()

            # Читаем только что созданный манифест для передачи в Фазу 2            
            manifest_path = Path(self.gateway.cfg['storage'].get('vault_dir', './.vault_internal')) / "GLOBAL_MANIFEST.yaml"
            global_manifest_content = ""
            if manifest_path.exists():
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    # Читаем как текст или YAML
                    import yaml
                    m_data = yaml.safe_load(f)
                    global_manifest_content = m_data.get('architecture_summary', '')

            # --- ФАЗА 2: ПЛАНИРОВАНИЕ (Генерация планов нарезки) ---
            self.logger.info("✂️ [PIPELINE] Фаза 2: Планирование нарезки чанков...")
            plans_dir = Path(self.gateway.cfg['storage'].get('vault_dir', './.vault_internal')) / "plans"
            plans_dir.mkdir(parents=True, exist_ok=True)

            for f_info in files_data:
                path = root_path / f_info['path']
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Вызываем ВАШ метод plan_chunks и передаем туда Манифест!
                plan_result = self.director.plan_chunks(content, f_info['path'], global_manifest_content)
                
                # Сохраняем сгенерированный план в папку plans/
                file_id = str(f_info['path']).replace("/", "_").replace(".", "_")
                with open(plans_dir / f"{file_id}_plan.yaml", "w", encoding="utf-8") as f:
                    yaml.dump(plan_result, f, allow_unicode=True, sort_keys=False)
                    
                await asyncio.sleep(0.1)
            
             # --- ФАЗА 3: НАВЕДЕНИЕ ПОРЯДКА (НАРЕЗКА И ВЕКТОРИЗАЦИЯ) ---
            self.logger.info("💾 [PIPELINE] Фаза 3: Нарезка и запись в Теневой Индекс...")
            for f_info in files_data:
                # Ваш метод ingest_by_plan сам прочитает созданный в Фазе 2 YAML-план!
                self.ingest_by_plan(root_path / f_info['path'], root_path)
                await asyncio.sleep(0.1)
            
                
            self.logger.info("✅ [PIPELINE] Конвейер успешно завершил работу.")

        except Exception as e:
            self.logger.error(f"🚨 [PIPELINE_ERROR]: {e}")


    def _compile_global_manifest(self):
        """#S_EN: [LAYER_0.5] Сшивка всех паспортов в единый Манифест."""
        import yaml
        import time
        
        cfg = self.gateway.cfg
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
            try:
                with open(pass_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    all_passports_summary += f"--- FILE: {pass_file.name} ---\n"
                    # Читаем поля, которые генерирует ваша Фаза 1
                    all_passports_summary += f"PURPOSE: {data.get('file_purpose', 'N/A')}\n"
                    all_passports_summary += f"VERDICT: {data.get('architectural_verdict', 'N/A')}\n\n"
            except Exception as e:
                self.logger.warning(f"⚠️ Не смог прочитать {pass_file.name}: {e}")

        # Вызываем метод Семантического Директора
        manifest_text = self.director.generate_global_manifest(all_passports_summary)

        # Физическая запись YAML
        try:
            manifest_data = {
                "project_name": cfg.get('project', {}).get('name', "NeuralVault"),
                "architecture_summary": manifest_text,
                "processed_files": [p.name for p in passport_files],
                "last_updated": time.ctime()
            }
            with open(manifest_path, "w", encoding="utf-8") as f:
                yaml.dump(manifest_data, f, allow_unicode=True, sort_keys=False)
            self.logger.info(f"✅ [MANIFEST] Успешно создан: {manifest_path}")
        except Exception as e:
            self.logger.error(f"❌ Ошибка записи GLOBAL_MANIFEST.yaml: {e}")

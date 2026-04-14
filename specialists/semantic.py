import logging
from pathlib import Path
from core.base import BaseSpecialist

class SemanticDirector(BaseSpecialist):
    def __init__(self, gateway):
        super().__init__(name="semantic")
        self.gateway = gateway
        self.cfg = gateway.cfg.get('indexing', {})
        
        # Настройки из конфига
        self.chunk_size = self.cfg.get('chunk_size', 2500)
        self.overlap = self.cfg.get('overlap', 300)
        
        # Гарантируем наличие папки journals
        vault_base = Path(gateway.cfg.get('storage', {}).get('vault_dir', './.vault_internal'))
        self.vault_dir = vault_base / "journals"
        self.vault_dir.mkdir(parents=True, exist_ok=True)

    def analyze_architecture(self, content: str, file_path: str) -> dict:
        """[PHASE_1] Первичная разведка файла."""
        prompt = f"""
        #S_EN: [IDENTIFICATION]: You are 'ArchitecturalAnalyst'.
        #S_EN: [TASK]: Perform Phase 1 (Reconnaissance) of file: {file_path}.
        #S_EN: [INPUT_DATA]:
        ```python
        {content[:4000]}
        ```
        #S_EN: [STRICT_JSON_OUTPUT]:
        {{
          "file_purpose": "Краткая суть файла (RU)",
          "classes": [{{ "name": "ClassName", "desc": "Роль" }}],
          "methods": [{{ "name": "method_name", "desc": "суть" }}],
          "key_dependencies": ["lib1", "module2"],
          "architectural_verdict": "Твой вердикт: чистота кода и баги (RU)",
          "recon_status": "SUCCESS"
        }}
        """
        return self.gateway.ask(specialist="semantic", prompt=prompt, schema="json")

    def plan_chunks(self, content: str, file_path: str, global_manifest: str) -> dict:
        """[PHASE_2] Логическая разметка файлов на чанки."""
        lines = content.splitlines()
        
        # 🐘 ДРОБИТЕЛЬ: Если в файле больше 500 строк, мы не шлем его весь
        if len(lines) > 500:
            self.logger.warning(f"🐘 Файл {file_path} слишком большой ({len(lines)} строк). Беру только первые 500 для разметки.")
            content = "\n".join(lines[:500])

        prompt = f"""
        #S_EN: [IDENTIFICATION]: You are 'SlicingPlanner'.
        #S_EN: [GLOBAL_MANIFEST]: {global_manifest}
        #S_EN: [TASK]: Analyze this file and propose LOGICAL chunks. 
        #S_EN: [RULE]: Do not cut methods or classes in half!
        #S_EN: [FILE_TO_PLAN]: {file_path}
        #S_EN: [INPUT_CODE]:
        ```python
        {content}
        ```
        #S_EN: [STRICT_JSON_OUTPUT]:
        {{
          "proposed_chunks": [
            {{ "label": "Brief description", "lines": "1-20", "core_responsibility": "Что делает (RU)" }}
          ]
        }}
        """
        return self.gateway.ask(specialist="semantic", prompt=prompt, schema="json")

    def produce_atom(self, chunk_content: str, file_path: str, label: str) -> dict:
        """[PHASE_3] Создание атома для базы."""
        prompt = f"""
        #S_EN: [IDENTIFICATION]: You are 'AtomProducer'.
        #S_EN: [FILE]: {file_path}
        #S_EN: [BLOCK_ROLE]: {label}
        #S_EN: [INPUT_CODE_BLOCK]:
        ```python
        {chunk_content}
        ```
        #S_EN: [STRICT_JSON_FORMAT]:
        {{
          "proto": "[OP: ...] [TARGET: ...]",
          "intent": "Краткий смысл на русском",
          "tags": "#tag1"
        }}
        """
        return self.gateway.ask(specialist="semantic", prompt=prompt, schema="json")

    def generate_global_manifest(self, all_passports_summary: str) -> str:
        """[PHASE_1.5] Генерация текста манифеста через LLM."""
        
        prompt = f"""
        #S_EN: [IDENTIFICATION]: You are 'ArchitecturalAnalyst'.
        #S_EN: [TASK] Create GLOBAL ARCHITECTURAL MANIFEST.
        #S_EN: [GOAL] Summarize the project's logic, tech stack, and key 'pits' (flaws).
        #S_EN: [DATA_FROM_PASSPORTS]:
        {all_passports_summary}
        """
        
        self.logger.info("📡 Отправка суммаризированных паспортов в LLM для генерации Манифеста...")
        res = self.gateway.ask(specialist="semantic", prompt=prompt)
        return res.get("response", "Manifest generation failed.")



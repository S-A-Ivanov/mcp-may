import json
import time
import yaml
import requests
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

from core.llm_gateway import LLMBasicGateway


class UniversalGateway(LLMBasicGateway):
    """#S_EN: [GATEWAY] Универсальный роутер запросов с тотальным логированием.
    
    Наследуется от LLMBasicGateway из core, добавляет специфичную логику
    маршрутизации по провайдерам.
    
    Attributes:
        cfg: Конфигурация из config.yaml.
        raw_dir: Директория для логов обмена.
        logger: Логгер модуля.
    """
    
    def __init__(self, config_path: str = "config.yaml") -> None:
        """Инициализация шлюза.
        
        Args:
            config_path: Путь к файлу конфигурации относительно корня проекта.
        """
        super().__init__(config_path)

    def _call_ollama_embeddings(self, model: str, text: str) -> List[float]:
        """#S_EN: [INTERNAL] Низкоуровневый запрос векторов.
        
        Переопределяет метод родителя для кастомной логики (если нужна).
        В текущей версии использует реализацию родителя.
        
        Args:
            model: Название модели для эмбеддингов.
            text: Текст для векторизации.
            
        Returns:
            Вектор эмбеддинга.
        """
        # Используем реализацию родителя
        return super()._call_ollama_embeddings(model, text)

    def _call_provider(self, provider: str, model: str, prompt: str, 
                       schema: str, timeout: int) -> Dict[str, Any]:
        """Реализация абстрактного метода маршрутизации по провайдерам.
        
        Args:
            provider: Название провайдера (ollama, openai).
            model: Модель для генерации.
            prompt: Промпт.
            schema: Формат ответа.
            timeout: Таймаут.
            
        Returns:
            Ответ от модели.
            
        Raises:
            ValueError: Если провайдер не реализован.
        """
        if provider == "ollama":
            return self._call_ollama(model, prompt, schema, timeout)
        elif provider == "openai":
            return self._call_openai(model, prompt, schema, timeout)
        else:
            raise ValueError(f"Provider {provider} not implemented!")

    def ask(self, specialist: str, prompt: str, schema: str = "text") -> Dict[str, Any]:
        """#S_EN: [PROCESS] Главный метод запроса.
        
        Переопределяет метод родителя для добавления специфичного логирования TARGET.
        
        Args:
            specialist: Имя специалиста из конфигурации.
            prompt: Промпт для LLM.
            schema: Формат ответа ('text' или 'json').
            
        Returns:
            Ответ от LLM или словарь с ошибкой.
            
        Raises:
            ValueError: Если специалист не настроен в конфигурации.
        """
        route = self.cfg['routing'].get(specialist)
        if not route:
            raise ValueError(f"Specialist '{specialist}' not configured in config.yaml!")

        provider = route['provider']
        model = route['model']
        timeout = route.get('timeout', 90)

        # 🕒 Имя лога по времени: ГГГГММДД_ЧЧММСС_СПЕЦ_МОДЕЛЬ
        ts = time.strftime("%Y%m%d_%H%M%S")
        log_base = f"{ts}_{specialist}_{model.replace(':', '-')}"
        
        # 📂 Логируем ПРЕДПОЛАГАЕМЫЙ запрос (с указанием провайдера)
        with open(self.raw_dir / f"{log_base}_REQ.txt", "w", encoding="utf-8") as f:
            f.write(f"TARGET: {provider}/{model}\n{'-'*30}\n{prompt}")

        try:
            res = self._call_provider(provider, model, prompt, schema, timeout)

            # 📂 Логируем ПОЛУЧЕННЫЙ ответ
            with open(self.raw_dir / f"{log_base}_RES.json", "w", encoding="utf-8") as f:
                f.write(json.dumps(res, ensure_ascii=False, indent=2))

            return res

        except Exception as e:
            self.logger.error(f"🚨 Gateway Error [{specialist}]: {e}")
            return {"error": str(e), "updated_journal": "Error in LLM call", "chunks": []}

    def _call_ollama(self, model: str, prompt: str, schema: str, timeout: int) -> Dict[str, Any]:
        """Вызов Ollama API.
        
        Args:
            model: Модель для генерации.
            prompt: Промпт.
            schema: Формат ответа.
            timeout: Таймаут запроса.
            
        Returns:
            Ответ от модели.
        """
        url = f"{self.cfg['providers']['ollama']['base_url']}/api/generate"
        payload = {"model": model, "prompt": prompt, "stream": False}
        if schema == "json":
            payload["format"] = "json"
        
        r = requests.post(url, json=payload, timeout=timeout)
        r.raise_for_status()
        
        raw_txt = r.json().get("response", "")
        if schema == "json":
            return json.loads(raw_txt)
        return {"response": raw_txt}

    def _call_openai(self, model: str, prompt: str, schema: str, timeout: int) -> Dict[str, Any]:
        """Заглушка для OpenAI.
        
        Args:
            model: Модель.
            prompt: Промпт.
            schema: Формат.
            timeout: Таймаут.
            
        Returns:
            Заглушка ответа.
        """
        # Реализуем по запросу, пока заглушка
        return {"response": "OpenAI Not Configured Yet"}

    def get_from_hf(self, repo_id: str, filename: str) -> str:
        """#S_EN: [HF_HUB] Загрузка моделей или весов через шлюз.
        
        Переопределяет метод родителя для кастомного логирования.
        
        Args:
            repo_id: ID репозитория на HuggingFace.
            filename: Имя файла для загрузки.
            
        Returns:
            Путь к загруженному файлу.
        """
        token = self.cfg['providers']['hf_hub'].get('token')
        cache = self.cfg['providers']['hf_hub'].get('cache_dir')
        
        self.logger.info(f"📡 Gateway: Загрузка {filename} из {repo_id}...")
        
        # Логируем действие в наш общий реестр (кастомный формат)
        ts = time.strftime("%Y%m%d_%H%M%S")
        with open(self.raw_dir / f"{ts}_HF_DOWNLOAD.txt", "w") as f:
            f.write(f"REPO: {repo_id}\nFILE: {filename}")

        from huggingface_hub import hf_hub_download
        return hf_hub_download(
            repo_id=repo_id, 
            filename=filename, 
            token=token, 
            cache_dir=cache
        )
    
    def get_embeddings(self, text: str, model: Optional[str] = None) -> List[float]:
        """Получение эмбеддингов для текста.
        
        Переопределяет метод родителя для использования секции 'embeddings'.
        
        Args:
            text: Текст для векторизации.
            model: Модель для эмбеддингов (опционально).
            
        Returns:
            Вектор эмбеддинга или нулевой вектор при ошибке.
        """
        # Берем настройки из секции 'embeddings' в config.yaml
        cfg = self.cfg['routing'].get('embeddings', {})
        provider = cfg.get('provider', 'ollama')
        model = model or cfg.get('model')

        # Логируем только если уровень DEBUG или если возникла ошибка
        try:
            if provider == "ollama":
                return super().get_embeddings(text, model)
            elif provider == "openai":
                # Здесь можно добавить _call_openai_embeddings при необходимости
                pass
            return [0.0] * 1024
        except Exception as e:
            self.logger.error(f"🚨 Embedding Error: {e}")
            return [0.0] * 1024

    async def ask_via_resource(
        self, 
        resource: str, 
        prompt: str, 
        schema: str = "text"
    ) -> Dict[str, Any]:
        """#S_EN: [GATEWAY] Роутинг запроса на конкретный порт или провайдера.
        
        Args:
            resource: Имя ресурса из конфигурации.
            prompt: Промпт для генерации.
            schema: Формат ответа.
            
        Returns:
            Ответ от ресурса.
            
        Raises:
            ValueError: Если ресурс не найден в конфигурации.
        """
        res_cfg = self.cfg.get('compute_resources', {}).get(resource)
        if not res_cfg:
            raise ValueError(f"Resource {resource} not found in config.yaml!")

        provider = res_cfg['provider']
        model = res_cfg['active_model']
        
        # 1. Если это Оллама, меняем порты
        if provider == "ollama":
            port = res_cfg.get('port', 11434)
            url = f"http://127.0.0.1:{port}/api/generate"
            
            payload = {"model": model, "prompt": prompt, "stream": False}
            if schema == "json":
                payload["format"] = "json"
                
            # Выполняем синхронный запрос в пуле потоков, чтобы не вешать асинхронность
            loop = asyncio.get_running_loop()
            
            def _call() -> requests.Response:
                return requests.post(url, json=payload, timeout=120)
                
            r = await loop.run_in_executor(None, _call)
            r.raise_for_status()
            
            raw_txt = r.json().get("response", "")
            if schema == "json":
                return json.loads(raw_txt)
            return {"response": raw_txt}
            
        # 2. Если это облако (OpenRouter или OpenAI)
        elif provider == "openrouter":
            # (Здесь будет твой код для облака при необходимости)
            return {"response": "CLOUD_STUB: OpenRouter call not implemented yet."}
        
        raise ValueError(f"Unknown provider: {provider}")


"""#S_EN: [CORE] LLM Gateway - Универсальный роутер запросов к языковым моделям.

Этот модуль содержит низкоуровневую инфраструктуру для взаимодействия с LLM:
- Маршрутизация запросов к разным провайдерам (Ollama, OpenAI, etc.)
- Логирование обмена данными (raw exchange logs)
- Получение эмбеддингов
- Загрузка моделей из HuggingFace Hub
- Асинхронные вызовы через compute_resources

Classes:
    LLMBasicGateway: Базовый класс шлюза с общей логикой маршрутизации и логирования.
"""

import json
import time
import yaml
import requests
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod


class LLMBasicGateway(ABC):
    """#S_EN: [GATEWAY] Базовый класс универсального роутера запросов.
    
    Предоставляет общую инфраструктуру для работы с LLM:
    - Загрузка конфигурации
    - Настройка путей для логирования
    - Маршрутизация по провайдерам
    - Логирование запросов/ответов
    
    Attributes:
        cfg: Конфигурация из config.yaml.
        raw_dir: Директория для логов обмена.
        logger: Логгер модуля.
    """
    
    def __init__(self, config_path: str = "config.yaml") -> None:
        """Инициализация шлюза.
        
        Args:
            config_path: Путь к файлу конфигурации относительно корня проекта.
            
        Raises:
            FileNotFoundError: Если файл конфигурации не найден.
        """
        # 📂 Принудительно ищем конфиг в корне проекта
        base_dir = Path(__file__).parent.parent.resolve()
        full_config_path = base_dir / config_path
        
        if not full_config_path.exists():
            raise FileNotFoundError(f"❌ Критическая ошибка: Не нашел {full_config_path}")
            
        with open(full_config_path, 'r', encoding='utf-8') as f:
            self.cfg: Dict[str, Any] = yaml.safe_load(f)
        
        # Настройка путей из конфига через абсолютный путь
        self.raw_dir = base_dir / self.cfg['storage'].get('vault_dir', './.vault_internal') / "raw_exchange"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("mcp_may.gateway")

    @abstractmethod
    def _call_provider(self, provider: str, model: str, prompt: str, 
                       schema: str, timeout: int) -> Dict[str, Any]:
        """Абстрактный метод вызова провайдера. Должен быть реализован в наследнике."""
        pass

    def _log_request(self, specialist: str, model: str, prompt: str) -> tuple[str, str]:
        """Логирование запроса в raw_dir.
        
        Args:
            specialist: Имя специалиста/ресурса.
            model: Название модели.
            prompt: Текст запроса.
            
        Returns:
            Кортеж (base_name, request_file_path).
        """
        ts = time.strftime("%Y%m%d_%H%M%S")
        log_base = f"{ts}_{specialist}_{model.replace(':', '-')}"
        
        req_path = self.raw_dir / f"{log_base}_REQ.txt"
        with open(req_path, "w", encoding="utf-8") as f:
            f.write(f"TARGET: {model}\n{'-'*30}\n{prompt}")
        
        return log_base, str(req_path)

    def _log_response(self, log_base: str, response: Dict[str, Any]) -> str:
        """Логирование ответа в raw_dir.
        
        Args:
            log_base: Базовое имя файла.
            response: Ответ от LLM.
            
        Returns:
            Путь к файлу с ответом.
        """
        res_path = self.raw_dir / f"{log_base}_RES.json"
        with open(res_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(response, ensure_ascii=False, indent=2))
        return str(res_path)

    def _log_hf_download(self, repo_id: str, filename: str) -> str:
        """Логирование загрузки из HuggingFace.
        
        Args:
            repo_id: ID репозитория.
            filename: Имя файла.
            
        Returns:
            Путь к файлу лога.
        """
        ts = time.strftime("%Y%m%d_%H%M%S")
        log_path = self.raw_dir / f"{ts}_HF_DOWNLOAD.txt"
        with open(log_path, "w") as f:
            f.write(f"REPO: {repo_id}\nFILE: {filename}")
        return str(log_path)

    def ask(self, specialist: str, prompt: str, schema: str = "text") -> Dict[str, Any]:
        """#S_EN: [PROCESS] Главный метод синхронного запроса.
        
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

        # 📂 Логируем запрос
        log_base, _ = self._log_request(specialist, model, prompt)
        
        try:
            res = self._call_provider(provider, model, prompt, schema, timeout)

            # 📂 Логируем ответ
            self._log_response(log_base, res)

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
        return {"response": "OpenAI Not Configured Yet"}

    def _call_ollama_embeddings(self, model: str, text: str) -> List[float]:
        """#S_EN: [INTERNAL] Низкоуровневый запрос векторов.
        
        Args:
            model: Название модели для эмбеддингов.
            text: Текст для векторизации.
            
        Returns:
            Вектор эмбеддинга.
        """
        url = f"{self.cfg['providers']['ollama']['base_url']}/api/embeddings"
        payload = {"model": model, "prompt": text}
        
        r = requests.post(url, json=payload, timeout=60)
        r.raise_for_status()
        
        return r.json().get("embedding", [0.0] * 1024)

    def get_from_hf(self, repo_id: str, filename: str) -> str:
        """#S_EN: [HF_HUB] Загрузка моделей или весов через шлюз.
        
        Args:
            repo_id: ID репозитория на HuggingFace.
            filename: Имя файла для загрузки.
            
        Returns:
            Путь к загруженному файлу.
        """
        from huggingface_hub import hf_hub_download
        
        token = self.cfg['providers']['hf_hub'].get('token')
        cache = self.cfg['providers']['hf_hub'].get('cache_dir')
        
        self.logger.info(f"📡 Gateway: Загрузка {filename} из {repo_id}...")
        
        # Логируем действие
        self._log_hf_download(repo_id, filename)

        return hf_hub_download(
            repo_id=repo_id, 
            filename=filename, 
            token=token, 
            cache_dir=cache
        )
    
    def get_embeddings(self, text: str, model: Optional[str] = None) -> List[float]:
        """Получение эмбеддингов для текста.
        
        Args:
            text: Текст для векторизации.
            model: Модель для эмбеддингов (опционально).
            
        Returns:
            Вектор эмбеддинга или нулевой вектор при ошибке.
        """
        cfg = self.cfg['routing'].get('embeddings', {})
        provider = cfg.get('provider', 'ollama')
        model = model or cfg.get('model')

        try:
            if provider == "ollama":
                return self._call_ollama_embeddings(model, text)
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
        
        # 1. Если это Ollama, меняем порты
        if provider == "ollama":
            port = res_cfg.get('port', 11434)
            url = f"http://127.0.0.1:{port}/api/generate"
            
            payload = {"model": model, "prompt": prompt, "stream": False}
            if schema == "json":
                payload["format"] = "json"
                
            # Выполняем синхронный запрос в пуле потоков
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
            return {"response": "CLOUD_STUB: OpenRouter call not implemented yet."}
        
        raise ValueError(f"Unknown provider: {provider}")


# Глобальный экземпляр для удобства использования (будет инициализирован при первом вызове get_llm_gateway)
_llm_gateway_instance: Optional[LLMBasicGateway] = None


def get_llm_gateway(config_path: str = "config.yaml") -> LLMBasicGateway:
    """Получить экземпляр шлюза.
    
    Примечание: LLMBasicGateway является абстрактным классом.
    Для получения рабочего экземпляра используйте UniversalGateway из specialists.gateway.
    
    Args:
        config_path: Путь к файлу конфигурации.
        
    Returns:
        Экземпляр LLMBasicGateway (или наследника).
        
    Raises:
        TypeError: При попытке создать экземпляр абстрактного класса.
    """
    # Эта функция предназначена для использования с конкретными реализациями
    # Например: from specialists.gateway import UniversalGateway; gw = UniversalGateway()
    raise TypeError(
        "LLMBasicGateway is an abstract class. \"\n"
        "Use a concrete implementation like UniversalGateway from specialists.gateway. \"\n"
        "Example: from specialists.gateway import UniversalGateway; gw = UniversalGateway()"
    )

import json
import time
import yaml
import requests
import asyncio
import logging
from pathlib import Path

class UniversalGateway:
    """#S_EN: [GATEWAY] Универсальный роутер запросов с тотальным логированием."""
    
    def __init__(self, config_path="config.yaml"):
        # 📂 Принудительно ищем конфиг в корне проекта (на уровень выше от специалиста)
        base_dir = Path(__file__).parent.parent.resolve()
        full_config_path = base_dir / config_path
        
        if not full_config_path.exists():
            raise FileNotFoundError(f"❌ Критическая ошибка: Не нашел {full_config_path}")
            
        with open(full_config_path, 'r', encoding='utf-8') as f:
            self.cfg = yaml.safe_load(f)
        
        # Настройка путей из конфига тоже через абсолютный путь
        self.raw_dir = base_dir / self.cfg['storage'].get('vault_dir', './.vault_internal') / "raw_exchange"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("mcp_may.gateway")

        
    def _call_ollama_embeddings(self, model, text):
        """#S_EN: [INTERNAL] Низкоуровневый запрос векторов."""
        url = f"{self.cfg['providers']['ollama']['base_url']}/api/embeddings"
        payload = {"model": model, "prompt": text}
        
        r = requests.post(url, json=payload, timeout=60)
        r.raise_for_status()
        
        return r.json().get("embedding", [0.0] * 1024)


    def ask(self, specialist: str, prompt: str, schema: str = "text") -> dict:
        """#S_EN: [PROCESS] Главный метод запроса."""
        route = self.cfg['routing'].get(specialist)
        if not route:
            raise ValueError(f"Specialist '{specialist}' not configured in config.yaml!")

        provider = route['provider']
        model = route['model']
        timeout = route.get('timeout', 90)

        # 🕒 Имя лога по времени: ГГГГММДД_ЧЧММСС_СПЕЦ_МОДЕЛЬ
        ts = time.strftime("%Y%m%d_%H%M%S")
        log_base = f"{ts}_{specialist}_{model.replace(':', '-')}"
        
        # 📂 Логируем ПРЕДПОЛАГАЕМЫЙ запрос
        with open(self.raw_dir / f"{log_base}_REQ.txt", "w", encoding="utf-8") as f:
            f.write(f"TARGET: {provider}/{model}\n{'-'*30}\n{prompt}")

        try:
            if provider == "ollama":
                res = self._call_ollama(model, prompt, schema, timeout)
            elif provider == "openai":
                res = self._call_openai(model, prompt, schema, timeout)
            else:
                raise ValueError(f"Provider {provider} not implemented!")

            # 📂 Логируем ПОЛУЧЕННЫЙ ответ
            with open(self.raw_dir / f"{log_base}_RES.json", "w", encoding="utf-8") as f:
                f.write(json.dumps(res, ensure_ascii=False, indent=2))

            return res

        except Exception as e:
            self.logger.error(f"🚨 Gateway Error [{specialist}]: {e}")
            return {"error": str(e), "updated_journal": "Error in LLM call", "chunks": []}

    def _call_ollama(self, model, prompt, schema, timeout):
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

    def _call_openai(self, model, prompt, schema, timeout):
        # Реализуем по запросу, пока заглушка
        return {"response": "OpenAI Not Configured Yet"}
    

    def get_from_hf(self, repo_id: str, filename: str):
        """#S_EN: [HF_HUB] Загрузка моделей или весов через шлюз."""
        from huggingface_hub import hf_hub_download
        
        token = self.cfg['providers']['hf_hub'].get('token')
        cache = self.cfg['providers']['hf_hub'].get('cache_dir')
        
        self.logger.info(f"📡 Gateway: Загрузка {filename} из {repo_id}...")
        
        # Логируем действие в наш общий реестр
        ts = time.strftime("%Y%m%d_%H%M%S")
        with open(self.raw_dir / f"{ts}_HF_DOWNLOAD.txt", "w") as f:
            f.write(f"REPO: {repo_id}\nFILE: {filename}")

        return hf_hub_download(
            repo_id=repo_id, 
            filename=filename, 
            token=token, 
            cache_dir=cache
        )
    
    def get_embeddings(self, text: str, model: str = None) -> list:
        # Берем настройки из секции 'embeddings' в config.yaml
        cfg = self.cfg['routing'].get('embeddings', {})
        provider = cfg.get('provider', 'ollama')
        model = model or cfg.get('model')

        # Логируем только если уровень DEBUG или если возникла ошибка
        try:
            if provider == "ollama":
                return self._call_ollama_embeddings(model, text)
            elif provider == "openai":
                return self._call_openai_embeddings(model, text)
            return [0.0] * 1024
        except Exception as e:
            self.logger.error(f"🚨 Embedding Error: {e}")
            return [0.0] * 1024

    async def ask_via_resource(self, resource: str, prompt: str, schema: str = "text") -> dict:
        """#S_EN: [GATEWAY] Роутинг запроса на конкретный порт или провайдера [CHUNKING]."""
        import requests
        import json
        
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
            
            def _call():
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


import json
import logging

logger = logging.getLogger("mcp_may.navigator")

class Navigator:
    def __init__(self, gateway, orchestrator):
        self.gateway = gateway
        self.orchestrator = orchestrator
        self.logger = logger

    async def build_search_strategy(self, boss_query: str) -> list:
        """
        #S_EN: [PROCESS] Штурман использует Chain-of-Thought для генерации подзапросов.
        Прямой вызов через Gateway во избежание блокировки очереди.
        """
        import json
        
        prompt = f"""
        #S_EN: [IDENTIFICATION]: You are 'May's Research Navigator'.
        #S_EN: [TASK]: Break down the user's query into 3 specific technical search queries for a vector database.
        
        #S_EN: [USER_QUERY]: "{boss_query}"
        
        #S_EN: [INSTRUCTION]: 
        Think step-by-step about what technical terms, file names, or patterns are needed to answer this.
        Then output EXACTLY a JSON array of 3 strings.
        
        #S_EN: [STRICT_JSON_OUTPUT]:
        [
          "search term 1",
          "search term 2",
          "search term 3"
        ]
        """
        
        try:
            self.logger.info("🧭 Штурман делает прямой запрос к LLM...")
            
            # 🚀 Используем асинхронный метод шлюза, который мы видели ранее!
            # Он отправляет запрос на порт Олламы в пуле потоков
            result = await self.gateway.ask_via_resource(
                resource="gpu_local", # Укажите имя ресурса из вашего config.yaml (например, gpu_local)
                prompt=prompt,
                schema="json"
            )
            
            if isinstance(result, list):
                return result
            return [boss_query]
            
        except Exception as e:
            self.logger.error(f"Ошибка Штурмана при построении стратегии: {e}")
            return [boss_query]


    # async def build_search_strategy(self, boss_query: str) -> list:
    #     """
    #     #S_EN: [PROCESS] Штурман использует Chain-of-Thought для генерации подзапросов.
    #     """
    #     # Т.к. lfm2.5 отлично понимает английский, промпт даем на нем
    #     prompt = f"""
    #     #S_EN: [IDENTIFICATION]: You are 'May's Research Navigator'.
    #     #S_EN: [TASK]: Break down the user's query into 3 specific technical search queries for a vector database.
        
    #     #S_EN: [USER_QUERY]: "{boss_query}"
        
    #     #S_EN: [INSTRUCTION]: 
    #     Think step-by-step about what technical terms, file names, or patterns are needed to answer this.
    #     Then output EXACTLY a JSON array of 3 strings.
        
    #     #S_EN: [STRICT_JSON_OUTPUT]:
    #     [
    #       "search term 1",
    #       "search term 2",
    #       "search term 3"
    #     ]
    #     """
        
    #     try:
    #         # 🚦 Отправляем задачу в Очередь Дирижера!
    #         task_future = await self.orchestrator.add_task(
    #             task_type="search_strategy",
    #             priority=2, # Высокий приоритет для размышлений
    #             prompt=prompt,
    #             schema="json"
    #         )
            
    #         # Ждем выполнения ответа от GPU
    #         result = await task_future
            
    #         # Модель lfm2.5 сама сформирует теги <think>...</think>, Ollama их отдаст
    #         # Шлюз вернет нам распарсенный список благодаря schema="json"
    #         if isinstance(result, list):
    #             return result
    #         return [boss_query] # Фолбэк
            
    #     except Exception as e:
    #         logger.error(f"Ошибка Штурмана при построении стратегии: {e}")
    #         return [boss_query]

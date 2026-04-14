import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from specialists.technologist import Technologist


class ComputeOrchestrator:
    """#S_EN: [ORCHESTRATOR] Дирижер вычислений.
    
    Управляет очередью задач и распределяет их по ресурсам (GPU_0, GPU_1, CLOUD).
    
    Attributes:
        gateway: Универсальный шлюз для запросов.
        cfg: Конфигурация из шлюза.
        logger: Логгер модуля.
        technologist: Технолог для получения карт маршрутизации.
        queue: Приоритетная очередь задач.
        running: Флаг работы диспетчера.
        locks: Блокировки ресурсов.
    """
    
    def __init__(self, gateway) -> None:
        """Инициализация оркестратора.
        
        Args:
            gateway: Экземпляр UniversalGateway для доступа к конфигурации и LLM.
        """
        self.gateway = gateway
        # Берем конфиг прямо из шлюза
        self.cfg = gateway.cfg
        self.logger = logging.getLogger("mcp_may.orchestrator")
        self.technologist = Technologist()
        # 🚦 Единая приоритетная очередь
        self.queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.running = True
        
        # Блокировщики ресурсов (чтобы задачи на одной карте не шли одновременно)
        self.locks: Dict[str, asyncio.Lock] = {
            "GPU_0": asyncio.Lock(),
            "GPU_1": asyncio.Lock(),
            "GPU_ALL": asyncio.Lock(),
            "CLOUD": asyncio.Lock()
        }

    async def add_task(
        self, 
        task_type: str, 
        priority: int, 
        prompt: str, 
        schema: str = "text"
    ) -> Any:
        """Добавление задачи в очередь.
        
        Специалист просто кидает задачу: 'Сделай нарезку с приоритетом 5'.
        
        Args:
            task_type: Тип задачи для маршрутизации.
            priority: Приоритет задачи (меньше = выше приоритет).
            prompt: Промпт для выполнения задачи.
            schema: Формат ответа ('text' или 'json').
            
        Returns:
            Future с результатом выполнения задачи.
        """
        future = asyncio.get_running_loop().create_future()
        
        # Кладем в очередь: (приоритет, время, данные)
        await self.queue.put((priority, asyncio.get_event_loop().time(), {
            "task_type": task_type,
            "prompt": prompt,
            "schema": schema,
            "future": future
        }))
        
        return await future

    async def start_dispatcher(self) -> None:
        """Главный цикл Дирижера."""
        self.logger.info("📡 Дирижер вычислений на посту. Слушаю задачи...")
        
        while self.running:
            try:
                priority, ts, task_data = await self.queue.get()
                
                # Определяем ресурс по типу задачи из конфига
                resource = self.cfg.get('task_routing', {}).get(task_data["task_type"], "GPU_0")
                
                # Запускаем выполнение в фоне, чтобы не блокировать очередь
                asyncio.create_task(self._process_task(resource, task_data))
                self.queue.task_done()
            except asyncio.CancelledError:
                self.logger.info("🛑 Диспетчер остановлен.")
                break
            except Exception as e:
                self.logger.error(f"🚨 Ошибка в диспетчере: {e}")

    async def _process_task(self, resource: str, task_data: dict) -> None:
        """Выполнение задачи с динамической маршрутизацией по тех. карте.
        
        Args:
            resource: Имя ресурса для выполнения (GPU_0, GPU_1, CLOUD, etc.).
            task_data: Данные задачи (тип, промпт, schema, future).
        """
        task_type = task_data["task_type"]
        query = task_data["prompt"]
        
        # 🤖 1. Спрашиваем у Технолога карту для этой задачи
        route_card = self.technologist.get_routing_card(task_type)
        
        # Если для задачи есть тех. карта — запускаем конвейер
        if route_card:
            self.logger.info(f"🎭 Дирижер запускает тех. карту для: {task_type}")
            current_context: Any = query  # Входные данные
            
            try:
                for stage in route_card:
                    actor = stage["actor"]
                    action = stage["action"]
                    self.logger.info(f"⚙️ Шаг {stage['step']}: Передача в {actor} -> {action}")
                    
                    # 🚦 Динамический вызов специалистов
                    if actor == "navigator" and action == "build_strategy":
                        current_context = await self.navigator.build_search_strategy(current_context)
                        
                    elif actor == "librarian" and action == "fetch_context":
                        # Ищем по всем 3 запросам из навигатора
                        all_docs: List = []
                        all_metas: List = []
                        for sub_query in current_context:
                            results = self.lib.get_search_context(sub_query, n_results=2)
                            if results.get('documents'):
                                all_docs.extend(results['documents'])
                                all_metas.extend(results['metadatas'])
                        current_context = {"documents": all_docs, "metadatas": all_metas}
                        
                    elif actor == "reporter" and action == "compile_final":
                        current_context = await self.reporter.compile_brief(query, current_context)

                # Завершаем задачу, отдаем результат
                task_data["future"].set_result(current_context)
                
            except Exception as e:
                self.logger.error(f"🚨 Брак на линии {task_type}: {e}")
                task_data["future"].set_exception(e)
            return

        # ⚙️ Базовый вызов одиночных LLM (если карты нет)
        async def _execute() -> None:
            try:
                # 📡 Вызываем Шлюз, передавая ему вычисленный ресурс
                response = await self.gateway.ask_via_resource(
                    resource=resource,
                    prompt=task_data["prompt"],
                    schema=task_data["schema"]
                )
                task_data["future"].set_result(response)
            except Exception as e:
                task_data["future"].set_exception(e)

        # Логика "Тяжелой артиллерии": лочим сразу обе карты
        if resource == "GPU_ALL":
            async with self.locks["GPU_0"], self.locks["GPU_1"], self.locks["GPU_ALL"]:
                await _execute()
        else:
            # Для обычной задачи лочим только целевую карту
            async with self.locks[resource]:
                await _execute()

    def stop(self) -> None:
        """Остановка диспетчера."""
        self.running = False
        self.logger.info("🛑 Получена команда остановки.")

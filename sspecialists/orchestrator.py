import asyncio
import time
import logging
from pathlib import Path

class ComputeOrchestrator:
    """#S_EN: [ORCHESTRATOR] Дирижер вычислений.
    Управляет очередью задач и распределяет их по ресурсам (GPU_0, GPU_1, CLOUD) [CHUNKING]."""
    
    def __init__(self, gateway):
        self.gateway = gateway
        # Берем конфиг прямо из шлюза
        self.cfg = gateway.cfg
        self.logger = logging.getLogger("mcp_may.orchestrator")
        
        # 🚦 Единая приоритетная очередь
        self.queue = asyncio.PriorityQueue()
        self.running = True
        
        # Блокировщики ресурсов (чтобы задачи на одной карте не шли одновременно)
        self.locks = {
            "GPU_0": asyncio.Lock(),
            "GPU_1": asyncio.Lock(),
            "GPU_ALL": asyncio.Lock(),
            "CLOUD": asyncio.Lock()
        }

    async def add_task(self, task_type: str, priority: int, prompt: str, schema: str = "text") -> asyncio.Future:
        """Специалист просто кидает задачу: 'Сделай нарезку с приоритетом 5' [CHUNKING]."""
        future = asyncio.get_running_loop().create_future()
        
        # Кладем в очередь: (приоритет, время, данные)
        await self.queue.put((priority, time.time(), {
            "task_type": task_type,
            "prompt": prompt,
            "schema": schema,
            "future": future
        }))
        
        return await future

    async def start_dispatcher(self):
        """Главный цикл Дирижера [CHUNKING]."""
        self.logger.info("📡 Дирижер вычислений на посту. Слушаю задачи...")
        
        while self.running:
            priority, ts, task_data = await self.queue.get()
            
            # Определяем ресурс по типу задачи из конфига
            resource = self.cfg.get('task_routing', {}).get(task_data["task_type"], "GPU_0")
            
            # Запускаем выполнение в фоне, чтобы не блокировать очередь
            asyncio.create_task(self._process_task(resource, task_data))
            self.queue.task_done()

    async def _process_task(self, resource: str, task_data: dict):
        """Выполнение задачи с блокировкой конкретного ресурса."""
        
        async def _execute():
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
                await _execute()import asyncio
import time
import logging
from pathlib import Path

class ComputeOrchestrator:
    """#S_EN: [ORCHESTRATOR] Дирижер вычислений.
    Управляет очередью задач и распределяет их по ресурсам (GPU_0, GPU_1, CLOUD) [CHUNKING]."""
    
    def __init__(self, gateway):
        self.gateway = gateway
        # Берем конфиг прямо из шлюза
        self.cfg = gateway.cfg
        self.logger = logging.getLogger("mcp_may.orchestrator")
        
        # 🚦 Единая приоритетная очередь
        self.queue = asyncio.PriorityQueue()
        self.running = True
        
        # Блокировщики ресурсов (чтобы задачи на одной карте не шли одновременно)
        self.locks = {
            "GPU_0": asyncio.Lock(),
            "GPU_1": asyncio.Lock(),
            "GPU_ALL": asyncio.Lock(),
            "CLOUD": asyncio.Lock()
        }

    async def add_task(self, task_type: str, priority: int, prompt: str, schema: str = "text") -> asyncio.Future:
        """Специалист просто кидает задачу: 'Сделай нарезку с приоритетом 5' [CHUNKING]."""
        future = asyncio.get_running_loop().create_future()
        
        # Кладем в очередь: (приоритет, время, данные)
        await self.queue.put((priority, time.time(), {
            "task_type": task_type,
            "prompt": prompt,
            "schema": schema,
            "future": future
        }))
        
        return await future

    async def start_dispatcher(self):
        """Главный цикл Дирижера [CHUNKING]."""
        self.logger.info("📡 Дирижер вычислений на посту. Слушаю задачи...")
        
        while self.running:
            priority, ts, task_data = await self.queue.get()
            
            # Определяем ресурс по типу задачи из конфига
            resource = self.cfg.get('task_routing', {}).get(task_data["task_type"], "GPU_0")
            
            # Запускаем выполнение в фоне, чтобы не блокировать очередь
            asyncio.create_task(self._process_task(resource, task_data))
            self.queue.task_done()

    async def _process_task(self, resource: str, task_data: dict):
        """Выполнение задачи с блокировкой конкретного ресурса."""
        
        async def _execute():
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

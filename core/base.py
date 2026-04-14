"""
#S_EN: [CORE] Базовые классы и протоколы для специалистов.

Этот модуль содержит:
1. Базовый класс BaseSpecialist для всех специалистов
2. Протоколы для типизации
3. Общие исключения проекта
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Protocol
from pathlib import Path


class SpecialistProtocol(Protocol):
    """Протокол для всех специалистов."""
    
    logger: logging.Logger
    gateway: Any
    
    async def initialize(self) -> bool:
        """Инициализация специалиста."""
        ...
    
    def get_status(self) -> Dict[str, Any]:
        """Получение статуса специалиста."""
        ...


class BaseSpecialist(ABC):
    """#S_EN: [BASE] Базовый класс для всех специалистов.
    
    Предоставляет общую функциональность:
    - Логирование с префиксом имени специалиста
    - Доступ к шлюзу (gateway)
    - Базовая инициализация
    - Управление состоянием
    
    Пример использования:
        class Librarian(BaseSpecialist):
            async def initialize(self) -> bool:
                await super().initialize()
                # дополнительная инициализация
                return True
            
            def process_file(self, path: Path) -> Dict[str, Any]:
                self.logger.info(f"Обработка файла: {path}")
                # логика обработки
                return {"status": "success"}
    """
    
    def __init__(
        self, 
        name: str, 
        gateway: Optional[Any] = None,
        log_level: int = logging.INFO
    ):
        """Инициализация базового специалиста.
        
        Args:
            name: Имя специалиста (для логгера).
            gateway: Шлюз для доступа к конфигурации и LLM.
            log_level: Уровень логирования.
        """
        self.name = name
        self.gateway = gateway
        self._initialized = False
        
        # Настройка логгера с уникальным именем
        self.logger = logging.getLogger(f"mcp_may.specialist.{name}")
        self.logger.setLevel(log_level)
        
        # Конфигурация (если есть gateway)
        self.cfg = gateway.cfg if gateway else {}
    
    async def initialize(self) -> bool:
        """Базовая инициализация специалиста.
        
        Переопределите этот метод в наследниках для дополнительной инициализации.
        
        Returns:
            True если инициализация успешна.
        """
        self.logger.info(f"🔧 Специалист {self.name} инициализирован")
        self._initialized = True
        return True
    
    @property
    def is_initialized(self) -> bool:
        """Проверка состояния инициализации."""
        return self._initialized
    
    def get_status(self) -> Dict[str, Any]:
        """Получение статуса специалиста.
        
        Returns:
            Словарь со статусом и информацией о специалисте.
        """
        return {
            "name": self.name,
            "initialized": self._initialized,
            "has_gateway": self.gateway is not None,
            "log_level": self.logger.level
        }
    
    def process(self, *args, **kwargs) -> Any:
        """Основной метод обработки.
        
        Может быть переопределен в наследниках для единого интерфейса.
        По умолчанию возвращает NotImplementedError.
        
        Returns:
            Результат обработки.
            
        Raises:
            NotImplementedError: Если метод не переопределен.
        """
        raise NotImplementedError("Метод process может быть реализован в наследнике при необходимости")


class BaseAsyncSpecialist(BaseSpecialist):
    """#S_EN: [BASE_ASYNC] Базовый класс для асинхронных специалистов.
    
    Расширяет BaseSpecialist асинхронными методами.
    
    Пример использования:
        class Scanner(BaseAsyncSpecialist):
            async def process(self, directory: str) -> Dict[str, Any]:
                self.logger.info(f"Сканирование: {directory}")
                # асинхронная логика
                return {"files": []}
    """
    
    async def process_async(self, *args, **kwargs) -> Any:
        """Асинхронный метод обработки по умолчанию.
        
        Вызывает синхронный process в executor если он определен.
        
        Returns:
            Результат обработки.
            
        Raises:
            NotImplementedError: Если process не реализован.
        """
        import asyncio
        
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, 
            lambda: self.process(*args, **kwargs)
        )


# Общие исключения проекта

class MayException(Exception):
    """Базовое исключение проекта May."""
    pass


class ConfigurationError(MayException):
    """Ошибка конфигурации."""
    pass


class SpecialistError(MayException):
    """Ошибка в работе специалиста."""
    
    def __init__(self, specialist_name: str, message: str):
        self.specialist_name = specialist_name
        super().__init__(f"[{specialist_name}] {message}")


class FileNotFoundError(MayException):
    """Файл не найден."""
    pass


class SessionError(MayException):
    """Ошибка сессии."""
    pass

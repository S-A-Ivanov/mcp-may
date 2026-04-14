"""
#S_EN: [CORE] Модуль ядра проекта.

Экспортирует основные компоненты ядра:
- Базовые классы для специалистов
- Утилиты файловой системы
- Менеджер сессий
- LLM Gateway для работы с языковыми моделями
"""

from core.base import (
    BaseSpecialist,
    BaseAsyncSpecialist,
    SpecialistProtocol,
    MayException,
    ConfigurationError,
    SpecialistError,
    FileNotFoundError,
    SessionError
)

from core.filesystem import FileSystemUtils, fs_utils

from core.session import (
    SessionManager,
    SessionContext,
    get_session_manager,
    session_manager
)

from core.llm_gateway import LLMBasicGateway


__all__ = [
    # Базовые классы
    'BaseSpecialist',
    'BaseAsyncSpecialist',
    'SpecialistProtocol',
    
    # Исключения
    'MayException',
    'ConfigurationError',
    'SpecialistError',
    'FileNotFoundError',
    'SessionError',
    
    # Файловая система
    'FileSystemUtils',
    'fs_utils',
    
    # Сессии
    'SessionManager',
    'SessionContext',
    'get_session_manager',
    'session_manager',
    
    # LLM Gateway (базовый класс)
    'LLMBasicGateway'
]

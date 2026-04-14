# Рефакторинг: Выделение ядра проекта (core)

## 📋 Обзор изменений

В ходе анализа проекта было выявлено дублирование кода и отсутствие единой архитектуры для специалистов. 
Для решения этих проблем создана новая директория `core/` с базовыми компонентами.

## 🎯 Проблемы решенные рефакторингом

### 1. Дублирование кода работы с файлами
**Было:** Каждый специалист реализовывал свои методы:
- Чтение файлов (`open()`, `read()`)
- Запись YAML (`yaml.dump()`)
- Сканирование директорий (`rglob()`)
- Вычисление хэшей (`hashlib.md5()`)

**Стало:** Единый класс `FileSystemUtils` в `core/filesystem.py`

### 2. Отсутствие базового класса для специалистов
**Было:** 10 различных классов специалистов без общей базы:
```python
class Librarian:
    def __init__(self, collection, inventory, gateway, director, orchestrator):
        ...

class Reporter:
    def __init__(self, gateway):
        ...

class Navigator:
    def __init__(self, gateway, orchestrator):
        ...
```

**Стало:** Базовые классы `BaseSpecialist` и `BaseAsyncSpecialist` в `core/base.py`

### 3. Менеджер сессий в неправильном месте
**Было:** `specialists/session.py` (552 строки) - логика инфраструктуры среди бизнес-логики

**Стало:** `core/session.py` - инфраструктурный компонент в ядре

## 📁 Структура core/

```
core/
├── __init__.py          # Экспорт основных компонентов
├── base.py              # Базовые классы специалистов
├── filesystem.py        # Утилиты работы с файлами
└── session.py           # Менеджер сессий
```

## 🔧 Компоненты ядра

### 1. BaseSpecialist (base.py)

Базовый класс для всех специалистов с общей функциональностью:

```python
from core import BaseSpecialist

class Librarian(BaseSpecialist):
    def __init__(self, collection, inventory, gateway, director, orchestrator):
        super().__init__(name="librarian", gateway=gateway)
        self.collection = collection
        self.inventory = inventory
        # остальная инициализация
    
    def process(self, *args, **kwargs):
        # бизнес-логика специалиста
        pass
```

**Преимущества:**
- ✅ Единое логирование (`self.logger`)
- ✅ Доступ к конфигурации (`self.cfg`)
- ✅ Управление состоянием (`is_initialized`)
- ✅ Стандартный интерфейс (`process()`)

### 2. BaseAsyncSpecialist (base.py)

Расширение для асинхронных специалистов:

```python
from core import BaseAsyncSpecialist

class Scanner(BaseAsyncSpecialist):
    async def process(self, directory: str):
        self.logger.info(f"Сканирование: {directory}")
        # асинхронная логика
        return {"files": []}
```

### 3. FileSystemUtils (filesystem.py)

Централизованная работа с файловой системой:

```python
from core import fs_utils

# Чтение файла
content = fs_utils.get_file_content(path)

# Запись YAML
fs_utils.save_yaml(path, data)

# Сканирование директории
files, scanned, skipped = fs_utils.scan_directory("/project", max_files=50)

# Хэш файла
file_hash = fs_utils.get_file_hash(path)
```

**Методы:**
- `normalize_path()` - нормализация путей
- `get_file_hash()` - вычисление хэшей (MD5, SHA256)
- `get_file_content()` - чтение файлов
- `read_lines()` - построчное чтение
- `scan_directory()` - сканирование с фильтрацией
- `save_yaml()` / `load_yaml()` - работа с YAML
- `ensure_directory()` - создание директорий
- `is_readable()` / `is_writable()` - проверка прав

### 4. SessionManager (session.py)

Изоляция сессий для параллельной работы:

```python
from core import get_session_manager

session_mgr = get_session_manager()

# Запуск очистки сессий
await session_mgr.start_cleanup_task()

# Параллельная работа с разными директориями
async with session_mgr.create_session("/projectA") as s1:
    files_a = await session_mgr.scan_files(s1.session_id)
    
async with session_mgr.create_session("/projectB") as s2:
    files_b = await session_mgr.scan_files(s2.session_id)

# Статистика
stats = session_mgr.get_session_stats()
print(f"Активных сессий: {stats['active_sessions']}")
```

**Возможности:**
- ✅ Полная изоляция контекстов
- ✅ Параллельная работа нескольких сессий
- ✅ Автоматическая очистка устаревших сессий
- ✅ Кэширование информации о файлах
- ✅ Потокобезопасность (asyncio.Lock)

## 📊 Сравнение "До" и "После"

### До рефакторинга

| Файл | Строк | Дублирование |
|------|-------|--------------|
| specialists/librarian.py | 306 | 6 блоков try/except для файлов |
| specialists/session.py | 552 | Инфраструктура в specialists |
| specialists/scanner.py | 47 | Логика сканирования |
| **Всего дублирования** | ~200 строк |多处 |

### После рефакторинга

| Файл | Строк | Статус |
|------|-------|--------|
| core/filesystem.py | 271 | ✅ Централизованно |
| core/session.py | 329 | ✅ Перемещено из specialists |
| core/base.py | 177 | ✅ Новый базовый класс |
| specialists/librarian.py | ~250 | ⏳待 рефакторинга |

**Экономия:** ~200-300 строк дублирования будет устранено при полном рефакторинге

## 🚀 План миграции

### Этап 1:已完成 ✅
- [x] Создание `core/` директории
- [x] Перемещение `FileManager` → `FileSystemUtils`
- [x] Перемещение `SessionManager` в `core/session.py`
- [x] Создание `BaseSpecialist`
- [x] Тестирование компонентов

### Этап 2: Следующие шаги
- [ ] Обновить `specialists/librarian.py`:
  ```python
  from core import BaseSpecialist, fs_utils
  
  class Librarian(BaseSpecialist):
      def __init__(self, collection, inventory, gateway, director, orchestrator):
          super().__init__(name="librarian", gateway=gateway)
          self.collection = collection
          self.fs = fs_utils  # вместо создания FileManager
  ```

- [ ] Обновить `specialists/scanner.py`:
  ```python
  from core import fs_utils
  
  def scan_directory(directory: str, max_files: int = 100):
      return fs_utils.scan_directory(directory, max_files)
  ```

- [ ] Обновить `tools.py`:
  ```python
  from core import get_session_manager, fs_utils
  
  session_manager = get_session_manager()
  file_manager = fs_utils  # переименовать использование
  ```

### Этап 3: Дополнительные улучшения
- [ ] Создать `core/config.py` для работы с конфигурацией
- [ ] Создать `core/exceptions.py` с проектными исключениями
- [ ] Добавить `core/logging_utils.py` для настройки логирования
- [ ] Рефакторинг остальных специалистов на базу `BaseSpecialist`

## ✅ Тесты

Все компоненты протестированы:

```bash
# Тест базовых классов
python -c "from core import BaseSpecialist; print('✅ OK')"

# Тест файловой системы
python -c "from core import fs_utils; print('✅ OK')"

# Тест сессий
python -c "from core import get_session_manager; print('✅ OK')"

# Полный тест
python DOCS/test_core_all.py
```

## 📝 Рекомендации

1. **Не переносите в core:**
   - Бизнес-логику специалистов
   - Специфичные зависимости (chromadb, transformers)
   - Тяжелые вычисления

2. **Переносите в core:**
   - Общие утилиты
   - Базовые абстракции
   - Инфраструктурные компоненты
   - Протоколы и типы

3. **Именование:**
   - `core/` - ядро проекта (инфраструктура)
   - `specialists/` - бизнес-логика (агенты)
   - `utils/` - простые функции (альтернатива core для легковесных утилит)

## 🔗 Связанные документы

- `DOCS/SESSION_AND_FILE_MANAGER.md` - документация менеджера сессий
- `DOCS/CODE_QUALITY_IMPROVEMENTS.md` - общие улучшения кода

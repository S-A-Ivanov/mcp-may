# Рефакторинг Gateway: Перенос в core

## 📊 Обзор изменений

### Созданные файлы
- **`core/llm_gateway.py`** (348 строк) - Базовый класс `LLMBasicGateway` для работы с LLM

### Обновленные файлы
- **`specialists/gateway.py`** (272 строки, было ~260) - Теперь наследуется от `LLMBasicGateway`
- **`core/__init__.py`** - Добавлен экспорт `LLMBasicGateway`

## 🎯 Архитектурные решения

### 1. Разделение ответственности

#### `core/llm_gateway.py` (Инфраструктура)
- **`LLMBasicGateway`** - Абстрактный базовый класс
  - Загрузка конфигурации
  - Настройка путей для логирования
  - Методы логирования запросов/ответов (`_log_request`, `_log_response`, `_log_hf_download`)
  - Базовая реализация `_call_ollama()`, `_call_openai()`
  - Получение эмбеддингов (`get_embeddings()`)
  - Загрузка из HuggingFace (`get_from_hf()`)
  - Асинхронные вызовы (`ask_via_resource()`)
  - Абстрактный метод `_call_provider()` для реализации в наследниках

#### `specialists/gateway.py` (Бизнес-логика)
- **`UniversalGateway(LLMBasicGateway)`** - Конкретная реализация
  - Реализация `_call_provider()` для маршрутизации по провайдерам
  - Переопределение `ask()` для кастомного логирования TARGET
  - Переопределение `get_from_hf()` для специфичного формата логов
  - Переопределение `get_embeddings()` для использования секции 'embeddings'

### 2. Преимущества новой архитектуры

✅ **Уменьшение дублирования**: Базовая логика вынесена в core
✅ **Расширяемость**: Легко добавить новые реализации шлюза
✅ **Тестируемость**: Можно тестировать базовый класс отдельно
✅ **Соблюдение SOLID**: 
   - Single Responsibility: core - инфраструктура, specialists - бизнес-логика
   - Open/Closed: открыто для расширения через наследование
   - Liskov Substitution: UniversalGateway полностью заменяем вместо базового класса

## 📈 Статистика

```
До рефакторинга:
- specialists/gateway.py: ~260 строк (вся логика в одном классе)

После рефакторинга:
- core/llm_gateway.py: 348 строк (базовая инфраструктура)
- specialists/gateway.py: 272 строки (бизнес-логика + наследование)
- Итого: 620 строк
- Переиспользуемый код в core: ~350 строк
```

## 🔧 Использование

### Базовый класс (только для наследования)

```python
from core.llm_gateway import LLMBasicGateway

# Нельзя создать экземпляр напрямую (абстрактный класс)
# gw = LLMBasicGateway()  # TypeError!
```

### Конкретная реализация

```python
from specialists.gateway import UniversalGateway

gw = UniversalGateway()

# Синхронный запрос
response = gw.ask(specialist="librarian", prompt="Обработай файлы")

# Получение эмбеддингов
embedding = gw.get_embeddings("текст для векторизации")

# Загрузка из HuggingFace
file_path = gw.get_from_hf("repo/id", "filename.bin")

# Асинхронный запрос через ресурс
import asyncio
result = await gw.ask_via_resource("gpu_1", "промт")
```

### Наследование для создания своего шлюза

```python
from core.llm_gateway import LLMBasicGateway

class MyCustomGateway(LLMBasicGateway):
    def _call_provider(self, provider, model, prompt, schema, timeout):
        if provider == "my_provider":
            # Кастомная логика
            return self._call_my_provider(model, prompt, schema, timeout)
        return super()._call_provider(provider, model, prompt, schema, timeout)
    
    def _call_my_provider(self, model, prompt, schema, timeout):
        # Реализация вызова моего провайдера
        pass
```

## ✅ Тесты пройдены

```bash
✅ Импорт LLMBasicGateway из core успешен
✅ Импорт UniversalGateway из specialists успешен
✅ UniversalGateway наследуется от LLMBasicGateway: True
✅ Экземпляр UniversalGateway создается корректно
✅ Все методы доступны: ask, get_embeddings, get_from_hf, ask_via_resource, _call_ollama, _call_openai
✅ Абстрактный метод _call_provider() реализован
```

## 🚀 Следующие шаги

1. **Orchestrator**: Аналогично перенести инфраструктурную логику в `core/orchestration.py`
2. **Embeddings**: Вынести `UniversalEmbeddingFunction` в `core/embedding_function.py`
3. **Inventory**: Перенести работу с SQLite в `core/database.py`
4. **Technologist**: Вынести технологические карты в `core/recipes.py`

## 📝 Примечания

- `LLMBasicGateway` является абстрактным классом и не может быть создан напрямую
- Для использования всегда применяйте `UniversalGateway` или создайте свою реализацию
- Функция `get_llm_gateway()` удалена, так как не может создать экземпляр абстрактного класса
- Все существующие вызовы `UniversalGateway` продолжают работать без изменений

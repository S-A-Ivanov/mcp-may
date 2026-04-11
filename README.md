# NeuralVault-May

Agentic RAG (Retrieval-Augmented Generation) система с трёхпроходной индексацией и универсальным шлюзом для управления агентами на базе локальных и облачных LLM.

## 📖 Описание

NeuralVault-May — это продвинутая система, сочетающая RAG с агентным подходом. Она использует трёхпроходную индексацию документов, семантический поиск, автоматическую картографию кода и маршрутизацию задач между различными моделями (Ollama, OpenAI, Cloud).

**Ключевые возможности:**
- 🧠 **Трёхпроходная индексация**: Recon → Semantic → Manifest
- 🔍 **Семантический поиск**: Векторизация через ChromaDB + Ollama embeddings
- 🗺️ **Картографирование**: Автоматическое построение графов связей кода (Mermaid)
- 🎯 **Маршрутизация задач**: Распределение запросов между GPU/Cloud по типу задачи
- 🛠️ **AI Forge**: Зона для генерации и хранения кода

---

## 🏗️ Архитектура

### Агенты системы:

| Агент | Файл | Роль |
|-------|------|------|
| **Architect** | `architect.py` | Структура кода, управление задачами, AI Forge |
| **Cartographer** | `cartographer.py` | Визуализация связей кода (Mermaid graphs) |
| **Librarian** | `librarian.py` | Управление архивом знаний, индексация |
| **Orchestrator** | `orchestrator.py` | Координация агентов и пайплайнов |
| **Scanner** | `scanner.py` | Сканирование файлов проекта |
| **Semantic** | `semantic.py` | Семантическая обработка запросов |
| **Gateway** | `gateway.py` | Универсальный шлюз к провайдерам LLM |

### Утилиты:

| Компонент | Файл | Назначение |
|-----------|------|------------|
| **Client** | `client.py` | MCP клиент для взаимодействия |
| **Tools** | `tools.py` | Общие инструменты |
| **Transport** | `transport.py` | Транспортный слой |
| **Pipeline Manager** | `pipeline_manager.py` | Управление пайплайнами индексации |
| **Inventory** | `inventory.py` | SQLite инвентарь ресурсов |
| **Embeddings** | `embeddings.py` | Генерация эмбеддингов |
| **Server** | `server_may.py` | MCP сервер |

---

## ⚙️ Конфигурация

Основная конфигурация находится в [`config.yaml`](config.yaml):

```yaml
project:
  name: "NeuralVault-May"
  version: "1.0-ALPHA"

storage:
  db_path: "./data/chroma_db"
  collection_name: "mcp_knowledge"
  chunk_size: 1500

routing:
  embeddings:
    model: "mxbai-embed-large"
  semantic:
    model: "gemma3:12b"
  cartographer:
    model: "deepseek-coder-v2:16b"
```

### Маршрутизация задач:
- `quick_chat` → SYSTEM_GPU (Ollama:11434)
- `text_slicing` → GPU_0 (Ollama:11435)
- `embeddings` → GPU_1 (Ollama:11436)
- `strategic_boss` → CLOUD (OpenRouter/Claude)

---

## 🚀 Быстрый старт

### Требования:
- Python 3.10+
- Ollama (локально) или доступ к OpenAI/OpenRouter
- ChromaDB

### Установка зависимостей:
```bash
pip install chromadb httpx pyyaml mcp
```

### Запуск:
```bash
# Убедитесь, что Ollama запущена
ollama serve

# Запуск основного клиента
python client.py
```

---

## 📁 Структура проекта

```
NeuralVault-May/
├── architect.py           # Агент структуры кода
├── cartographer.py        # Агент картографирования
├── librarian.py           # Агент управления знаниями
├── orchestrator.py        # Координатор
├── scanner.py             # Сканер файлов
├── semantic.py            # Семантический анализ
├── gateway.py             # Универсальный шлюз
├── client.py              # MCP клиент
├── server_may.py          # MCP сервер
├── tools.py               # Инструменты
├── transport.py           # Транспорт
├── pipeline_manager.py    # Менеджер пайплайнов
├── inventory.py           # Инвентарь (SQLite)
├── embeddings.py          # Эмбеддинги
├── config.yaml            # Конфигурация
├── LICENSE                # Лицензия
└── README.md              # Этот файл
```

---

## 🔮 Трёхпроходная индексация

1. **Recon (Разведка)**: Быстрое сканирование структуры проекта
2. **Semantic (Семантика)**: Глубокий анализ с векторизацией
3. **Manifest (Манифест)**: Финальная сборка глобального индекса

---

## 📄 Лицензия

MIT License — см. файл [LICENSE](LICENSE)

---

## 📞 Контакты

Проект находится в активной разработке (ALPHA). Детальная документация будет предоставлена позже.


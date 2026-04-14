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

### Агенты системы (Specialists):

| Агент | Файл | Роль |
|-------|------|------|
| **Orchestrator** | `specialists/orchestrator.py` | Координация агентов и пайплайнов |
| **Librarian** | `specialists/librarian.py` | Управление архивом знаний, трёхпроходная индексация |
| **Semantic** | `specialists/semantic.py` | Семантическая обработка запросов |
| **Scanner** | `specialists/scanner.py` | Сканирование файлов проекта (Recon pass) |
| **Gateway** | `specialists/gateway.py` | Универсальный шлюз к провайдерам LLM (Ollama, OpenAI, Cloud) |
| **Inventory** | `specialists/inventory.py` | SQLite инвентарь ресурсов проекта |
| **Embeddings** | `specialists/embeddings.py` | Генерация эмбеддингов через Ollama |
| **Navigator** | `specialists/navigator.py` | Навигация по кодовой базе |
| **Technologist** | `specialists/technologist.py` | Анализ технологического стека |
| **Reporter** | `specialists/reporter.py` | Генерация отчётов и документации |

### Основные компоненты:

| Компонент | Файл | Назначение |
|-----------|------|------------|
| **Server** | `server_may.py` | MCP сервер |
| **Client** | `client.py` | MCP клиент для взаимодействия |
| **Tools** | `tools.py` | Общие инструменты |
| **Transport** | `transport.py` | Транспортный слой |
| **Config** | `config.yaml` | Конфигурация системы |

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
├── server_may.py          # MCP сервер
├── client.py              # MCP клиент
├── tools.py               # Общие инструменты
├── transport.py           # Транспортный слой
├── config.yaml            # Конфигурация
├── requirements.txt       # Зависимости Python
├── LICENSE                # Лицензия
├── README.md              # Этот файл
│
├── data/
│   └── chroma_db/         # ChromaDB хранилище векторов
│
└── specialists/           # Агенты системы
    ├── orchestrator.py    # Координатор агентов
    ├── librarian.py       # Управление знаниями и индексация
    ├── semantic.py        # Семантическая обработка
    ├── scanner.py         # Сканирование файлов (Recon)
    ├── gateway.py         # Шлюз к LLM провайдерам
    ├── inventory.py       # SQLite инвентарь ресурсов
    ├── embeddings.py      # Генерация эмбеддингов
    ├── navigator.py       # Навигация по коду
    ├── technologist.py    # Анализ технологического стека
    └── reporter.py        # Генерация отчётов
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


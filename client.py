import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

# --- [🛠️] УМНЫЙ ВЫЗОВ ---
async def safe_call(session: ClientSession, tools: list, name: str, args: dict = None):
    if any(t.name == name for t in tools):
        print(f"⟨⚙⟩ Выполняю: {name}...")
        res = await session.call_tool(name, args or {})
        # Извлекаем текст (Мэй всегда отдает TextContent)
        text = res.content[0].text if isinstance(res.content, list) else res.content.text
        print(f"   ⟨✓⟩ Ответ: {text}\n")
        return text
    else:
        print(f"   ⟨!!⟩ Пропуск: {name} (не найден)\n")
        return None

async def main():
    url = "http://localhost:8001/mcp"
    print(f"🌀 Подключение к {url}...")

    try:
        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("✅ Сессия ⟦HEALTHY⟧\n")
                
                # --- 1. СПИСОК ИНСТРУМЕНТОВ ---
                print("🔍 Мэй проверяет свои модули...")
                tools_resp = await session.list_tools()
                available_tools = tools_resp.tools
                

                # --- 0. 📡 ПИНГ (Проверка связи после листинга) ---
                await safe_call(session, available_tools, "ping")
                
                print("🔍 Мэй начинает инвентаризацию проекта...")
                await safe_call(session, available_tools, "scan_directory_tool", {"directory": ".", "max_files": 30})
                #await safe_call(session, available_tools, "get_db_stats")
                #print("🔍 Мэй разобралась с инвентаризацией проекта...")
                
                # 4. 📊 ПРОВЕРКА КАРТОТЕКИ (Статистика)
                print("📊 ПРОВЕРКА КАРТОТЕКИ (Статистика)")
                await safe_call(session, available_tools, "get_db_stats")

 
                # 5. 🔍 СЕМАНТИЧЕСКИЙ ПОИСК
                # Проверим, нашла ли Мэй информацию о самой себе
                print(" 🔍 СЕМАНТИЧЕСКИЙ ПОИСК: 📡 Как организованна очередь задач?")
                await safe_call(session, available_tools, "get_verified_brief", {
                    "query": "Как организованна очередь задач?",
                    "include_gossip": True
                })
                
                # print("📡 Сейчас база данных привязана к директории кода, как нам сделать чтобы база хранилась в сканируемой директории, нужно добавить понятие рабочее пространство?")
                # await safe_call(session, available_tools, "get_verified_brief", {
                #     "query": "Сейчас база данных привязана к директории кода, как нам сделать чтобы база хранилась в сканируемой директории, нужно добавить понятие рабочее пространство?",
                #     "include_gossip": True
                # })


    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main())

import httpx
import json

class OllamaCartographer:
    """#S_EN: [AGENT] Визуализатор связей. Работает через универсальный шлюз."""
    
    def __init__(self, gateway=None): # 👈 Добавляем gateway
        self.gateway = gateway
    

    async def get_mermaid_graph(self, code_chunk: str, filename: str) -> str:
        """Просит нейронку извлечь связи в формате Mermaid."""
        
        prompt = f"""
        Ты — архитектор кода. Проанализируй фрагмент файла {filename} и выведи ТОЛЬКО связи в формате Mermaid.
        Формат: {filename} -- вызывает --> НазваниеФункции
        
        Код:
        {code_chunk}
        
        Выводи только код Mermaid, без лишнего текста.
        """
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(self.url, json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                })
                result = response.json()
                return result.get("response", "").strip()
            except Exception as e:
                return f"⟨!!⟩ Ошибка Ollama: {str(e)}"
            
    async def draw_project_map(self, lib, query: str = "") -> str:
        """Генерация глобальной карты связей."""
        search_query = query if query else "import def class"
        
        # Используем метод библиотекаря для поиска (уже с фиксом типизации)
        results = lib.get_search_context(search_query, n_results=15)
        
        if not results['documents'] or not results['documents'][0]:
            return "🔍 Мэй: Архив пуст, нечего картографировать."

        context = "\n---\n".join(results['documents'][0])
        
        print(f"🗺️ Мэй: Передаю данные Картографу ({self.model_name})...")
        mermaid_code = await self.get_mermaid_graph(context, "Project_Scope")
        
        # Чистим Mermaid от лишних тегов
        clean_mermaid = mermaid_code.replace("```mermaid", "").replace("```", "").strip()
        
        return f"⟦⚓⟧ КАРТА СВЯЗЕЙ (Semantic_View):\n\n```mermaid\ngraph TD\n{clean_mermaid}\n```"

    async def draw_file_map(self, collection, filename: str) -> str:
        """Генерация карты конкретного файла."""
        results = collection.get(where={"file_path": filename})
        
        if not results['documents']:
            return f"🔍 Файл {filename} не найден в архиве Мэй."
        
        full_code = "\n".join(results['documents'])
        
        print(f"🗺️ Мэй передает код {filename} Картографу...")
        mermaid_code = await self.get_mermaid_graph(full_code, filename)
        clean_mermaid = mermaid_code.replace("```mermaid", "").replace("```", "").strip()
        
        return f"⟦⚓⟧ КАРТА СВЯЗЕЙ ДЛЯ {filename}:\n\n```mermaid\ngraph TD\n{clean_mermaid}\n```"

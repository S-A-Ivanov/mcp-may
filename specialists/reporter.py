import logging

logger = logging.getLogger("mcp_may.reporter")

class Reporter:
    def __init__(self, gateway):
        self.gateway = gateway # Наш UniversalGateway

    async def compile_brief(self, query: str, raw_atoms: dict) -> str:
        """
        #S_EN: [PROCESS] Читает сырые атомы из БД и формирует связный отчет для Босса.
        """
        if not raw_atoms.get('documents') or not raw_atoms['documents'][0]:
            return f"Мэй докладывает: по запросу '{query}' в архивах ничего не найдено."

        # Собираем все найденные куски в один текст для анализа
        context_to_analyze = ""
        documents = raw_atoms['documents'][0]
        metadatas = raw_atoms['metadatas'][0]

        for i, (doc, meta) in enumerate(zip(documents, metadatas)):
            context_to_analyze += f"--- Фрагмент {i+1} ---\n"
            context_to_analyze += f"Суть (Index): {doc}\n"
            context_to_analyze += f"Файл (Unit): {meta.get('file_path', 'N/A')}\n"
            context_to_analyze += f"Код/Контент:\n{meta.get('original_content', meta.get('code', 'N/A'))}\n\n"

        # 🇬🇧 Промпт на английском с тегами #S_EN, но с жестким требованием ответа на русском
        prompt = f"""
        #S_EN: [IDENTIFICATION]: You are 'May's Senior Analyst' (Референт).
        #S_EN: [TASK]: Summarize the raw data found in the database into a clean, structured brief for The Boss.
        #S_EN: [CONSTRAINT]: You must write the final response strictly in RUSSIAN.
        
        #S_EN: [INPUT_QUERY]: "{query}"
        
        #S_EN: [INPUT_DATA]:
        {context_to_analyze}
        
        #S_EN: [INSTRUCTION]:
        Analyze the raw code snippets and summaries provided above. 
        Create a coherent, high-level summary that answers the Boss's query.
        Explain how these pieces fit together in plain text. Do not just list the files.
        
        #S_EN: [OUTPUT_LANGUAGE]: Russian (RU).
        """

        try: 
            # 1. Вызываем LLM через шлюз под ролью 'reporter'
            result = self.gateway.ask(
                specialist="reporter", 
                prompt=prompt, 
                schema="text"
            )
            summary = result.get('response', "Ошибка при формировании сводки.")
            
            # 🔥 АНТИ-DEEPSEEK ОЧИСТКА:
            # Вырезаем теги <think>...</think> и всё, что между ними
            import re
            summary = re.sub(r"<think>.*?</think>\n?", "", summary, flags=re.DOTALL)
            
            # Убираем лишние пробелы по краям, которые могли остаться
            summary = summary.strip()
            
            return f"⟦⚓⟧ ОТЧЕТ МЭЙ ДЛЯ БОССА\n{summary}"
                    
        except Exception as e:
            logger.error(f"Ошибка Референта при суммаризации: {e}")
            return f"Ошибка при подготовке отчета: {str(e)}"



    # async def create_verified_brief(self, lib, query: str, include_gossip: bool = False) -> str:
    #     """
    #     #S_EN: [PROCESS] Главная точка входа для генерации сводного отчета.
    #     Мэй забирает сырые данные из Теневого Индекса, а Референт пишет отчет Боссу.
    #     """
    #     # 1. Запрашиваем сырые данные у Библиотекаря (lib)
    #     results = lib.get_search_context(query, n_results=5)

    #     # Проверка на пустоту (ChromaDB возвращает пустые списки, если ничего не найдено)
    #     if not results.get('documents') or not results['documents'][0]:
    #         return f"🔍 По теме '{query}' в архивах Мэй ничего не найдено."

    #     # 2. Подготавливаем структуру для суммаризации
    #     raw_atoms = {
    #         "documents": results['documents'][0],
    #         "metadatas": results['metadatas'][0]
    #     }
        
    #     print("📝 Референт изучает собранные Мэй материалы...")
        
    #     # 3. Вызываем наш метод суммаризации по английскому промпту (результат будет на русском)
    #     summary = await self.compile_brief(query, raw_atoms)
        
    #     return f"⟦⚓⟧ ОТЧЕТ МЭЙ ДЛЯ БОССА\n{summary}"


    async def create_verified_brief(self, lib, query: str, include_gossip: bool = False) -> str:
        """
        #S_EN: [PROCESS] Главная точка входа для генерации сводного отчета.
        Мэй забирает сырые данные из Теневого Индекса, а Референт пишет отчет Боссу.
        """
        # 1. Запрашиваем сырые данные у Библиотекаря (lib)
        results = lib.get_search_context(query, n_results=5)

        # 2. Проверка на пустоту (Безопасно проверяем вложенные списки)
        if not results.get('documents') or not results['documents'][0]:
            return f"🔍 По теме '{query}' в архивах Мэй ничего не найдено."

        # 3. Принудительно достаем первый уровень (т.к. запрос у нас один)
        # Теперь doc_list — это список строк, а meta_list — это список словарей!
        doc_list = results['documents'][0]
        meta_list = results['metadatas'][0]
        
        print(f"📝 Референт изучает собранные Мэй материалы (Найдено атомов: {len(doc_list)})...")
        
        # 4. Собираем чистый текст для суммаризации прямо здесь, чтобы не путать типы
        context_to_analyze = ""
        for i, (doc, meta) in enumerate(zip(doc_list, meta_list)):
            # Защита: проверяем, что meta — это действительно словарь
            if not isinstance(meta, dict):
                meta = {}
                
            context_to_analyze += f"--- Фрагмент {i+1} ---\n"
            context_to_analyze += f"Суть (Index): {doc}\n"
            context_to_analyze += f"Файл (Unit): {meta.get('file_path', meta.get('header', 'Unknown'))}\n"
            
            # Достаем код
            code_content = meta.get('original_content', meta.get('code', 'N/A'))
            context_to_analyze += f"Код/Контент:\n{code_content}\n\n"
            
        # 5. Промпт для Босса
        prompt = f"""
        #S_EN: [IDENTIFICATION]: You are 'May's Senior Analyst' (Референт).
        #S_EN: [TASK]: Summarize the raw data found in the database into a clean, structured brief for The Boss.
        #S_EN: [CONSTRAINT]: You must write the final response strictly in RUSSIAN.
        
        #S_EN: [INPUT_QUERY]: "{query}"
        
        #S_EN: [INPUT_DATA]:
        {context_to_analyze}
        
        #S_EN: [INSTRUCTION]:
        Analyze the raw code snippets and summaries provided above. 
        Create a coherent, high-level summary that answers the Boss's query.
        Explain how these pieces fit together in plain text. Do not just list the files.
        
        #S_EN: [OUTPUT_LANGUAGE]: Russian (RU).
        """

        try:
            # 6. Вызываем LLM через шлюз под ролью 'reporter'
            result = self.gateway.ask(
                specialist="reporter", 
                prompt=prompt, 
                schema="text"
            )
            summary = result.get('response', "Ошибка при формировании сводки.")
            
            return f"⟦⚓⟧ ОТЧЕТ МЭЙ ДЛЯ БОССА\n{summary}"
            
        except Exception as e:
            self.logger.error(f"Ошибка Референта при суммаризации: {e}")
            return f"Ошибка при подготовке отчета: {str(e)}"

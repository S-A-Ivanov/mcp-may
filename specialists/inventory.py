import sqlite3
import time
import hashlib

class FileInventory:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._init_db()

    def _init_db(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                filepath TEXT PRIMARY KEY,
                hash TEXT,
                model TEXT,   -- [📂] Кем сделаны векторы?   
                timestamp REAL
            )
        """)
        self.conn.commit()

    def get_hash(self, text: str) -> str:
        """#S_EN: [LOGIC] MD5 Fingerprint."""
        return hashlib.md5(text.encode('utf-8', errors='ignore')).hexdigest()

    def is_changed(self, filepath, current_hash):
        """#S_EN: [GUARD] Сравнение хешей в SQLite."""
        self.cursor.execute("SELECT hash FROM inventory WHERE filepath = ?", (filepath,))
        row = self.cursor.fetchone()
        return not (row and row[0] == current_hash)

    def update(self, filepath, current_hash):
        """#S_EN: [LOGIC] Запись в картотеку."""
        self.cursor.execute(
            "INSERT OR REPLACE INTO inventory (filepath, hash, timestamp) VALUES (?, ?, ?)",
            (filepath, current_hash, time.time())
        )
        self.conn.commit()

    def get_file_meta(self, filepath: str) -> dict:
        """#S_EN: [GUARD] Получение хэша и метаданных файла из SQLite."""
        self.cursor.execute(
            "SELECT hash, timestamp FROM inventory WHERE filepath = ?", 
            (filepath,)
        )
        row = self.cursor.fetchone()
        
        if row:
            return {
                "hash": row[0],
                "timestamp": row[1]
            }
        return {}

    def check_and_update(self, filepath: str, full_path: str) -> bool:
        """
        #S_EN: [GUARD] Считывает файл, вычисляет хэш и сверяет с базой.
        Возвращает True, если файл изменился или новый.
        """
        import hashlib
        import os
        
        if not os.path.exists(full_path):
            return False
            
        # 1. Считаем хэш файла на диске
        hasher = hashlib.md5()
        with open(full_path, 'rb') as f:
            hasher.update(f.read())
        current_hash = hasher.hexdigest()
        
        # 2. Проверяем в SQLite
        self.cursor.execute("SELECT hash FROM inventory WHERE filepath = ?", (filepath,))
        row = self.cursor.fetchone()
        
        # 3. Если хэш совпадает — возвращаем False (не изменился)
        if row and row[0] == current_hash:
            return False
            
        # 4. Если изменился — обновляем запись в базе и возвращаем True
        self.update(filepath, current_hash)
        return True

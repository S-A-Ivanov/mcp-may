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


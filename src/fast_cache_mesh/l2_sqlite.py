import json
import sqlite3
import time
from typing import Any, Optional, Tuple


class L2SQLiteCache:
    """Persistent local disk cache with automatic serialization and TTL."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._shared_conn = sqlite3.connect(db_path, check_same_thread=False) if db_path == ":memory:" else None
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._shared_conn is not None:
            return self._shared_conn
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        conn = self._get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_store (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    expires_at REAL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expires ON cache_store(expires_at)")
            conn.commit()
        finally:
            if self._shared_conn is None:
                conn.close()

    def get(self, key: str) -> Tuple[bool, Any]:
        now = time.time()
        conn = self._get_connection()
        try:
            cur = conn.execute(
                "SELECT value, expires_at FROM cache_store WHERE key = ?", (key,)
            )
            row = cur.fetchone()
            if not row:
                return False, None

            val_json, exp = row
            if exp is not None and now > exp:
                conn.execute("DELETE FROM cache_store WHERE key = ?", (key,))
                conn.commit()
                return False, None

            return True, json.loads(val_json)
        finally:
            if self._shared_conn is None:
                conn.close()

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        exp = (time.time() + ttl) if ttl else None
        val_json = json.dumps(value)
        conn = self._get_connection()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO cache_store (key, value, expires_at) VALUES (?, ?, ?)",
                (key, val_json, exp),
            )
            conn.commit()
        finally:
            if self._shared_conn is None:
                conn.close()

    def delete(self, key: str) -> None:
        conn = self._get_connection()
        try:
            conn.execute("DELETE FROM cache_store WHERE key = ?", (key,))
            conn.commit()
        finally:
            if self._shared_conn is None:
                conn.close()

    def clear(self) -> None:
        conn = self._get_connection()
        try:
            conn.execute("DELETE FROM cache_store")
            conn.commit()
        finally:
            if self._shared_conn is None:
                conn.close()

# src/coordinator/repositories/base_repository.py
# Base repository class with common database functionality

from __future__ import annotations
from typing import Optional, List, Dict, Any
import sqlite3
import threading
import os
from datetime import datetime

class BaseRepository:
    """Base repository class providing common database operations."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or os.environ.get("COORDINATOR_DB_PATH", "chats.db")
        self._lock = threading.Lock()

    def _conn(self) -> sqlite3.Connection:
        """Create a new database connection with row factory."""
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
        return conn

    def _execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """
        Execute a query with automatic connection management.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Cursor object with query results
        """
        with self._lock:
            conn = self._conn()
            cur = conn.cursor()
            cur.execute(query, params)
            conn.commit()
            conn.close()
            return cur

    def _fetchone_dict(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """
        Execute query and fetch one result as dictionary.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Dictionary with query results or None
        """
        with self._lock:
            conn = self._conn()
            cur = conn.cursor()
            cur.execute(query, params)
            row = cur.fetchone()
            conn.close()

            if not row:
                return None
            return dict(row)

    def _fetchall_list(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        Execute query and fetch all results as list of dictionaries.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            List of dictionaries with query results
        """
        with self._lock:
            conn = self._conn()
            cur = conn.cursor()
            cur.execute(query, params)
            rows = cur.fetchall()
            conn.close()

            return [dict(r) for r in rows]

    @staticmethod
    def _now() -> str:
        """Get current UTC timestamp in ISO format."""
        return datetime.utcnow().isoformat(timespec="seconds") + "Z"

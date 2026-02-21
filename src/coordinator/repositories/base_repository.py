# src/coordinator/repositories/base_repository.py
# Base repository class with common database functionality

from __future__ import annotations
from typing import Optional, List, Dict, Any
import sqlite3
import threading
import os
from datetime import datetime
from .db_adapter import DatabaseAdapter, SQLiteAdapter


def utc_now_iso() -> str:
    """Return current UTC time as ``YYYY-MM-DDTHH:MM:SSZ`` string."""
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


class BaseRepository:
    """Base repository class providing common database operations via adapter pattern."""

    def __init__(self, db_path: Optional[str] = None, adapter: Optional[DatabaseAdapter] = None):
        """
        Initialize repository with database adapter.

        Args:
            db_path: Path to database file (SQLite default)
            adapter: Optional database adapter instance (defaults to SQLiteAdapter)
        """
        self._db_path = db_path or os.environ.get("COORDINATOR_DB_PATH", "data/chats.db")
        self._lock = threading.Lock()

        # Use provided adapter or default to SQLiteAdapter
        self._adapter = adapter if adapter is not None else SQLiteAdapter(self._db_path)

    def _conn(self) -> sqlite3.Connection:
        """
        Get a database connection via the adapter.

        Returns:
            Database connection object
        """
        return self._adapter.get_connection()

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
            return self._adapter.execute(query, params)

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
            return self._adapter.fetchone(query, params)

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
            return self._adapter.fetchall(query, params)

    @staticmethod
    def _now() -> str:
        """Get current UTC timestamp in ISO format."""
        return utc_now_iso()

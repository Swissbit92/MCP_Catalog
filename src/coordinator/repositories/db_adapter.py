# src/coordinator/repositories/db_adapter.py
"""Database adapter abstraction layer for multi-database support."""

from __future__ import annotations
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any, List, Dict, Optional, Tuple
import sqlite3
from sqlalchemy import create_engine, pool


class DatabaseAdapter(ABC):
    """Abstract base class for database adapters."""

    @abstractmethod
    def get_connection(self):
        """
        Get a database connection.

        Returns:
            Database connection object
        """
        pass

    @abstractmethod
    def execute(self, query: str, params: tuple = ()) -> Any:
        """
        Execute a query and return the cursor.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Cursor object with query results
        """
        pass

    @abstractmethod
    def fetchone(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """
        Execute query and fetch one result as dictionary.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Dictionary with query results or None
        """
        pass

    @abstractmethod
    def fetchall(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        Execute query and fetch all results as list of dictionaries.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            List of dictionaries with query results
        """
        pass

    @abstractmethod
    def close(self):
        """Close database connection and cleanup resources."""
        pass


class SQLiteAdapter(DatabaseAdapter):
    """SQLite database adapter with connection pooling."""

    # Class-level engine cache (keyed by database path)
    _engines = {}
    _engine_lock = None

    def __init__(self, db_path: str):
        """
        Initialize SQLite adapter.

        Args:
            db_path: Path to SQLite database file
        """
        import threading

        if SQLiteAdapter._engine_lock is None:
            SQLiteAdapter._engine_lock = threading.Lock()

        self.db_path = db_path

    @classmethod
    def _get_engine(cls, db_path: str):
        """
        Get or create SQLAlchemy engine with connection pooling.

        Engines are cached per database path, allowing multiple databases
        to coexist with separate connection pools.

        Args:
            db_path: Path to SQLite database file

        Returns:
            SQLAlchemy Engine instance with connection pool configured
        """
        with cls._engine_lock:
            if db_path not in cls._engines:
                cls._engines[db_path] = create_engine(
                    f"sqlite:///{db_path}",
                    poolclass=pool.QueuePool,
                    pool_size=5,  # Number of connections to keep in pool
                    max_overflow=10,  # Maximum additional connections beyond pool_size
                    pool_pre_ping=True,  # Verify connections before use
                    connect_args={"check_same_thread": False}  # SQLite thread safety
                )
            return cls._engines[db_path]

    def get_connection(self) -> sqlite3.Connection:
        """
        Get a database connection from the connection pool.

        Returns:
            sqlite3.Connection object with row factory and foreign keys enabled
        """
        # Get fresh connection from pool each time
        engine = self._get_engine(self.db_path)
        fairy = engine.raw_connection()
        
        # CRITICAL: SQLAlchemy returns a _ConnectionFairy wrapper, not the actual connection
        # We need to unwrap it to get the real sqlite3.Connection where row_factory works
        conn = fairy.connection if hasattr(fairy, 'connection') else fairy
        
        # CRITICAL: Set row_factory BEFORE any execute() calls
        # (execute creates internal cursor that captures current row_factory)
        conn.row_factory = sqlite3.Row
        
        # Now safe to execute PRAGMA
        conn.execute("PRAGMA foreign_keys = ON")

        return conn

    @contextmanager
    def _managed_connection(self):
        """
        Context manager that holds the SQLAlchemy fairy alive for the duration of a query.

        Without this, get_connection() drops the fairy immediately after extracting the
        raw sqlite3.Connection. CPython then calls fairy.__del__() which returns the
        checkout to the pool — but the raw conn is still in use. The pool can hand out
        the same underlying connection to another caller, causing a double-use race.

        Yields:
            Tuple of (fairy, conn) where fairy is the _ConnectionFairy keeping the pool
            slot reserved and conn is the raw sqlite3.Connection with row_factory set.
        """
        engine = self._get_engine(self.db_path)
        fairy = engine.raw_connection()
        try:
            conn = fairy.connection if hasattr(fairy, 'connection') else fairy
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            yield fairy, conn
        finally:
            fairy.close()

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """
        Execute a query and return the cursor.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Cursor object with query results
        """
        with self._managed_connection() as (fairy, conn):
            cur = conn.cursor()
            cur.execute(query, params)
            conn.commit()
            return cur

    def fetchone(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """
        Execute query and fetch one result as dictionary.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Dictionary with query results or None
        """
        with self._managed_connection() as (fairy, conn):
            cur = conn.cursor()
            cur.execute(query, params)
            row = cur.fetchone()

        if not row:
            return None

        return dict(row)

    def fetchall(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        Execute query and fetch all results as list of dictionaries.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            List of dictionaries with query results
        """
        with self._managed_connection() as (fairy, conn):
            cur = conn.cursor()
            cur.execute(query, params)
            rows = cur.fetchall()

        return [dict(r) for r in rows]

    def close(self):
        """Close database connection."""
        # No longer caching connections, so nothing to close
        pass

# tests/test_server.py
# Unit tests for FastAPI server endpoints

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from coordinator.server import app

@pytest.fixture
def client():
    """Test client for FastAPI app."""
    return TestClient(app)

@pytest.fixture
def mock_db():
    """Mock database operations."""
    with patch('coordinator.server._DB_LOCK'), \
         patch('coordinator.server._conn') as mock_conn, \
         patch('coordinator.server._init_db'):
        mock_cursor = MagicMock()
        mock_conn.return_value.cursor.return_value = mock_cursor
        mock_conn.return_value.__enter__ = MagicMock(return_value=mock_conn.return_value)
        mock_conn.return_value.__exit__ = MagicMock(return_value=None)
        yield mock_cursor

class TestSessionAPI:
    """Test session management endpoints."""

    def test_list_sessions(self, client, mock_db):
        """Test listing chat sessions for a persona."""
        # Mock database response
        mock_db.fetchall.return_value = [
            {
                'id': 'session_123',
                'persona_key': 'gojo',
                'title': 'Test Chat',
                'created_at': '2025-01-07T10:00:00Z',
                'updated_at': '2025-01-07T10:30:00Z',
                'message_count': 5
            }
        ]

        response = client.get("/sessions?persona_key=gojo")
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert len(data["sessions"]) == 1
        assert data["sessions"][0]["id"] == "session_123"

    def test_create_session(self, client, mock_db):
        """Test creating a new chat session."""
        session_data = {
            "persona_key": "gojo",
            "title": "New Chat"
        }

        response = client.post("/sessions", json=session_data)
        assert response.status_code == 200
        data = response.json()
        assert data["persona_key"] == "gojo"
        assert "id" in data
        assert "created_at" in data

    def test_get_session(self, client, mock_db):
        """Test retrieving a chat session with messages."""
        # Mock session data
        mock_db.fetchone.side_effect = [
            # Session query result
            {
                'id': 'session_123',
                'persona_key': 'gojo',
                'title': 'Test Chat',
                'created_at': '2025-01-07T10:00:00Z',
                'updated_at': '2025-01-07T10:30:00Z',
                'message_count': 2
            }
        ]
        # Mock messages data
        mock_db.fetchall.return_value = [
            {
                'id': 'msg_001',
                'role': 'user',
                'content': 'Hello',
                'timestamp': '2025-01-07T10:00:00Z',
                'latency_ms': None
            },
            {
                'id': 'msg_002',
                'role': 'assistant',
                'content': 'Hi there!',
                'timestamp': '2025-01-07T10:00:05Z',
                'latency_ms': 1500
            }
        ]

        response = client.get("/sessions/session_123")
        assert response.status_code == 200
        data = response.json()
        assert "session" in data
        assert "messages" in data
        assert data["session"]["id"] == "session_123"
        assert len(data["messages"]) == 2

    def test_get_session_not_found(self, client, mock_db):
        """Test retrieving a non-existent session."""
        mock_db.fetchone.return_value = None

        response = client.get("/sessions/nonexistent")
        assert response.status_code == 404
        assert "Session not found" in response.json()["detail"]

    def test_update_session(self, client, mock_db):
        """Test updating a session title."""
        update_data = {"title": "Updated Title"}

        response = client.put("/sessions/session_123", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["title"] == "Updated Title"

    def test_delete_session(self, client, mock_db):
        """Test deleting a chat session."""
        # Mock session exists
        mock_db.fetchone.return_value = {'id': 'session_123'}

        response = client.delete("/sessions/session_123")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True

    def test_delete_session_not_found(self, client, mock_db):
        """Test deleting a non-existent session."""
        mock_db.fetchone.return_value = None

        response = client.delete("/sessions/nonexistent")
        assert response.status_code == 404

    def test_add_message(self, client, mock_db):
        """Test adding a message to a session."""
        # Mock session exists
        mock_db.fetchone.return_value = {'id': 'session_123'}

        message_data = {
            "role": "user",
            "content": "Hello world",
            "ts": "2025-01-07T10:00:00Z",
            "latency_ms": None
        }

        response = client.post("/sessions/session_123/messages", json=message_data)
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "message_id" in data

    def test_add_message_session_not_found(self, client, mock_db):
        """Test adding a message to a non-existent session."""
        mock_db.fetchone.return_value = None

        message_data = {"role": "user", "content": "Hello"}

        response = client.post("/sessions/nonexistent/messages", json=message_data)
        assert response.status_code == 404

class TestExportImportAPI:
    """Test export/import functionality."""

    @patch('coordinator.server.get_persona_card')
    def test_export_session(self, mock_get_persona, client, mock_db):
        """Test exporting a chat session."""
        # Mock persona data
        mock_get_persona.return_value = {
            "key": "gojo",
            "display_name": "Gojo Satoru",
            "style": "Confident Sorcerer"
        }

        # Mock session and messages data (same as get_session test)
        mock_db.fetchone.side_effect = [
            {
                'id': 'session_123',
                'persona_key': 'gojo',
                'title': 'Test Chat',
                'created_at': '2025-01-07T10:00:00Z',
                'updated_at': '2025-01-07T10:30:00Z',
                'message_count': 2
            }
        ]
        mock_db.fetchall.return_value = [
            {
                'id': 'msg_001',
                'role': 'user',
                'content': 'Hello',
                'timestamp': '2025-01-07T10:00:00Z',
                'latency_ms': None
            }
        ]

        response = client.get("/sessions/session_123/export")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "1.0"
        assert "persona" in data
        assert "session" in data
        assert "messages" in data
        assert data["persona"]["key"] == "gojo"

    @patch('coordinator.server.get_persona_card')
    def test_import_session(self, mock_get_persona, client, mock_db):
        """Test importing a chat session."""
        # Mock persona exists
        mock_get_persona.return_value = {"key": "gojo", "display_name": "Gojo Satoru"}

        import_data = {
            "data": {
                "version": "1.0",
                "exported_at": "2025-01-07T11:00:00Z",
                "app_version": "1.0.0",
                "persona": {
                    "key": "gojo",
                    "display_name": "Gojo Satoru"
                },
                "session": {
                    "id": "session_123",
                    "persona_key": "gojo",
                    "title": "Imported Chat",
                    "created_at": "2025-01-07T10:00:00Z",
                    "updated_at": "2025-01-07T10:30:00Z",
                    "message_count": 1
                },
                "messages": [
                    {
                        "id": "msg_001",
                        "role": "user",
                        "content": "Hello",
                        "timestamp": "2025-01-07T10:00:00Z",
                        "latency_ms": None
                    }
                ]
            },
            "create_new_session": True
        }

        response = client.post("/sessions/import", json=import_data)
        if response.status_code != 200:
            print(f"Error response: {response.json()}")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "session_id" in data

    def test_import_invalid_data(self, client):
        """Test importing invalid data."""
        # This will fail Pydantic validation since required fields are missing
        invalid_data = {"data": {"version": "1.0"}, "create_new_session": True}

        response = client.post("/sessions/import", json=invalid_data)
        assert response.status_code == 422  # Pydantic validation error

    @patch('coordinator.server.get_persona_card')
    def test_import_unknown_persona(self, mock_get_persona, client):
        """Test importing with unknown persona."""
        mock_get_persona.return_value = None  # Persona not found

        import_data = {
            "data": {
                "version": "1.0",
                "exported_at": "2025-01-07T11:00:00Z",
                "app_version": "1.0.0",
                "persona": {"key": "unknown"},
                "session": {
                    "id": "session_123",
                    "persona_key": "unknown",
                    "title": "Test",
                    "created_at": "2025-01-07T10:00:00Z",
                    "updated_at": "2025-01-07T10:30:00Z",
                    "message_count": 0
                },
                "messages": []
            },
            "create_new_session": True
        }

        response = client.post("/sessions/import", json=import_data)
        if response.status_code != 400:
            print(f"Unexpected response: {response.status_code} - {response.json()}")
        assert response.status_code == 400
        error_detail = response.json()["detail"]
        assert "not found" in error_detail or "Invalid import data structure" in error_detail

class TestChatAPI:
    """Test chat functionality."""

    @patch('coordinator.server.get_persona_card')
    @patch('coordinator.server.LC_OllamaClient')
    def test_chat_with_session(self, mock_client_class, mock_get_persona, client, mock_db):
        """Test chatting with automatic session saving."""
        # Mock persona and LLM client
        mock_get_persona.return_value = {"key": "gojo"}
        mock_client = MagicMock()
        mock_client.complete.return_value = "Hello from Gojo!"
        mock_client_class.return_value = mock_client

        # Mock session exists
        mock_db.fetchone.return_value = {'persona_key': 'gojo'}

        chat_data = {
            "persona": "gojo",
            "history": [],
            "message": "Hi Gojo"
        }

        response = client.post("/sessions/session_123/chat", json=chat_data)
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert data["answer"] == "Hello from Gojo!"

    def test_chat_with_session_not_found(self, client, mock_db):
        """Test chatting with non-existent session."""
        mock_db.fetchone.return_value = None

        chat_data = {"persona": "gojo", "history": [], "message": "Hi"}

        response = client.post("/sessions/nonexistent/chat", json=chat_data)
        assert response.status_code == 404

if __name__ == "__main__":
    pytest.main([__file__])
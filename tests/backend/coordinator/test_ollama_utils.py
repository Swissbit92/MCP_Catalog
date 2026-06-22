"""
Unit tests for src/coordinator/ollama_utils.py

Coverage targets:
  - list_local_models() — success, empty models list, missing 'name', HTTP error, connection error
  - assert_model_available() — model present, model not found, Ollama unreachable

External calls mocked: requests.get (HTTP layer) — NO live Ollama required.
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
import requests

from src.coordinator.ollama_utils import (
    list_local_models,
    assert_model_available,
    OllamaModelNotFound,
)

BASE_URL = "http://localhost:11434"
TAGS_URL = f"{BASE_URL}/api/tags"


def _mock_response(json_data: dict, status_code: int = 200, raise_for_status=None):
    """Build a mock requests.Response."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data
    if raise_for_status is not None:
        mock_resp.raise_for_status.side_effect = raise_for_status
    else:
        mock_resp.raise_for_status.return_value = None
    return mock_resp


# ============================================================================
# list_local_models
# ============================================================================

class TestListLocalModels:
    def test_returns_model_names_on_success(self):
        payload = {"models": [{"name": "llama3:8b"}, {"name": "mistral:7b"}]}
        with patch("requests.get", return_value=_mock_response(payload)) as mock_get:
            models = list_local_models(BASE_URL)
        mock_get.assert_called_once_with(f"{BASE_URL}/api/tags", timeout=10)
        assert models == ["llama3:8b", "mistral:7b"]

    def test_empty_models_list_returns_empty(self):
        payload = {"models": []}
        with patch("requests.get", return_value=_mock_response(payload)):
            models = list_local_models(BASE_URL)
        assert models == []

    def test_missing_models_key_returns_empty(self):
        payload = {}
        with patch("requests.get", return_value=_mock_response(payload)):
            models = list_local_models(BASE_URL)
        assert models == []

    def test_models_without_name_field_are_filtered(self):
        payload = {"models": [{"name": "good-model"}, {"digest": "abc123"}]}
        with patch("requests.get", return_value=_mock_response(payload)):
            models = list_local_models(BASE_URL)
        assert models == ["good-model"]

    def test_models_with_empty_name_are_filtered(self):
        payload = {"models": [{"name": ""}, {"name": "real-model"}]}
        with patch("requests.get", return_value=_mock_response(payload)):
            models = list_local_models(BASE_URL)
        assert models == ["real-model"]

    def test_raises_on_http_error(self):
        err = requests.exceptions.HTTPError("500 Server Error")
        mock_resp = _mock_response({}, status_code=500, raise_for_status=err)
        with patch("requests.get", return_value=mock_resp):
            with pytest.raises(requests.exceptions.HTTPError):
                list_local_models(BASE_URL)

    def test_raises_on_connection_error(self):
        with patch("requests.get", side_effect=requests.exceptions.ConnectionError("refused")):
            with pytest.raises(requests.exceptions.ConnectionError):
                list_local_models(BASE_URL)

    def test_raises_on_timeout(self):
        with patch("requests.get", side_effect=requests.exceptions.Timeout("timed out")):
            with pytest.raises(requests.exceptions.Timeout):
                list_local_models(BASE_URL)

    def test_trailing_slash_stripped_from_base_url(self):
        payload = {"models": [{"name": "m1"}]}
        with patch("requests.get", return_value=_mock_response(payload)) as mock_get:
            list_local_models(BASE_URL + "/")
        # rstrip('/') should ensure no double-slash
        called_url = mock_get.call_args[0][0]
        assert "//" not in called_url.replace("http://", "http-PLACEHOLDER").replace("https://", "https-PLACEHOLDER")
        assert called_url.endswith("/api/tags")

    def test_none_json_response_treated_as_empty_dict(self):
        """If r.json() returns None (edge case), should return []."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = None
        with patch("requests.get", return_value=mock_resp):
            models = list_local_models(BASE_URL)
        assert models == []

    def test_single_model_returned(self):
        payload = {"models": [{"name": "hf.co/TheDrummer/Magidonia-24B-v4.3-GGUF:Q4_K_M"}]}
        with patch("requests.get", return_value=_mock_response(payload)):
            models = list_local_models(BASE_URL)
        assert len(models) == 1
        assert "Magidonia" in models[0]


# ============================================================================
# assert_model_available
# ============================================================================

class TestAssertModelAvailable:
    def test_does_not_raise_when_model_is_available(self):
        payload = {"models": [{"name": "llama3:8b"}, {"name": "mistral:7b"}]}
        with patch("requests.get", return_value=_mock_response(payload)):
            # Should not raise
            assert_model_available(BASE_URL, "llama3:8b")

    def test_raises_model_not_found_when_missing(self):
        payload = {"models": [{"name": "llama3:8b"}]}
        with patch("requests.get", return_value=_mock_response(payload)):
            with pytest.raises(OllamaModelNotFound) as exc_info:
                assert_model_available(BASE_URL, "missing-model")
        assert "missing-model" in str(exc_info.value)
        assert "ollama pull" in str(exc_info.value)

    def test_model_not_found_hint_includes_available_models(self):
        payload = {"models": [{"name": "llama3:8b"}, {"name": "mistral:7b"}]}
        with patch("requests.get", return_value=_mock_response(payload)):
            with pytest.raises(OllamaModelNotFound) as exc_info:
                assert_model_available(BASE_URL, "nonexistent")
        msg = str(exc_info.value)
        assert "llama3:8b" in msg
        assert "mistral:7b" in msg

    def test_model_not_found_with_no_available_models_no_hint(self):
        payload = {"models": []}
        with patch("requests.get", return_value=_mock_response(payload)):
            with pytest.raises(OllamaModelNotFound) as exc_info:
                assert_model_available(BASE_URL, "ghost-model")
        msg = str(exc_info.value)
        # hint string should be empty (no "Available models:" section)
        assert "Available models:" not in msg

    def test_wraps_connection_error_as_runtime_error(self):
        with patch("requests.get", side_effect=requests.exceptions.ConnectionError("refused")):
            with pytest.raises(RuntimeError) as exc_info:
                assert_model_available(BASE_URL, "some-model")
        msg = str(exc_info.value)
        assert "Could not reach Ollama" in msg
        assert BASE_URL in msg

    def test_wraps_timeout_as_runtime_error(self):
        with patch("requests.get", side_effect=requests.exceptions.Timeout("timeout")):
            with pytest.raises(RuntimeError) as exc_info:
                assert_model_available(BASE_URL, "some-model")
        assert "Could not reach Ollama" in str(exc_info.value)

    def test_wraps_http_error_as_runtime_error(self):
        err = requests.exceptions.HTTPError("503 Service Unavailable")
        mock_resp = _mock_response({}, status_code=503, raise_for_status=err)
        with patch("requests.get", return_value=mock_resp):
            with pytest.raises(RuntimeError) as exc_info:
                assert_model_available(BASE_URL, "some-model")
        assert "Could not reach Ollama" in str(exc_info.value)

    def test_original_error_included_in_runtime_error_message(self):
        original_msg = "Connection refused by localhost"
        with patch("requests.get", side_effect=Exception(original_msg)):
            with pytest.raises(RuntimeError) as exc_info:
                assert_model_available(BASE_URL, "model")
        assert original_msg in str(exc_info.value)

    def test_model_not_found_is_subclass_of_runtime_error(self):
        assert issubclass(OllamaModelNotFound, RuntimeError)

    def test_exact_model_match_required(self):
        """'llama3' should NOT match 'llama3:8b'."""
        payload = {"models": [{"name": "llama3:8b"}]}
        with patch("requests.get", return_value=_mock_response(payload)):
            with pytest.raises(OllamaModelNotFound):
                assert_model_available(BASE_URL, "llama3")

    def test_passes_with_special_characters_in_model_name(self):
        model = "hf.co/TheDrummer/Magidonia-24B-v4.3-GGUF:Q4_K_M"
        payload = {"models": [{"name": model}]}
        with patch("requests.get", return_value=_mock_response(payload)):
            assert_model_available(BASE_URL, model)  # must not raise

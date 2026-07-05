# tests/backend/coordinator/test_web_toolset.py
"""Tests for the ADR-009 W2 generic web toolset: definitions, safesearch clamp,
fetch_url executor."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.coordinator.tools.web_safesearch import clamp_safesearch
from src.coordinator.tools.web_tool_generators import (
    get_extract_tool,
    get_fetch_url_tool,
    get_image_search_tool,
    get_news_search_tool,
    get_video_search_tool,
    get_web_search_tool,
)
from src.coordinator.services.web_fetch_service import fetch_url


# ------------------------------------------------------------ safesearch clamp

class TestSafesearchClamp:
    def test_nsfw_persona_allows_off(self):
        assert clamp_safesearch("off", persona_nsfw=True) == "off"
        assert clamp_safesearch(None, persona_nsfw=True, global_default="off") == "off"

    def test_non_nsfw_persona_floored_at_moderate(self):
        assert clamp_safesearch("off", persona_nsfw=False) == "moderate"
        assert clamp_safesearch(None, persona_nsfw=False, global_default="off") == "moderate"

    def test_clamp_only_tightens_never_loosens(self):
        # strict request stays strict even for nsfw persona.
        assert clamp_safesearch("strict", persona_nsfw=True) == "strict"
        # moderate request stays moderate for nsfw persona (not lowered to off).
        assert clamp_safesearch("moderate", persona_nsfw=True) == "moderate"

    def test_non_nsfw_cannot_be_lowered_by_model(self):
        # even if the model asks for off, a non-nsfw persona gets moderate.
        assert clamp_safesearch("off", persona_nsfw=False) == "moderate"
        assert clamp_safesearch("strict", persona_nsfw=False) == "strict"

    def test_invalid_defaults_to_off_then_clamped(self):
        assert clamp_safesearch("bogus", persona_nsfw=True) == "off"
        assert clamp_safesearch("bogus", persona_nsfw=False) == "moderate"


# ------------------------------------------------------------ tool definitions

class TestWebToolDefinitions:
    def test_all_have_valid_shape(self):
        for factory in (get_web_search_tool, get_fetch_url_tool, get_image_search_tool,
                        get_video_search_tool, get_news_search_tool, get_extract_tool):
            d = factory()
            assert d["type"] == "function"
            fn = d["function"]
            assert fn["name"] and fn["description"]
            assert fn["parameters"]["type"] == "object"

    def test_web_search_params(self):
        props = get_web_search_tool()["function"]["parameters"]["properties"]
        assert set(props) >= {"query", "category", "safesearch", "time_range", "max_results"}
        assert props["safesearch"]["enum"] == ["off", "moderate", "strict"]

    def test_fetch_url_required(self):
        fn = get_fetch_url_tool()["function"]
        assert fn["parameters"]["required"] == ["url"]

    def test_extract_required(self):
        assert get_extract_tool()["function"]["parameters"]["required"] == [
            "source", "instruction"]


# ------------------------------------------------------------ fetch_url

class TestFetchUrl:
    def _resp(self, body: str, status: int = 200):
        r = MagicMock()
        r.content = body.encode("utf-8")
        r.encoding = "utf-8"
        r.raise_for_status = MagicMock()
        if status >= 400:
            r.raise_for_status.side_effect = httpx.HTTPStatusError(
                "err", request=MagicMock(), response=MagicMock())
        return r

    def _patch_client(self, resp):
        client = MagicMock()
        client.__enter__.return_value = client
        client.__exit__.return_value = False
        client.get.return_value = resp
        return patch("httpx.Client", return_value=client)

    def test_empty_url(self):
        assert fetch_url("").startswith("ERROR")

    def test_extracts_readable_text(self):
        html = "<html><body><article><h1>Title</h1><p>Hello world content here.</p>" \
               "</article><script>junk()</script></body></html>"
        with self._patch_client(self._resp(html)):
            out = fetch_url("https://example.com", mode="text")
        assert "Hello world content here." in out
        assert "junk()" not in out

    def test_raw_mode_returns_html(self):
        html = "<html><body><p>raw</p></body></html>"
        with self._patch_client(self._resp(html)):
            out = fetch_url("https://example.com", mode="raw")
        assert "<p>raw</p>" in out

    def test_prefixes_scheme(self):
        html = "<html><body><p>ok text long enough to extract properly.</p></body></html>"
        client = MagicMock()
        client.__enter__.return_value = client
        client.__exit__.return_value = False
        client.get.return_value = self._resp(html)
        with patch("httpx.Client", return_value=client):
            fetch_url("example.com", mode="text")
        called_url = client.get.call_args[0][0]
        assert called_url.startswith("https://example.com")

    def test_fetch_failure_returns_error_sentinel(self):
        client = MagicMock()
        client.__enter__.return_value = client
        client.__exit__.return_value = False
        client.get.side_effect = httpx.ConnectError("refused")
        with patch("httpx.Client", return_value=client):
            out = fetch_url("https://down.example")
        assert out.startswith("ERROR")

    def test_output_is_capped(self):
        big = "<html><body><article>" + ("word " * 50000) + "</article></body></html>"
        with self._patch_client(self._resp(big)):
            out = fetch_url("https://example.com", mode="text")
        assert len(out) <= 20_000

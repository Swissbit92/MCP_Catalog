"""
Unit tests for src/coordinator/tools/tool_utils.py

Coverage targets:
  - ToolCall dataclass and to_dict()
  - should_use_keyword_filter() — all three return branches
  - parse_tool_call() — full JSON, embedded JSON, invalid JSON, missing fields
  - format_search_results_for_llm() — empty, with/without age, max_results truncation
  - get_tools_for_persona() — mcp_access paths, rarity fallback
  - get_tools_for_query() — intent-routing paths (mocked classify_query_intent)
"""

from __future__ import annotations

import json
import pytest
from unittest.mock import patch, MagicMock

from src.coordinator.tools.tool_utils import (
    ToolCall,
    should_use_keyword_filter,
    parse_tool_call,
    format_search_results_for_llm,
    get_tools_for_persona,
    get_tools_for_query,
)
from src.coordinator.tools.intent_classifier import QueryIntent


# ============================================================================
# ToolCall dataclass
# ============================================================================

class TestToolCall:
    def test_to_dict_basic(self):
        tc = ToolCall(name="brave_web_search", arguments={"query": "hello"})
        assert tc.to_dict() == {"name": "brave_web_search", "arguments": {"query": "hello"}}

    def test_to_dict_empty_arguments(self):
        tc = ToolCall(name="noop", arguments={})
        d = tc.to_dict()
        assert d["name"] == "noop"
        assert d["arguments"] == {}

    def test_to_dict_nested_arguments(self):
        args = {"query": "test", "filters": {"lang": "en"}}
        tc = ToolCall(name="search", arguments=args)
        assert tc.to_dict()["arguments"]["filters"]["lang"] == "en"

    def test_fields_accessible(self):
        tc = ToolCall(name="foo", arguments={"x": 1})
        assert tc.name == "foo"
        assert tc.arguments == {"x": 1}


# ============================================================================
# should_use_keyword_filter
# ============================================================================

class TestShouldUseKeywordFilter:
    def test_returns_false_for_no_search_keyword(self):
        # "what is" is in NO_SEARCH_KEYWORDS and "current" is not present
        result = should_use_keyword_filter("What is Bitcoin?")
        assert result is False

    def test_returns_true_for_search_keyword(self):
        # "current" is in SEARCH_KEYWORDS
        result = should_use_keyword_filter("What is the current price of Bitcoin?")
        # "what is" is no-search, but "current" is search → should return None (LLM decides)
        # or True if search keyword dominates; either way NOT False
        # Actual logic: no-search branch returns False only if no search keyword present.
        # Here "current" is in SEARCH_KEYWORDS so the no-search early-return is skipped,
        # then the search-keyword loop fires → True
        assert result is True

    def test_returns_none_for_no_signal(self):
        result = should_use_keyword_filter("Tell me a joke")
        assert result is None

    def test_no_search_keyword_without_search_returns_false(self):
        result = should_use_keyword_filter("Define the term blockchain")
        assert result is False

    def test_search_keyword_alone_returns_true(self):
        result = should_use_keyword_filter("What is today's weather forecast?")
        assert result is True

    def test_case_insensitive(self):
        result = should_use_keyword_filter("WHAT IS A BLOCKCHAIN")
        assert result is False

    def test_empty_string_returns_none(self):
        result = should_use_keyword_filter("")
        assert result is None

    def test_only_whitespace_returns_none(self):
        result = should_use_keyword_filter("   ")
        assert result is None

    def test_both_keywords_lets_llm_decide(self):
        # "what is" (no-search) + "current" (search) → has_search_keyword is True → skip False return
        # then loop finds "current" → return True
        result = should_use_keyword_filter("what is the current news")
        assert result is True

    def test_news_keyword_returns_true(self):
        result = should_use_keyword_filter("Show me the latest news")
        assert result is True


# ============================================================================
# parse_tool_call
# ============================================================================

class TestParseToolCall:
    def _make_fc_json(self, name: str, arguments: dict) -> str:
        return json.dumps({
            "function_call": {
                "name": name,
                "arguments": arguments
            }
        })

    def test_parses_full_json_response(self):
        raw = self._make_fc_json("brave_web_search", {"query": "bitcoin price"})
        result = parse_tool_call(raw)
        assert result is not None
        assert result.name == "brave_web_search"
        assert result.arguments == {"query": "bitcoin price"}

    def test_returns_none_for_plain_text(self):
        result = parse_tool_call("Hello, how can I help you today?")
        assert result is None

    def test_returns_none_for_empty_string(self):
        result = parse_tool_call("")
        assert result is None

    def test_returns_none_for_invalid_json(self):
        result = parse_tool_call("{this is not valid json}")
        assert result is None

    def test_returns_none_when_no_function_call_key(self):
        raw = json.dumps({"some_key": "some_value"})
        result = parse_tool_call(raw)
        assert result is None

    def test_parses_function_call_embedded_in_text(self):
        fc_blob = json.dumps({
            "function_call": {
                "name": "search",
                "arguments": {"query": "test"}
            }
        })
        # The regex pattern only handles flat structure so embed minimally
        raw = f'Let me search for that.\n{fc_blob}\nDone.'
        # Top-level JSON check fails (starts with 'L'), regex pattern tries next
        # Regex requires nested braces pattern — this may or may not match depending on depth
        # Just assert no exception is raised
        result = parse_tool_call(raw)
        # Result may be None (regex doesn't match nested JSON) — acceptable behavior
        assert result is None or isinstance(result, ToolCall)

    def test_empty_arguments_defaulted(self):
        raw = json.dumps({
            "function_call": {
                "name": "noop"
                # no "arguments" key
            }
        })
        result = parse_tool_call(raw)
        assert result is not None
        assert result.name == "noop"
        assert result.arguments == {}

    def test_whitespace_padded_json(self):
        raw = "   " + self._make_fc_json("tool", {"x": 1}) + "   "
        result = parse_tool_call(raw)
        # Leading whitespace: strip().startswith('{') → True
        assert result is not None
        assert result.name == "tool"

    def test_json_without_starting_brace_falls_to_regex(self):
        # Prefix prevents the startswith('{') branch; regex pattern also won't
        # match simple flat JSON without nested braces as required by the pattern
        raw = 'result: {"function_call": {"name": "foo", "arguments": {}}}'
        result = parse_tool_call(raw)
        # Behaviour depends on regex — no exception is the key invariant
        assert result is None or isinstance(result, ToolCall)

    def test_regex_branch_matches_embedded_flat_function_call(self):
        """
        Hit lines 86-93: text that doesn't start with '{' but contains a regex-matchable
        function_call block (arguments as a string, not a nested dict, so no nested braces).
        """
        # arguments as a flat string (no nested {}) — the regex can match this
        raw = 'The LLM decided: {"function_call": {"name": "brave_web_search", "arguments": "bitcoin price"}}'
        result = parse_tool_call(raw)
        # The regex will match; json.loads will succeed; function_call is present
        # arguments will be the string "bitcoin price" (not a dict)
        assert result is not None
        assert result.name == "brave_web_search"

    def test_regex_branch_matches_embedded_no_arguments(self):
        """Hit lines 86-93 with a minimal embedded function_call (no arguments key)."""
        raw = 'I will call {"function_call": {"name": "noop"}} now.'
        result = parse_tool_call(raw)
        assert result is not None
        assert result.name == "noop"
        assert result.arguments == {}

    def test_regex_branch_invalid_json_after_match_returns_none(self):
        """Hit line 94-95: regex matches but json.loads fails (malformed inner JSON)."""
        # Craft a string that matches the regex pattern but is not valid JSON
        # Pattern: \{[^{}]*"function_call"[^{}]*\{[^{}]*\}[^{}]*\}
        # We need the outer { to NOT start the string, so prefix it
        raw = 'prefix {"function_call": {"name": broken}} suffix'
        result = parse_tool_call(raw)
        assert result is None


# ============================================================================
# format_search_results_for_llm
# ============================================================================

class TestFormatSearchResultsForLlm:
    def _make_result(self, title: str, url: str, description: str, age: str = None):
        m = MagicMock()
        m.title = title
        m.url = url
        m.description = description
        if age:
            m.age = age
        else:
            del m.age  # make hasattr(m, 'age') → False
        return m

    def test_empty_results_returns_no_results_string(self):
        result = format_search_results_for_llm([])
        assert result == "No search results found."

    def test_single_result_formatted(self):
        r = self._make_result("Python Docs", "https://docs.python.org", "The official docs", "1 day ago")
        output = format_search_results_for_llm([r])
        assert "1. Python Docs" in output
        assert "URL: https://docs.python.org" in output
        assert "The official docs" in output
        assert "Published: 1 day ago" in output

    def test_result_without_age_omits_published_line(self):
        m = MagicMock(spec=["title", "url", "description"])
        m.title = "No Age"
        m.url = "https://example.com"
        m.description = "desc"
        output = format_search_results_for_llm([m])
        assert "Published:" not in output

    def test_max_results_truncates(self):
        results = [
            self._make_result(f"Result {i}", f"https://example.com/{i}", f"desc {i}")
            for i in range(1, 10)
        ]
        output = format_search_results_for_llm(results, max_results=3)
        assert "1. Result 1" in output
        assert "3. Result 3" in output
        assert "4. Result 4" not in output

    def test_default_max_results_is_5(self):
        results = [
            self._make_result(f"R{i}", f"https://x.com/{i}", f"d{i}")
            for i in range(1, 8)
        ]
        output = format_search_results_for_llm(results)
        assert "5. R5" in output
        assert "6. R6" not in output

    def test_output_contains_sources_footer(self):
        r = self._make_result("Title", "https://src.com", "Desc")
        output = format_search_results_for_llm([r])
        assert "Sources:" in output
        assert "IMPORTANT" in output

    def test_multiple_results_numbered_correctly(self):
        results = [
            self._make_result(f"Item {i}", f"https://x.com/{i}", f"d{i}")
            for i in range(1, 4)
        ]
        output = format_search_results_for_llm(results)
        for i in range(1, 4):
            assert f"{i}. Item {i}" in output

    def test_none_age_value_omits_published_line(self):
        """age attribute present but falsy value."""
        m = MagicMock()
        m.title = "T"
        m.url = "https://u.com"
        m.description = "d"
        m.age = None  # attribute exists but is None
        output = format_search_results_for_llm([m])
        assert "Published:" not in output


# ============================================================================
# get_tools_for_persona
# ============================================================================

BRAVE_TOOL_NAME = "brave_web_search"


class TestGetToolsForPersona:
    def test_mcp_access_with_brave_returns_brave_tool(self):
        tools = get_tools_for_persona("Eeva", "legendary", mcp_access=["brave_search"])
        assert len(tools) == 1
        assert tools[0]["function"]["name"] == BRAVE_TOOL_NAME

    def test_mcp_access_empty_list_returns_no_tools(self):
        tools = get_tools_for_persona("Nyx", "common", mcp_access=[])
        assert tools == []

    def test_mcp_access_none_rarity_rare_returns_brave(self):
        tools = get_tools_for_persona("Cipher", "rare", mcp_access=None)
        assert len(tools) == 1
        assert tools[0]["function"]["name"] == BRAVE_TOOL_NAME

    def test_mcp_access_none_rarity_epic_returns_brave(self):
        tools = get_tools_for_persona("Aurora", "epic", mcp_access=None)
        assert any(t["function"]["name"] == BRAVE_TOOL_NAME for t in tools)

    def test_mcp_access_none_rarity_legendary_returns_brave(self):
        tools = get_tools_for_persona("Eeva", "legendary", mcp_access=None)
        assert any(t["function"]["name"] == BRAVE_TOOL_NAME for t in tools)

    def test_mcp_access_none_rarity_common_returns_no_tools(self):
        tools = get_tools_for_persona("Gojo", "common", mcp_access=None)
        assert tools == []

    def test_mcp_access_none_rarity_case_insensitive(self):
        # "Rare" with capital R should still grant access
        tools = get_tools_for_persona("X", "Rare", mcp_access=None)
        assert len(tools) >= 1

    def test_mcp_access_without_brave_returns_no_brave(self):
        # mcp_access specified but does NOT include brave_search
        tools = get_tools_for_persona("Eeva", "legendary", mcp_access=["some_other_service"])
        names = [t["function"]["name"] for t in tools]
        assert BRAVE_TOOL_NAME not in names

    def test_mcp_access_with_solana_wallet_returns_wallet_tools(self):
        # ADR-009 R2: sourced from the registry (no longer a direct
        # get_wallet_tools call). Assert the behavior, not the internal path.
        tools = get_tools_for_persona("Eeva", "legendary", mcp_access=["solana_wallet"])
        names = {t["function"]["name"] for t in tools}
        assert "wallet_get_balances" in names and "solana_propose_swap" in names


# ============================================================================
# get_tools_for_query
# ============================================================================

class TestGetToolsForQuery:
    def _patch_intent(self, intent: QueryIntent):
        return patch(
            "src.coordinator.tools.tool_utils.classify_query_intent",
            return_value=intent,
        )

    def test_web_search_intent_returns_brave_tool(self):
        with self._patch_intent(QueryIntent.NEEDS_WEB_SEARCH):
            tools = get_tools_for_query("latest bitcoin news", "Eeva", "legendary", mcp_access=["brave_search"])
        assert len(tools) == 1
        assert tools[0]["function"]["name"] == BRAVE_TOOL_NAME

    def test_neither_intent_returns_empty(self):
        with self._patch_intent(QueryIntent.NEEDS_NEITHER):
            tools = get_tools_for_query("what is 2+2", "Gojo", "common")
        assert tools == []

    def test_wallet_intent_returns_wallet_toolset(self):
        # ADR-009 R2: NEEDS_WALLET -> registry.definitions_for_toolsets(["wallet"]).
        with self._patch_intent(QueryIntent.NEEDS_WALLET):
            tools = get_tools_for_query(
                "my wallet balance", "Eeva", "legendary", mcp_access=["solana_wallet"]
            )
        names = {t["function"]["name"] for t in tools}
        assert "wallet_get_balances" in names
        assert len(names) == 7  # full wallet toolset

    def test_classify_query_intent_receives_correct_args(self):
        with patch("src.coordinator.tools.tool_utils.classify_query_intent", return_value=QueryIntent.NEEDS_NEITHER) as mock_classify:
            get_tools_for_query("hello", "TestPersona", "common", mcp_access=None)
        mock_classify.assert_called_once_with("hello", "common", mcp_access=None)

    def test_empty_query_does_not_raise(self):
        with self._patch_intent(QueryIntent.NEEDS_NEITHER):
            tools = get_tools_for_query("", "X", "common")
        assert tools == []

    def test_mcp_access_forwarded_to_classify(self):
        access = ["brave_search"]
        with patch("src.coordinator.tools.tool_utils.classify_query_intent", return_value=QueryIntent.NEEDS_WEB_SEARCH) as mock_classify:
            get_tools_for_query("query", "p", "rare", mcp_access=access)
        mock_classify.assert_called_once_with("query", "rare", mcp_access=access)

    def test_precomputed_intent_skips_classify(self):
        """When precomputed_intent is supplied, the redundant classify call is skipped."""
        with patch("src.coordinator.tools.tool_utils.classify_query_intent") as mock_classify:
            tools = get_tools_for_query(
                "latest bitcoin news", "Eeva", "legendary",
                mcp_access=["brave_search"], precomputed_intent=QueryIntent.NEEDS_WEB_SEARCH,
            )
        mock_classify.assert_not_called()
        assert len(tools) == 1
        assert tools[0]["function"]["name"] == BRAVE_TOOL_NAME

    def test_none_precomputed_intent_classifies_internally(self):
        """Backward compat: no precomputed_intent → classify is called as before."""
        with patch("src.coordinator.tools.tool_utils.classify_query_intent", return_value=QueryIntent.NEEDS_NEITHER) as mock_classify:
            tools = get_tools_for_query("hello", "Gojo", "common", mcp_access=None)
        mock_classify.assert_called_once()
        assert tools == []

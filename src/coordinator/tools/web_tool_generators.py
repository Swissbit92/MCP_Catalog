# src/coordinator/tools/web_tool_generators.py
"""Generic web-toolset tool definitions — ADR-009 Phase W (W2).

Extensive, task-agnostic web primitives (not weather/finance-specific). These
are OpenAI-function-format dicts registered into the `web` toolset so personas
can be granted them and the introspection API / Telegram `/tools` command can
list them. Executors are bound at service-wiring time.

`safesearch` on every search tool is an enum the model MAY set per call; the
executor clamps it UP for non-nsfw personas (never down) — see web_safesearch.
"""

from __future__ import annotations

from typing import Any, Dict

_SAFESEARCH_ENUM = ["off", "moderate", "strict"]
_CATEGORY_ENUM = [
    "general", "images", "videos", "news", "science", "files", "it",
    "music", "social_media",
]
_TIME_RANGE_ENUM = ["day", "week", "month", "year"]


def get_web_search_tool() -> Dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the web for current information, facts, news, prices, "
                "people, products, or any topic. Returns titles, URLs, and "
                "snippets. Use fetch_url afterward to read a result in full."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query."},
                    "category": {
                        "type": "string", "enum": _CATEGORY_ENUM,
                        "description": "Result category (default general).",
                    },
                    "safesearch": {
                        "type": "string", "enum": _SAFESEARCH_ENUM,
                        "description": "Adult-content filtering level.",
                    },
                    "time_range": {
                        "type": "string", "enum": _TIME_RANGE_ENUM,
                        "description": "Restrict to recent results.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Number of results (1-20, default 5).",
                    },
                },
                "required": ["query"],
            },
        },
    }


def get_fetch_url_tool() -> Dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": (
                "Fetch a web page and return its main content as clean, readable "
                "text (boilerplate removed). Use this to read a search result in "
                "full rather than relying on the snippet."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to fetch."},
                    "mode": {
                        "type": "string", "enum": ["markdown", "text", "raw"],
                        "description": "Output format (default markdown).",
                    },
                },
                "required": ["url"],
            },
        },
    }


def _category_search_tool(name: str, category: str, desc: str) -> Dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query."},
                    "safesearch": {"type": "string", "enum": _SAFESEARCH_ENUM,
                                   "description": "Adult-content filtering level."},
                    "time_range": {"type": "string", "enum": _TIME_RANGE_ENUM,
                                   "description": "Restrict to recent results."},
                },
                "required": ["query"],
            },
        },
    }


def get_image_search_tool() -> Dict[str, Any]:
    return _category_search_tool(
        "image_search", "images",
        "Search the web for images. Returns image page URLs and titles.",
    )


def get_video_search_tool() -> Dict[str, Any]:
    return _category_search_tool(
        "video_search", "videos",
        "Search the web for videos. Returns video page URLs and titles.",
    )


def get_news_search_tool() -> Dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "news_search",
            "description": "Search recent news articles on a topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The news query."},
                    "time_range": {"type": "string", "enum": _TIME_RANGE_ENUM,
                                   "description": "Recency window (default week)."},
                },
                "required": ["query"],
            },
        },
    }


def get_extract_tool() -> Dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "extract",
            "description": (
                "Extract or summarize specific information from a URL or a block "
                "of text, guided by an instruction (e.g. 'the release date', "
                "'the main argument')."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string",
                               "description": "A URL to fetch, or raw text."},
                    "instruction": {"type": "string",
                                    "description": "What to extract or summarize."},
                },
                "required": ["source", "instruction"],
            },
        },
    }


# Category per search-family tool, for the executor to route to the backend.
WEB_TOOL_CATEGORY = {
    "web_search": "general",
    "image_search": "images",
    "video_search": "videos",
    "news_search": "news",
}

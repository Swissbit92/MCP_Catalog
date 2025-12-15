# src/coordinator/server.py
# Local Coordinator server for GraphRAG Local QA Chat with Personas
# Provides endpoints for chat, greetings, persona CV summaries, and chat persistence (SQLite).

from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import datetime
import sqlite3
import os
import threading
import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager

from .config import (
    get_ollama_base, get_persona_model, get_persona_temperature,
    is_brave_enabled, get_brave_api_key, get_brave_max_results,
    get_brave_safesearch, get_brave_search_timeout, get_brave_enabled_rarities,
    is_mongodb_enabled, get_mongodb_uri, get_mongodb_timeout,
    get_mongodb_max_response_bytes, get_mongodb_enabled_rarities,
    get_mongodb_cache_ttl
)
from .ollama_utils import assert_model_available
from .llm_client import LC_OllamaClient
from .persona_memory import (
    build_system_prompt, build_greeting_user_prompt, get_persona_card,
    get_or_build_cv_summary, ensure_all_summaries_serialized, _load_all_cards_cached
)
from .mcp_client import BraveMCPClient
from .mongodb_mcp_client import MongoDBMCPClient
from .cache import get_cache, MongoDBCache
from .tool_definitions import get_tools_for_persona, classify_query_intent, get_tools_for_query, QueryIntent

import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ----------------- Citation Validation -----------------

def validate_citations(answer: str, used_search: bool, search_results_count: int = 0) -> tuple[str, bool, dict]:
    """
    Validate that web search responses include proper source citations.

    Args:
        answer: LLM's response text
        used_search: Whether web search was used
        search_results_count: Number of search results returned

    Returns:
        Tuple of (answer, has_valid_citations, validation_details)
        - answer: Potentially modified answer (with warning if citations missing)
        - has_valid_citations: Boolean indicating if citations are valid
        - validation_details: Dict with validation results
    """
    validation = {
        "has_citation_section": False,
        "has_markdown_links": False,
        "citation_count": 0,
        "has_emoji": False,
        "valid": False
    }

    if not used_search:
        validation["valid"] = True
        return answer, True, validation

    # Check for citation section markers (with or without emoji)
    has_citation_with_emoji = "🔍 Sources:" in answer or "🔍 **Sources:**" in answer
    has_citation_without_emoji = bool(re.search(r'\*\*Sources:\*\*|\nSources:\n', answer))

    validation["has_citation_section"] = has_citation_with_emoji or has_citation_without_emoji
    validation["has_emoji"] = has_citation_with_emoji

    # Check for markdown links [text](url)
    markdown_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', answer)
    validation["has_markdown_links"] = len(markdown_links) > 0
    validation["citation_count"] = len(markdown_links)

    # Check if links contain http/https URLs
    has_http_links = any('http' in url for _, url in markdown_links)

    # Valid if: has citation section + has markdown links with URLs
    if validation["has_citation_section"] and validation["has_markdown_links"] and has_http_links:
        validation["valid"] = True

        # Log success
        logger.info(f"[Citations] ✅ Valid citations found: {validation['citation_count']} sources, emoji={'✅' if validation['has_emoji'] else '❌'}")

        return answer, True, validation

    # Invalid citations - log warning
    logger.warning(f"[Citations] ❌ Missing or invalid citations for search query")
    logger.warning(f"[Citations] Details: section={validation['has_citation_section']}, links={validation['has_markdown_links']}, count={validation['citation_count']}")


# ----------------- First-Person Post-Processing -----------------

def detect_third_person(answer: str, persona_name: str) -> tuple[bool, list[str]]:
    """
    Detect third-person patterns in persona response.

    Args:
        answer: Persona's response text
        persona_name: Full persona name (e.g., "Eeva — Bitcoin Expert")

    Returns:
        Tuple of (has_third_person, violations_list)
    """
    first_name = persona_name.split(" — ")[0].strip().split()[0].lower()
    answer_lower = answer.lower()

    # Check for first-person self-introduction (these are valid)
    has_first_person_intro = any(pattern in answer_lower for pattern in [
        f"i'm {first_name},",
        f"i am {first_name},",
        f"i'm {first_name} and",
        f"i am {first_name} and",
    ])

    # Third-person violation patterns
    violation_patterns = [
        f"{first_name} is a ",
        f"{first_name} is an ",
        f"{first_name} has ",
        f"{first_name} was ",
        f"{first_name} specializes ",
        f"{first_name} believes ",
        f"{first_name} works ",
        f"{first_name}'s ",
        f"about {first_name}",
    ]

    # Only flag "{name}, a/an" if NOT part of first-person intro
    if not has_first_person_intro:
        violation_patterns.extend([
            f"{first_name}, a ",
            f"{first_name}, an ",
        ])

    # Find violations
    violations = [pattern for pattern in violation_patterns if pattern in answer_lower]

    return len(violations) > 0, violations


def rewrite_to_first_person(answer: str, persona_name: str) -> str:
    """
    Use LLM to rewrite third-person response to first-person.

    Args:
        answer: Original response (in third-person)
        persona_name: Persona name for context

    Returns:
        Rewritten response in first-person
    """
    first_name = persona_name.split(" — ")[0].strip().split()[0]

    rewrite_prompt = f"""The following response was written in THIRD PERSON but should be in FIRST PERSON.

Original response:
{answer}

Your task:
1. Rewrite this response so {first_name} speaks in FIRST PERSON (I, my, me)
2. Keep the same information and tone
3. Do NOT add new information
4. Do NOT use "{first_name} is", "{first_name} has", etc.
5. Use "I am", "I have", "my", "me" instead

Rewritten first-person response:"""

    try:
        client = LC_OllamaClient(
            base=get_ollama_base(),
            model=get_persona_model(),
            temperature=0.2  # Lower temperature for more consistent rewrites
        )

        rewritten = client.complete(
            system="You are a helpful assistant that rewrites text from third-person to first-person. Follow the instructions exactly.",
            user_prompt=rewrite_prompt
        )

        return rewritten.strip()

    except Exception as e:
        logger.warning(f"[FirstPerson] Failed to rewrite response: {e}")
        return answer  # Return original on error


def post_process_first_person(answer: str, persona_name: str) -> tuple[str, bool]:
    """
    Post-process response to enforce first-person voice.

    Detects third-person patterns and rewrites to first-person if needed.

    Args:
        answer: Persona response
        persona_name: Full persona name

    Returns:
        Tuple of (processed_answer, was_rewritten)
    """
    has_third_person, violations = detect_third_person(answer, persona_name)

    if not has_third_person:
        logger.info(f"[FirstPerson] ✅ Response is first-person, no rewrite needed")
        return answer, False

    # Log violation and rewrite
    logger.warning(f"[FirstPerson] ⚠️ Third-person detected: {violations[0]}")
    logger.info(f"[FirstPerson] 🔄 Rewriting to first-person...")

    rewritten = rewrite_to_first_person(answer, persona_name)

    # Verify rewrite worked
    still_third_person, _ = detect_third_person(rewritten, persona_name)

    if still_third_person:
        logger.warning(f"[FirstPerson] ❌ Rewrite still contains third-person, using original")
        return answer, False
    else:
        logger.info(f"[FirstPerson] ✅ Successfully rewritten to first-person")
        return rewritten, True

    # Auto-append reminder if citations are completely missing
    if not validation["has_citation_section"]:
        reminder = f"\n\n⚠️ Note: {search_results_count} web source(s) were consulted but citations were not included in the response."
        answer = answer + reminder
        logger.info(f"[Citations] Appended missing citation reminder to response")

    return answer, False, validation


app = FastAPI(title="Local Coordinator (Chat-only)", version="0.5.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- Brave MCP Client (Web Search) -----------------
_brave_client: Optional[BraveMCPClient] = None

def get_brave_client() -> Optional[BraveMCPClient]:
    """Get the global Brave MCP client instance."""
    return _brave_client

def _init_brave_client():
    """Initialize Brave MCP client if enabled."""
    global _brave_client
    if not is_brave_enabled():
        logger.info("Brave MCP is disabled (no API key)")
        return

    try:
        api_key = get_brave_api_key()
        max_results = get_brave_max_results()
        safesearch = get_brave_safesearch()
        timeout = get_brave_search_timeout()

        _brave_client = BraveMCPClient(
            api_key=api_key,
            max_results=max_results,
            safesearch=safesearch,
            timeout=timeout
        )
        logger.info(f"Brave MCP client initialized (max_results={max_results}, timeout={timeout}s)")
    except Exception as e:
        logger.error(f"Failed to initialize Brave MCP client: {e}")
        _brave_client = None

# ----------------- MongoDB MCP Client (Trading Data) -----------------
_mongodb_client: Optional[MongoDBMCPClient] = None
_mongodb_cache: Optional[MongoDBCache] = None

def get_mongodb_client() -> Optional[MongoDBMCPClient]:
    """Get the global MongoDB MCP client instance."""
    return _mongodb_client

def get_mongodb_cache() -> Optional[MongoDBCache]:
    """Get the global MongoDB cache instance."""
    return _mongodb_cache

def _init_mongodb_client():
    """Initialize MongoDB MCP client if enabled."""
    global _mongodb_client, _mongodb_cache
    if not is_mongodb_enabled():
        logger.info("MongoDB MCP is disabled (no URI or feature flag off)")
        return

    try:
        mongodb_uri = get_mongodb_uri()
        timeout = get_mongodb_timeout()
        max_response_bytes = get_mongodb_max_response_bytes()

        _mongodb_client = MongoDBMCPClient(
            connection_uri=mongodb_uri,
            timeout=timeout,
            max_response_bytes=max_response_bytes
        )

        # Initialize cache
        _mongodb_cache = get_cache()

        logger.info(f"MongoDB MCP client initialized (timeout={timeout}s, max_response={max_response_bytes} bytes)")
        logger.info(f"MongoDB cache initialized")
    except Exception as e:
        logger.error(f"Failed to initialize MongoDB MCP client: {e}")
        _mongodb_client = None
        _mongodb_cache = None

# ----------------- SQLite persistence (tiny DAO) -----------------
_DB_PATH = os.environ.get("COORDINATOR_DB_PATH", "chats.db")
_DB_LOCK = threading.Lock()

def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def _init_db():
    with _DB_LOCK:
        c = _conn()
        cur = c.cursor()

        # Create chat_sessions table (replaces old chats table)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id TEXT PRIMARY KEY,
            persona_key TEXT NOT NULL,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""")

        # Create messages table linked to sessions
        cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            latency_ms INTEGER,
            FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
        )""")

        # Migration: If old tables exist, migrate data
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chats'")
        if cur.fetchone():
            print("Migrating old chat data to new schema...")
            # Migrate existing chats to sessions
            cur.execute("""
            INSERT OR IGNORE INTO chat_sessions (id, persona_key, title, created_at, updated_at)
            SELECT printf('session_%06d', id), persona, title, created_at, updated_at FROM chats
            """)
            # Migrate messages
            cur.execute("""
            INSERT OR IGNORE INTO messages (id, session_id, role, content, timestamp, latency_ms)
            SELECT printf('msg_%06d', id), printf('session_%06d', chat_id), role, content, ts, latency_ms FROM messages
            """)
            print("Migration completed.")

        # Create indexes for better performance
        cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_sessions_persona ON chat_sessions(persona_key)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON chat_sessions(created_at)")

        c.commit()
        c.close()

def _now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"

def _fetchone_dict(cur) -> Optional[Dict[str, Any]]:
    row = cur.fetchone()
    if not row:
        return None
    return dict(row)

def _fetchall_list(cur) -> List[Dict[str, Any]]:
    return [dict(r) for r in cur.fetchall()]

def _cleanup_orphaned_sessions():
    """
    Remove chat sessions for personas that no longer exist.
    This should be called when personas are loaded to ensure cleanup.
    """
    try:
        # Get all current persona keys
        cards = _load_all_cards_cached()
        current_persona_keys = {card.get("key") for card in cards if card.get("key")}

        with _DB_LOCK:
            c = _conn()
            cur = c.cursor()

            # Find sessions with personas that no longer exist
            cur.execute("SELECT id, persona_key FROM chat_sessions")
            all_sessions = cur.fetchall()

            orphaned_sessions = []
            for session in all_sessions:
                session_id = session["id"]
                persona_key = session["persona_key"]
                if persona_key not in current_persona_keys:
                    orphaned_sessions.append((session_id, persona_key))

            # Delete orphaned sessions (messages will be cascade deleted)
            if orphaned_sessions:
                orphaned_ids = [s[0] for s in orphaned_sessions]
                orphaned_personas = list(set(s[1] for s in orphaned_sessions))  # Unique persona keys

                # Delete sessions (messages will be cascade deleted due to FOREIGN KEY)
                placeholders = ','.join('?' * len(orphaned_ids))
                cur.execute(f"DELETE FROM chat_sessions WHERE id IN ({placeholders})", orphaned_ids)

                c.commit()
                print(f"Cleaned up {len(orphaned_sessions)} orphaned sessions for removed personas: {orphaned_personas}")

            c.close()

    except Exception as e:
        print(f"Warning: Failed to cleanup orphaned sessions: {e}")
        # Don't raise - this is not critical for app startup



# ----------------- Schemas -----------------
class ChatTurn(BaseModel):
    role: str
    content: str

class ChatBody(BaseModel):
    persona: Optional[str] = None
    history: List[ChatTurn] = []
    message: str

class GreetBody(BaseModel):
    persona: Optional[str] = None

class SummaryBody(BaseModel):
    persona: Optional[str] = None  # label/key; None resolves to first card

class CreateChatBody(BaseModel):
    persona: str
    title: str = "New Chat"

class RenameChatBody(BaseModel):
    title: str

class AppendMessageBody(BaseModel):
    role: str
    content: str
    ts: Optional[str] = None
    latency_ms: Optional[int] = None

class SelectChatBody(BaseModel):
    persona: str

# New session-based models
class CreateSessionBody(BaseModel):
    persona_key: str
    title: str = "New Chat"

class UpdateSessionBody(BaseModel):
    title: str

class MessageModel(BaseModel):
    id: str
    role: str
    content: str
    timestamp: str
    latency_ms: Optional[int] = None

class SessionModel(BaseModel):
    id: str
    persona_key: str
    title: str
    created_at: str
    updated_at: str
    message_count: int = 0

class SessionWithMessages(BaseModel):
    session: SessionModel
    messages: List[MessageModel]

# Export/Import models
class ExportData(BaseModel):
    version: str = "1.0"
    exported_at: str
    app_version: str = "1.0.0"
    persona: Dict[str, Any]
    session: Dict[str, Any]
    messages: List[Dict[str, Any]]

class ImportBody(BaseModel):
    data: ExportData
    create_new_session: bool = True

class ImportChatBody(BaseModel):
    persona: str
    chat: Dict[str, Any] = Field(..., description="JSON with {title, messages: [{role,content,ts?}]}")

# Response Metadata for MCP data sources
class ResponseMetadata(BaseModel):
    source_type: str = "llm"  # "llm", "brave_mcp", "mongodb_mcp", "multi_mcp"
    tools_used: List[str] = []
    cache_status: Optional[str] = None  # "hit", "miss", None
    data_timestamp: Optional[str] = None
    latency_breakdown: Optional[Dict[str, int]] = None  # {"llm": 3000, "mongodb": 500}

# ----------------- MongoDB Tool Handlers -----------------

def _check_cache_or_fetch(tool_name: str, fetch_func, force_refresh: bool = False):
    """Check cache first, then fetch from MongoDB if needed."""
    if not _mongodb_cache or not _mongodb_client:
        return None, "miss"

    # Check cache unless force refresh
    if not force_refresh:
        cached = _mongodb_cache.get(tool_name)
        if cached:
            logger.info(f"Cache HIT for {tool_name} (age: {cached.age_seconds()}s)")
            return cached.data, "hit"

    # Cache miss or force refresh - fetch from MongoDB
    logger.info(f"Cache MISS for {tool_name}, fetching from MongoDB...")
    try:
        data = fetch_func()
        # Cache the result
        ttl = get_mongodb_cache_ttl(tool_name)
        _mongodb_cache.set(tool_name, data, ttl=ttl, source="mongodb_mcp")
        logger.info(f"Cached {tool_name} with TTL={ttl}s")
        return data, "miss"
    except Exception as e:
        logger.error(f"MongoDB fetch error for {tool_name}: {e}")
        raise

def handle_bitcoin_current_price(reason: str, include_indicators: Optional[List[str]] = None) -> Dict[str, Any]:
    """Get current Bitcoin price with key technical indicators."""
    if not _mongodb_client:
        raise HTTPException(status_code=503, detail="MongoDB MCP not available")

    def fetch():
        # Query 1h_price_data for latest document
        result = _mongodb_client.find(
            database="btc_data",
            collection="1h_price_data",
            filter={},
            sort={"timestamp": -1},
            limit=1
        )

        if not result or len(result) == 0:
            raise HTTPException(status_code=404, detail="No price data found")

        latest = result[0]

        # Build response with technical explanations
        indicators_to_include = include_indicators or ["RSI", "MACD_Line", "BB_High", "BB_Low", "EMA_20", "EMA_50"]

        indicators_data = {}
        for ind in indicators_to_include:
            if ind in latest:
                indicators_data[ind] = latest[ind]

        # Add signal interpretations
        rsi = latest.get("RSI", 0)
        rsi_signal = "Overbought" if rsi > 70 else "Oversold" if rsi < 30 else "Neutral-Bullish" if rsi > 50 else "Neutral-Bearish"

        macd_hist = latest.get("MACD_Histogram", 0)
        macd_trend = "Bullish crossover" if macd_hist > 0 else "Bearish crossover"

        price = latest.get("Close", 0)
        bb_upper = latest.get("BB_High", 0)
        bb_lower = latest.get("BB_Low", 0)
        bb_mid = (bb_upper + bb_lower) / 2 if bb_upper and bb_lower else 0
        bb_position = "Near upper band" if price > bb_mid else "Near lower band"

        return {
            "price": latest.get("Close"),
            "timestamp": latest.get("timestamp"),
            "volume": latest.get("Volume"),
            "indicators": {
                "RSI": {"value": rsi, "signal": rsi_signal},
                "MACD": {
                    "line": latest.get("MACD_Line"),
                    "signal": latest.get("MACD_Signal"),
                    "histogram": macd_hist,
                    "trend": macd_trend
                },
                "Bollinger_Bands": {
                    "upper": bb_upper,
                    "lower": bb_lower,
                    "signal": bb_position
                },
                "EMA_20": latest.get("EMA_20"),
                "EMA_50": latest.get("EMA_50"),
                "raw_indicators": indicators_data
            },
            "data_source": "1h_price_data"
        }

    data, cache_status = _check_cache_or_fetch("bitcoin_current_price", fetch)
    data["cache_status"] = cache_status
    return data

def handle_bitcoin_historical_prices(reason: str, start_date: str, end_date: Optional[str] = None,
                                     timeframe: str = "daily", indicators: Optional[List[str]] = None) -> Dict[str, Any]:
    """Query historical Bitcoin price data with date range."""
    if not _mongodb_client:
        raise HTTPException(status_code=503, detail="MongoDB MCP not available")

    collection = "daily_price_data" if timeframe == "daily" else "1h_price_data"

    # Build query filter
    query_filter = {}
    if start_date:
        if not end_date:
            end_date = datetime.utcnow().strftime("%Y-%m-%d")
        query_filter["timestamp"] = {"$gte": start_date, "$lte": end_date}

    # Build projection
    projection = {
        "timestamp": 1,
        "Open": 1,
        "High": 1,
        "Low": 1,
        "Close": 1,
        "Volume": 1
    }

    if indicators:
        for ind in indicators:
            projection[ind] = 1

    def fetch():
        results = _mongodb_client.find(
            database="btc_data",
            collection=collection,
            filter=query_filter,
            projection=projection,
            sort={"timestamp": 1},
            limit=100  # Safety limit
        )

        return {
            "timeframe": timeframe,
            "start_date": start_date,
            "end_date": end_date,
            "count": len(results),
            "data": results,
            "data_source": collection
        }

    # Use a cache key that includes the date range
    cache_key = f"bitcoin_historical_prices_{start_date}_{end_date}_{timeframe}"
    data, cache_status = _check_cache_or_fetch(cache_key, fetch)
    data["cache_status"] = cache_status
    return data

def handle_bitcoin_trading_summary(reason: str, start_date: Optional[str] = None,
                                   end_date: Optional[str] = None) -> Dict[str, Any]:
    """Get DCA (Dollar Cost Averaging) trading statistics."""
    if not _mongodb_client:
        raise HTTPException(status_code=503, detail="MongoDB MCP not available")

    def fetch():
        # Build match stage
        match_stage = {}
        if start_date or end_date:
            match_stage["timestamp"] = {}
            if start_date:
                match_stage["timestamp"]["$gte"] = start_date
            if end_date:
                match_stage["timestamp"]["$lte"] = end_date

        # Aggregation pipeline
        pipeline = [
            {"$match": match_stage} if match_stage else {"$match": {}},
            {"$group": {
                "_id": None,
                "total_btc": {"$sum": "$dealSize"},
                "total_usdt_spent": {"$sum": "$dealFunds"},
                "total_fees": {"$sum": "$fee"},
                "num_purchases": {"$sum": 1},
                "avg_price": {"$avg": "$price"},
                "min_price": {"$min": "$price"},
                "max_price": {"$max": "$price"},
                "first_purchase": {"$min": "$timestamp"},
                "last_purchase": {"$max": "$timestamp"}
            }}
        ]

        results = _mongodb_client.aggregate(
            database="btc_data",
            collection="BTC dayli buying",
            pipeline=pipeline
        )

        if not results or len(results) == 0:
            return {
                "total_btc": 0,
                "total_usdt_spent": 0,
                "total_fees": 0,
                "num_purchases": 0,
                "data_source": "BTC dayli buying"
            }

        summary = results[0]
        summary["data_source"] = "BTC dayli buying"
        return summary

    cache_key = f"bitcoin_trading_summary_{start_date}_{end_date}"
    data, cache_status = _check_cache_or_fetch(cache_key, fetch)
    data["cache_status"] = cache_status
    return data

def handle_bitcoin_technical_analysis(reason: str, timeframe: str = "hourly") -> Dict[str, Any]:
    """Multi-timeframe technical analysis."""
    if not _mongodb_client:
        raise HTTPException(status_code=503, detail="MongoDB MCP not available")

    def fetch():
        collection = "1h_price_data" if timeframe == "hourly" else "daily_price_data"

        # Get latest data
        results = _mongodb_client.find(
            database="btc_data",
            collection=collection,
            filter={},
            sort={"timestamp": -1},
            limit=1
        )

        if not results or len(results) == 0:
            raise HTTPException(status_code=404, detail="No data found")

        latest = results[0]

        # Analyze indicators
        price = latest.get("Close", 0)
        ema_20 = latest.get("EMA_20", 0)
        ema_50 = latest.get("EMA_50", 0)
        ema_200 = latest.get("EMA_200", 0)

        trend = "bullish" if price > ema_20 > ema_50 else "bearish"

        rsi = latest.get("RSI", 0)
        rsi_signal = "overbought" if rsi > 70 else "oversold" if rsi < 30 else "neutral"

        macd_hist = latest.get("MACD_Histogram", 0)
        macd_crossover = "bullish" if macd_hist > 0 else "bearish"

        bb_high = latest.get("BB_High", 0)
        bb_low = latest.get("BB_Low", 0)
        bb_mid = (bb_high + bb_low) / 2 if bb_high and bb_low else 0
        bb_position = "upper" if price > bb_mid else "lower"

        analysis = {
            "price": price,
            "timestamp": latest.get("timestamp"),
            "timeframe": timeframe,
            "trend_indicators": {
                "EMA_20": ema_20,
                "EMA_50": ema_50,
                "EMA_200": ema_200,
                "trend": trend
            },
            "momentum_indicators": {
                "RSI": {
                    "value": rsi,
                    "signal": rsi_signal
                },
                "MACD": {
                    "line": latest.get("MACD_Line"),
                    "signal": latest.get("MACD_Signal"),
                    "histogram": macd_hist,
                    "crossover": macd_crossover
                },
                "Stochastic_RSI": latest.get("Stoch_RSI")
            },
            "volatility_indicators": {
                "Bollinger_Bands": {
                    "upper": bb_high,
                    "lower": bb_low,
                    "position": bb_position
                }
            },
            "support_resistance": {
                "Donchian_High": latest.get("Donchian_High"),
                "Donchian_Low": latest.get("Donchian_Low"),
                "Ichimoku_Base": latest.get("Ichimoku_Base")
            },
            "data_source": collection
        }

        return analysis

    cache_key = f"bitcoin_technical_analysis_{timeframe}"
    data, cache_status = _check_cache_or_fetch(cache_key, fetch)
    data["cache_status"] = cache_status
    return data

# ----------------- Chat Inference -----------------
@app.post("/persona/chat")
def chat(body: ChatBody):
    """Chat with a persona, with autonomous tool support (web search + MongoDB) for higher rarity personas."""
    card = get_persona_card(body.persona)
    if not card:
        raise HTTPException(status_code=400, detail="Unknown persona.")

    persona_key = card.get("key")
    persona_rarity = card.get("rarity", "common").lower()
    system = build_system_prompt(body.persona)

    # Build conversation context from history
    history = body.history[-6:]
    lines = []
    for t in history:
        role = (t.role or "").lower()
        lines.append(f"[Assistant]\n{t.content}" if role == "assistant" else f"[User]\n{t.content}")
    lines.append(f"[User]\n{body.message}")
    user_compiled = "\n\n".join(lines)

    # Use intent classification to determine which tools to inject
    intent = classify_query_intent(body.message, persona_rarity)
    logger.info(f"[Chat] Request received: persona={persona_key}, rarity={persona_rarity}, query_preview='{body.message[:60]}...'")
    logger.info(f"[Intent] Classification result: {intent.value}")

    # Get tools based on intent
    tools = get_tools_for_query(body.message, persona_key, persona_rarity)
    tool_names = [t["function"]["name"] for t in tools] if tools else []
    logger.info(f"[Tools] Injecting {len(tools)} tool(s): {tool_names}")

    # Prepare metadata
    metadata = ResponseMetadata(
        source_type="llm",
        tools_used=[],
        cache_status=None,
        data_timestamp=None
    )

    if not tools:
        # No tools needed - regular LLM completion
        logger.info("No tools needed, using regular completion")
        client = LC_OllamaClient(
            base=get_ollama_base(),
            model=get_persona_model(),
            temperature=get_persona_temperature()
        )
        answer = client.complete(system=system, user_prompt=user_compiled)

        # Post-process to enforce first-person
        persona_name = card.get("display_name") or card.get("key") or "Persona"
        answer, was_rewritten = post_process_first_person(answer, persona_name)

        return {"answer": answer, "used_search": False, "metadata": metadata.dict(), "rewritten": was_rewritten}

    # Tools needed - check if MongoDB tools are included
    mongodb_tools = [t for t in tools if t.get("function", {}).get("name", "").startswith("bitcoin_")]
    brave_tools = [t for t in tools if t.get("function", {}).get("name", "") == "brave_web_search"]

    if mongodb_tools and not brave_tools:
        # MongoDB-only query - handle directly without llm_client tool calling
        # This is more efficient for MongoDB queries
        logger.info(f"MongoDB-only query detected, using direct handlers")

        # For simplicity, use the first MongoDB tool (LLM will decide which one)
        # In production, we'd want the LLM to make this decision
        tool_name = mongodb_tools[0]["function"]["name"]
        logger.info(f"Using MongoDB tool: {tool_name}")

        try:
            # Execute MongoDB tool directly
            mongodb_result = None
            if tool_name == "bitcoin_current_price":
                mongodb_result = handle_bitcoin_current_price(reason="User query about current price")
            elif tool_name == "bitcoin_historical_prices":
                # Extract date from query if possible, otherwise use last 7 days
                import re
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', body.message)
                start_date = date_match.group(1) if date_match else "2025-12-01"
                mongodb_result = handle_bitcoin_historical_prices(reason="User query about historical data", start_date=start_date)
            elif tool_name == "bitcoin_trading_summary":
                mongodb_result = handle_bitcoin_trading_summary(reason="User query about trading stats")
            elif tool_name == "bitcoin_technical_analysis":
                mongodb_result = handle_bitcoin_technical_analysis(reason="User query about technical analysis")

            if mongodb_result:
                # Format results for LLM to synthesize
                import json
                formatted_data = json.dumps(mongodb_result, indent=2)

                # Ask LLM to synthesize the response
                client = LC_OllamaClient(
                    base=get_ollama_base(),
                    model=get_persona_model(),
                    temperature=get_persona_temperature()
                )

                synthesis_prompt = f"""{user_compiled}

[MongoDB Data Retrieved]
{formatted_data}

Please synthesize this data into a natural, conversational response. Include key technical insights and interpretations."""

                answer = client.complete(system=system, user_prompt=synthesis_prompt)

                # Update metadata
                metadata.source_type = "mongodb_mcp"
                metadata.tools_used = [tool_name]
                metadata.cache_status = mongodb_result.get("cache_status", "miss")
                metadata.data_timestamp = mongodb_result.get("timestamp", "")

                logger.info(f"MongoDB query completed: tool={tool_name}, cache={metadata.cache_status}")

                # Post-process to enforce first-person
                persona_name = card.get("display_name") or card.get("key") or "Persona"
                answer, was_rewritten = post_process_first_person(answer, persona_name)

                return {
                    "answer": answer,
                    "used_search": True,
                    "metadata": metadata.dict(),
                    "rewritten": was_rewritten
                }
        except Exception as e:
            logger.error(f"MongoDB query failed: {e}")
            # Fallback to regular LLM response
            client = LC_OllamaClient(
                base=get_ollama_base(),
                model=get_persona_model(),
                temperature=get_persona_temperature()
            )
            answer = client.complete(system=system, user_prompt=user_compiled)
            return {"answer": answer, "used_search": False, "metadata": metadata.dict()}

    elif brave_tools and not mongodb_tools:
        # Brave-only query - use existing tool calling system
        logger.info("[Brave] Starting Brave-only query workflow")
        start_time = time.time()

        client = LC_OllamaClient(
            base=get_ollama_base(),
            model=get_persona_model(),
            temperature=get_persona_temperature(),
            mcp_client=_brave_client
        )

        answer, tool_call, search_results = client.complete_with_tools(
            persona_system=system,
            user_prompt=user_compiled,
            tools=tools
        )

        elapsed = time.time() - start_time

        metadata.source_type = "brave_mcp"
        metadata.tools_used = ["brave_web_search"] if tool_call else []

        # Validate citations for web search responses
        search_count = len(search_results) if search_results else 0
        answer, has_valid_citations, citation_details = validate_citations(
            answer=answer,
            used_search=tool_call is not None,
            search_results_count=search_count
        )

        # Post-process to enforce first-person
        persona_name = card.get("display_name") or card.get("key") or "Persona"
        answer, was_rewritten = post_process_first_person(answer, persona_name)

        response = {
            "answer": answer,
            "used_search": tool_call is not None,
            "metadata": metadata.dict(),
            "citation_valid": has_valid_citations,
            "rewritten": was_rewritten
        }

        if search_results:
            response["search_results_count"] = len(search_results)
            logger.info(f"[Brave] ✅ Workflow completed: used_search={tool_call is not None}, results_count={len(search_results)}, citations_valid={has_valid_citations}, total_time={elapsed:.2f}s")
        else:
            logger.info(f"[Brave] ✅ Workflow completed: used_search=False, total_time={elapsed:.2f}s (LLM answered directly)")

        return response

    elif brave_tools and mongodb_tools:
        # Multi-MCP query - combine both sources
        logger.info("Multi-MCP query detected (Brave + MongoDB)")
        # For MVP, execute sequentially (parallel execution can be added later)

        # Execute Brave search first
        client = LC_OllamaClient(
            base=get_ollama_base(),
            model=get_persona_model(),
            temperature=get_persona_temperature(),
            mcp_client=_brave_client
        )

        answer, tool_call, search_results = client.complete_with_tools(
            persona_system=system,
            user_prompt=user_compiled,
            tools=brave_tools
        )

        # TODO: Add MongoDB query execution and combine results
        # For now, just return Brave results
        metadata.source_type = "multi_mcp"
        metadata.tools_used = ["brave_web_search"]

        # Validate citations
        search_count = len(search_results) if search_results else 0
        answer, has_valid_citations, citation_details = validate_citations(
            answer=answer,
            used_search=True,
            search_results_count=search_count
        )

        # Post-process to enforce first-person
        persona_name = card.get("display_name") or card.get("key") or "Persona"
        answer, was_rewritten = post_process_first_person(answer, persona_name)

        response = {
            "answer": answer,
            "used_search": True,
            "metadata": metadata.dict(),
            "citation_valid": has_valid_citations,
            "search_results_count": search_count,
            "rewritten": was_rewritten
        }

        return response

    else:
        # Fallback to regular completion
        client = LC_OllamaClient(
            base=get_ollama_base(),
            model=get_persona_model(),
            temperature=get_persona_temperature()
        )
        answer = client.complete(system=system, user_prompt=user_compiled)

        # Post-process to enforce first-person
        persona_name = card.get("display_name") or card.get("key") or "Persona"
        answer, was_rewritten = post_process_first_person(answer, persona_name)

        return {"answer": answer, "used_search": False, "metadata": metadata.dict(), "rewritten": was_rewritten}

@app.post("/sessions/{session_id}/chat")
def chat_with_session(session_id: str, body: ChatBody):
    """Chat with a persona and automatically save to session."""
    # Get session info
    with _DB_LOCK:
        c = _conn()
        cur = c.cursor()
        cur.execute("SELECT persona_key FROM chat_sessions WHERE id = ?", (session_id,))
        row = cur.fetchone()
        c.close()
        if not row:
            raise HTTPException(status_code=404, detail="Session not found.")

    persona_key = row["persona_key"]

    # Perform chat
    chat_body = ChatBody(persona=persona_key, history=body.history, message=body.message)
    response = chat(chat_body)

    # Save user message to session
    user_msg_body = AppendMessageBody(
        role="user",
        content=body.message,
        ts=_now()
    )
    add_message(session_id, user_msg_body)

    # Save assistant response to session
    assistant_msg_body = AppendMessageBody(
        role="assistant",
        content=response["answer"],
        ts=_now()
    )
    add_message(session_id, assistant_msg_body)

    return response

@app.post("/persona/greet")
def greet(body: GreetBody):
    card = get_persona_card(body.persona)
    if not card:
        raise HTTPException(status_code=400, detail="Unknown persona.")
    system = build_system_prompt(body.persona)
    user_prompt = build_greeting_user_prompt(body.persona)

    client = LC_OllamaClient(
        base=get_ollama_base(),
        model=get_persona_model(),
        temperature=get_persona_temperature(),
    )
    answer = client.complete(system=system, user_prompt=user_prompt)

    # Post-process to enforce first-person
    persona_name = card.get("display_name") or card.get("key") or "Persona"
    answer, was_rewritten = post_process_first_person(answer, persona_name)

    return {"answer": answer, "rewritten": was_rewritten}

@app.post("/sessions/{session_id}/greet")
def greet_with_session(session_id: str, body: GreetBody):
    """Generate a greeting and save it to the session."""
    # Get session info
    with _DB_LOCK:
        c = _conn()
        cur = c.cursor()
        cur.execute("SELECT persona_key FROM chat_sessions WHERE id = ?", (session_id,))
        row = cur.fetchone()
        c.close()
        if not row:
            raise HTTPException(status_code=404, detail="Session not found.")

    persona_key = row["persona_key"]

    # Generate greeting
    greet_body = GreetBody(persona=persona_key)
    response = greet(greet_body)

    # Save greeting to session
    greeting_msg_body = AppendMessageBody(
        role="assistant",
        content=response["answer"],
        ts=_now()
    )
    add_message(session_id, greeting_msg_body)

    return response

@app.get("/personas")
def list_personas():
    """Return list of available personas with metadata."""
    try:
        # Clean up orphaned sessions before returning personas
        _cleanup_orphaned_sessions()

        cards = _load_all_cards_cached()
        personas = []
        for card in cards:
            personas.append({
                "key": card.get("key"),
                "display_name": card.get("display_name") or card.get("key"),
                "style": card.get("style", ""),
                "rarity": card.get("rarity", "common"),
                "coordinator_label": card.get("coordinator_label"),
                "image": card.get("image"),
                "avatar": card.get("avatar"),
                "bg": card.get("bg"),
                "voice": card.get("voice"),
            })
        return personas
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list personas: {e}")

@app.post("/persona/summary")
def summary(body: SummaryBody):
    """
    Returns the cached or freshly built CV-style summary for a persona.
    { key, hash, updated, summary }
    """
    try:
        data = get_or_build_cv_summary(body.persona)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary error: {e}")

# ----------------- Session-based Persistence API -----------------

import uuid

def _generate_session_id() -> str:
    return f"session_{uuid.uuid4().hex[:16]}"

def _generate_message_id() -> str:
    return f"msg_{uuid.uuid4().hex[:16]}"

@app.get("/sessions")
def list_sessions():
    """List all chat sessions."""
    print("DEBUG: list_sessions called")
    with _DB_LOCK:
        c = _conn()
        cur = c.cursor()
        cur.execute("""
            SELECT s.id, s.persona_key, s.title, s.created_at, s.updated_at,
                   COUNT(m.id) as message_count
            FROM chat_sessions s
            LEFT JOIN messages m ON s.id = m.session_id
            GROUP BY s.id
            ORDER BY s.updated_at DESC, s.created_at DESC
        """)
        sessions = []
        for row in cur.fetchall():
            sessions.append({
                "id": row["id"],
                "persona_key": row["persona_key"],
                "title": row["title"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "message_count": row["message_count"]
            })
        c.close()
    return sessions

@app.post("/sessions")
def create_session(body: CreateSessionBody):
    """Create a new chat session."""
    session_id = _generate_session_id()
    now = _now()
    with _DB_LOCK:
        c = _conn()
        cur = c.cursor()
        cur.execute("""
            INSERT INTO chat_sessions (id, persona_key, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, body.persona_key, body.title.strip() or "New Chat", now, now))
        c.commit()
        c.close()
    return {
        "id": session_id,
        "persona_key": body.persona_key,
        "title": body.title,
        "created_at": now,
        "updated_at": now,
        "message_count": 0
    }

@app.get("/sessions/{session_id}")
def get_session(session_id: str):
    """Get a chat session with all its messages."""
    with _DB_LOCK:
        c = _conn()
        cur = c.cursor()

        # Get session info
        cur.execute("""
            SELECT s.id, s.persona_key, s.title, s.created_at, s.updated_at,
                   COUNT(m.id) as message_count
            FROM chat_sessions s
            LEFT JOIN messages m ON s.id = m.session_id
            WHERE s.id = ?
            GROUP BY s.id
        """, (session_id,))
        session_row = cur.fetchone()
        if not session_row:
            c.close()
            raise HTTPException(status_code=404, detail="Session not found.")

        # Get messages
        cur.execute("""
            SELECT id, role, content, timestamp, latency_ms
            FROM messages
            WHERE session_id = ?
            ORDER BY timestamp ASC
        """, (session_id,))
        messages = []
        for msg_row in cur.fetchall():
            messages.append({
                "id": msg_row["id"],
                "role": msg_row["role"],
                "content": msg_row["content"],
                "timestamp": msg_row["timestamp"],
                "latency_ms": msg_row["latency_ms"]
            })

        c.close()

    return {
        "session": {
            "id": session_row["id"],
            "persona_key": session_row["persona_key"],
            "title": session_row["title"],
            "created_at": session_row["created_at"],
            "updated_at": session_row["updated_at"],
            "message_count": session_row["message_count"]
        },
        "messages": messages
    }

@app.put("/sessions/{session_id}")
def update_session(session_id: str, body: UpdateSessionBody):
    """Update a chat session (e.g., rename)."""
    title = (body.title or "").strip() or "Untitled"
    now = _now()
    with _DB_LOCK:
        c = _conn()
        cur = c.cursor()
        cur.execute("""
            UPDATE chat_sessions
            SET title = ?, updated_at = ?
            WHERE id = ?
        """, (title, now, session_id))
        if cur.rowcount == 0:
            c.close()
            raise HTTPException(status_code=404, detail="Session not found.")
        c.commit()
        c.close()
    return {"ok": True, "id": session_id, "title": title, "updated_at": now}

@app.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    """Delete a chat session and all its messages."""
    with _DB_LOCK:
        c = _conn()
        cur = c.cursor()
        # Check if session exists
        cur.execute("SELECT id FROM chat_sessions WHERE id = ?", (session_id,))
        if not cur.fetchone():
            c.close()
            raise HTTPException(status_code=404, detail="Session not found.")
        # Delete messages first (cascade should handle this, but being explicit)
        cur.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        # Delete session
        cur.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
        c.commit()
        c.close()
    return {"ok": True}

@app.post("/sessions/{session_id}/messages")
def add_message(session_id: str, body: AppendMessageBody):
    """Add a message to a chat session."""
    message_id = _generate_message_id()
    timestamp = body.ts or _now()
    with _DB_LOCK:
        c = _conn()
        cur = c.cursor()
        # Verify session exists
        cur.execute("SELECT id FROM chat_sessions WHERE id = ?", (session_id,))
        if not cur.fetchone():
            c.close()
            raise HTTPException(status_code=404, detail="Session not found.")
        # Insert message
        cur.execute("""
            INSERT INTO messages (id, session_id, role, content, timestamp, latency_ms)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (message_id, session_id, body.role, body.content, timestamp, body.latency_ms))
        # Update session timestamp
        cur.execute("""
            UPDATE chat_sessions SET updated_at = ? WHERE id = ?
        """, (_now(), session_id))
        c.commit()
        c.close()
    return {"ok": True, "message_id": message_id}

@app.delete("/sessions/{session_id}/messages")
def clear_session_messages(session_id: str):
    """Clear all messages from a chat session (keep the session)."""
    with _DB_LOCK:
        c = _conn()
        cur = c.cursor()
        # Check if session exists
        cur.execute("SELECT id FROM chat_sessions WHERE id = ?", (session_id,))
        if not cur.fetchone():
            c.close()
            raise HTTPException(status_code=404, detail="Session not found.")
        # Delete all messages for this session
        cur.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        # Update session updated_at timestamp
        cur.execute("UPDATE chat_sessions SET updated_at = ? WHERE id = ?", (_now(), session_id))
        c.commit()
        c.close()
    return {"ok": True}

@app.get("/sessions/{session_id}/export")
def export_session(session_id: str):
    """Export a chat session as JSON."""
    session_data = get_session(session_id)

    # Get persona info
    persona_card = get_persona_card(session_data["session"]["persona_key"])
    if not persona_card:
        raise HTTPException(status_code=400, detail="Persona not found.")

    export_data = {
        "version": "1.0",
        "exported_at": _now(),
        "app_version": "1.0.0",
        "persona": {
            "key": persona_card.get("key"),
            "display_name": persona_card.get("display_name"),
            "style": persona_card.get("style")
        },
        "session": session_data["session"],
        "messages": session_data["messages"]
    }

    return export_data

@app.post("/sessions/import")
def import_session(body: ImportBody):
    """Import a chat session from exported JSON."""
    data = body.data

    # Validate data structure
    if not data.version or not data.persona or not data.session or not data.messages:
        raise HTTPException(status_code=400, detail="Invalid import data structure.")

    # Verify persona exists (data.persona is a dict from JSON)
    persona_key = data.persona.get("key") if isinstance(data.persona, dict) else getattr(data.persona, 'key', None)
    if not persona_key or not get_persona_card(persona_key):
        raise HTTPException(status_code=400, detail=f"Persona '{persona_key}' not found.")

    session_id = _generate_session_id() if body.create_new_session else data.session.get("id") if isinstance(data.session, dict) else getattr(data.session, 'id', None)
    now = _now()

    with _DB_LOCK:
        c = _conn()
        cur = c.cursor()

        # Create session
        session_title = data.session.get("title") if isinstance(data.session, dict) else getattr(data.session, 'title', 'Imported Chat')
        session_created_at = data.session.get("created_at") if isinstance(data.session, dict) else getattr(data.session, 'created_at', now)

        cur.execute("""
            INSERT INTO chat_sessions (id, persona_key, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            session_id,
            persona_key,
            session_title or 'Imported Chat',
            session_created_at or now,
            now
        ))

        # Insert messages
        for msg in data.messages:
            message_id = _generate_message_id()
            cur.execute("""
                INSERT INTO messages (id, session_id, role, content, timestamp, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                message_id,
                session_id,
                msg.get("role") if isinstance(msg, dict) else getattr(msg, 'role', 'user'),
                msg.get("content") if isinstance(msg, dict) else getattr(msg, 'content', ''),
                msg.get("timestamp") if isinstance(msg, dict) else getattr(msg, 'timestamp', now),
                msg.get("latency_ms") if isinstance(msg, dict) else getattr(msg, 'latency_ms', None)
            ))

        c.commit()
        c.close()

    return {"ok": True, "session_id": session_id}

# ----------------- Optional tiny health check (roadmap "Now") -----------------
@app.get("/health")
def health():
    try:
        base = get_ollama_base()
        model = get_persona_model()
        # DB ping
        with _DB_LOCK:
            c = _conn()
            cur = c.cursor()
            cur.execute("SELECT 1")
            c.close()
        return {"status": "ok", "model": model, "db": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

# ----------------- Initialize on startup -----------------
print("Initializing FastAPI server...")
try:
    assert_model_available(get_ollama_base(), get_persona_model())
    print("Model check passed.")
except Exception as e:
    print(f"Model check failed: {e}")
    raise

try:
    _init_db()
    print("Database initialized.")
except Exception as e:
    print(f"Database init failed: {e}")
    raise

# Initialize Brave MCP client
try:
    _init_brave_client()
    if _brave_client:
        enabled_rarities = get_brave_enabled_rarities()
        print(f"Brave MCP enabled for rarities: {', '.join(enabled_rarities)}")
    else:
        print("Brave MCP disabled (web search not available)")
except Exception as e:
    print(f"Brave MCP initialization warning: {e}")
    # Non-critical, continue without web search

# Initialize MongoDB MCP client
try:
    _init_mongodb_client()
    if _mongodb_client:
        enabled_rarities = get_mongodb_enabled_rarities()
        print(f"MongoDB MCP enabled for rarities: {', '.join(enabled_rarities)}")
    else:
        print("MongoDB MCP disabled (no URI or feature flag off)")
except Exception as e:
    print(f"MongoDB MCP initialization warning: {e}")
    # Non-critical, continue without MongoDB access

# Best-effort no-op refresh (non-blocking). If another process holds the lock, we just skip.
try:
    result = ensure_all_summaries_serialized(timeout_sec=0.01, poll_sec=0.01)
    print(f"Summaries check completed: {result}")
except Exception as e:
    print(f"Summary check failed: {e}")
    # Don't raise here as it's non-critical

print("FastAPI server initialization complete.")

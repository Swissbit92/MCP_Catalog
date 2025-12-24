# Hardcoded Values Assessment
**Date:** December 24, 2025
**Status:** Comprehensive analysis of configuration gaps

## Executive Summary

Found **15 hardcoded values** that should be externalized to `.env` or `config.py` for better configurability and maintainability.

**Priority Breakdown:**
- 🔴 **Critical (4):** Core functionality settings that users may need to tune
- 🟡 **Medium (7):** Feature-specific settings that affect behavior
- 🟢 **Low (4):** Technical defaults that rarely need changing

---

## 🔴 Critical Priority

### 1. **Embedding Model** (Phase 3)
**Current:** Hardcoded `"nomic-embed-text:latest"` in multiple places
**Locations:**
- `src/coordinator/memory_rag.py:38` - Default parameter
- `src/coordinator/startup.py:225` - Initialization

**Impact:** Users cannot use alternative embedding models (e.g., `all-MiniLM-L6-v2`, custom models)

**Recommendation:**
```python
# config.py
class MemorySettings(BaseSettings):
    embedding_model: str = Field(
        default="nomic-embed-text:latest",
        description="Ollama embedding model for RAG semantic search",
        alias="MEMORY_EMBEDDING_MODEL"
    )

# .env
MEMORY_EMBEDDING_MODEL=nomic-embed-text:latest
```

**Files to modify:**
- `src/coordinator/config.py` - Add MemorySettings class
- `src/coordinator/memory_rag.py` - Use `get_embedding_model()`
- `src/coordinator/startup.py` - Use `get_embedding_model()`

---

### 2. **Summarization Trigger Interval**
**Current:** Hardcoded `30` messages
**Location:** `src/coordinator/routes/chat.py:201`

```python
if messages_since_summary >= 30:
```

**Impact:** Users cannot tune memory compression frequency for different use cases (e.g., faster summarization for testing, slower for production)

**Recommendation:**
```python
# config.py
class MemorySettings(BaseSettings):
    summarization_interval: int = Field(
        default=30,
        ge=5,
        le=100,
        description="Number of messages before triggering auto-summarization",
        alias="MEMORY_SUMMARIZATION_INTERVAL"
    )

# .env
MEMORY_SUMMARIZATION_INTERVAL=30
```

---

### 3. **Fact Extraction Trigger Interval** (Phase 3)
**Current:** Hardcoded `10` messages
**Location:** `src/coordinator/routes/chat.py:440`

```python
if user_profile_repo and len(db_messages) % 10 == 0:
```

**Impact:** Users cannot tune user profile building frequency

**Recommendation:**
```python
# config.py
class MemorySettings(BaseSettings):
    fact_extraction_interval: int = Field(
        default=10,
        ge=5,
        le=50,
        description="Number of messages before triggering fact extraction",
        alias="MEMORY_FACT_EXTRACTION_INTERVAL"
    )

# .env
MEMORY_FACT_EXTRACTION_INTERVAL=10
```

---

### 4. **LLM Temperature for Specific Operations**
**Current:** Multiple hardcoded temperature values
**Locations:**
- `src/coordinator/services/first_person_service.py:93` - `0.2` for rewrites
- `src/coordinator/routes/chat.py:217` - `0.3` for summarization
- `src/coordinator/routes/chat.py:454` - `0.3` for fact extraction

**Impact:** Users cannot tune creativity/consistency trade-off for specific operations

**Recommendation:**
```python
# config.py
class OllamaSettings(BaseSettings):
    # ... existing fields ...

    temp_rewrite: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Temperature for first-person rewrites",
        alias="OLLAMA_TEMP_REWRITE"
    )
    temp_summarization: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Temperature for conversation summarization",
        alias="OLLAMA_TEMP_SUMMARIZATION"
    )
    temp_fact_extraction: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Temperature for fact extraction",
        alias="OLLAMA_TEMP_FACT_EXTRACTION"
    )

# .env
OLLAMA_TEMP_REWRITE=0.2
OLLAMA_TEMP_SUMMARIZATION=0.3
OLLAMA_TEMP_FACT_EXTRACTION=0.3
```

---

## 🟡 Medium Priority

### 5. **RSI Thresholds** (Technical Indicators)
**Current:** Hardcoded `70` (overbought) and `30` (oversold)
**Locations:**
- `src/coordinator/services/mongodb_handlers.py:96-97`
- `src/coordinator/services/mongodb_handlers.py:295`

```python
rsi_signal = "Overbought" if rsi > 70 else "Oversold" if rsi < 30 else "Neutral"
```

**Impact:** Users cannot customize technical analysis thresholds for different trading strategies

**Recommendation:**
```python
# config.py
class MongoDBSettings(BaseSettings):
    # ... existing fields ...

    rsi_overbought: int = Field(
        default=70,
        ge=50,
        le=90,
        description="RSI overbought threshold",
        alias="MONGODB_RSI_OVERBOUGHT"
    )
    rsi_oversold: int = Field(
        default=30,
        ge=10,
        le=50,
        description="RSI oversold threshold",
        alias="MONGODB_RSI_OVERSOLD"
    )

# .env
MONGODB_RSI_OVERBOUGHT=70
MONGODB_RSI_OVERSOLD=30
```

---

### 6. **Importance Scoring Weights** (Memory Manager)
**Current:** Hardcoded multipliers in `MessageImportanceScorer`
**Location:** `src/coordinator/memory_manager.py:70-100`

```python
# Name introduction: 6.0x
# Personal info: 4.0x
# User messages: 1.5x
# Questions: 1.3x / 1.2x
# Length threshold: 200 chars
```

**Impact:** Users cannot tune memory importance algorithm for different conversation styles

**Recommendation:**
```python
# config.py
class MemorySettings(BaseSettings):
    # ... existing fields ...

    importance_name_boost: float = Field(default=6.0, ge=1.0, le=10.0)
    importance_personal_boost: float = Field(default=4.0, ge=1.0, le=10.0)
    importance_user_boost: float = Field(default=1.5, ge=1.0, le=5.0)
    importance_question_boost: float = Field(default=1.3, ge=1.0, le=3.0)
    importance_length_threshold: int = Field(default=200, ge=50, le=500)

# .env
MEMORY_IMPORTANCE_NAME_BOOST=6.0
MEMORY_IMPORTANCE_PERSONAL_BOOST=4.0
# ... etc
```

**Note:** This might be over-engineering. Consider leaving as class constants unless users request tuning.

---

### 7. **RAG Search Parameters** (Phase 3)
**Current:** Hardcoded in function signatures
**Location:** `src/coordinator/memory_rag.py`

```python
def search_memory(self, session_id: str, query: str, k: int = 10, min_relevance: float = 0.5)
def get_relevant_context(self, session_id: str, query: str, max_messages: int = 10)
```

**Impact:** Users cannot tune semantic search recall vs precision trade-off

**Recommendation:**
```python
# config.py
class MemorySettings(BaseSettings):
    # ... existing fields ...

    rag_search_k: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of semantic search results to retrieve",
        alias="MEMORY_RAG_SEARCH_K"
    )
    rag_min_relevance: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum relevance score for RAG results (0.0-1.0)",
        alias="MEMORY_RAG_MIN_RELEVANCE"
    )

# .env
MEMORY_RAG_SEARCH_K=10
MEMORY_RAG_MIN_RELEVANCE=0.5
```

---

### 8. **Critical Score Threshold** (Memory Manager)
**Current:** Hardcoded `4.0`
**Location:** `src/coordinator/memory_manager.py:51`

```python
CRITICAL_SCORE_THRESHOLD = 4.0
```

**Impact:** Users cannot tune which messages are "never dropped"

**Recommendation:**
```python
# config.py
class MemorySettings(BaseSettings):
    critical_message_threshold: float = Field(
        default=4.0,
        ge=1.0,
        le=10.0,
        description="Importance score threshold for critical messages",
        alias="MEMORY_CRITICAL_THRESHOLD"
    )

# .env
MEMORY_CRITICAL_THRESHOLD=4.0
```

---

### 9. **Context Selection - First/Last Messages**
**Current:** Hardcoded in memory selection logic
**Location:** `src/coordinator/memory_manager.py` (likely in MemoryManager class)

Typically: "Always include first 3 and last 10 messages"

**Impact:** Users cannot tune conversation window shape

**Recommendation:**
```python
# config.py
class MemorySettings(BaseSettings):
    context_first_n: int = Field(default=3, ge=0, le=10)
    context_last_n: int = Field(default=10, ge=5, le=30)

# .env
MEMORY_CONTEXT_FIRST_N=3
MEMORY_CONTEXT_LAST_N=10
```

---

### 10. **Summarization Batch Size**
**Current:** Hardcoded `30` messages per summary
**Location:** `src/coordinator/routes/chat.py:207-209`

```python
start_idx = messages_summarized
end_idx = start_idx + 30
messages_to_summarize = all_messages[start_idx:end_idx]
```

**Impact:** This is directly tied to `MEMORY_SUMMARIZATION_INTERVAL` but worth noting as a separate concern

**Recommendation:** Use the same config value as trigger interval (no separate config needed)

---

### 11. **Conversation Summarizer - Summary Count**
**Current:** Hardcoded multiplication by 30
**Location:** `src/coordinator/routes/chat.py:197-198`

```python
summary_count = summary_repo.count_summaries(session_id)
messages_summarized = summary_count * 30
```

**Impact:** This assumes `MEMORY_SUMMARIZATION_INTERVAL=30`. Should use the config value.

**Recommendation:** No new config needed, just use existing `MEMORY_SUMMARIZATION_INTERVAL`

---

## 🟢 Low Priority

### 12. **Sampling Presets** (Preset Library)
**Current:** Hardcoded temperature values in sampling presets
**Location:** `src/coordinator/models/sampling_presets.py:78-108`

```python
"balanced": temperature=0.9
"precise": temperature=0.5
"deterministic": temperature=0.1
```

**Impact:** Low - these are intentional presets, not configuration

**Recommendation:** **Leave as-is**. Presets are semantic labels, not configuration. Users can override per-persona.

---

### 13. **Default Indicators** (MongoDB)
**Current:** Hardcoded indicator list
**Location:** `src/coordinator/services/mongodb_handlers.py:84-86`

```python
indicators_to_include = include_indicators or [
    "RSI", "MACD_Line", "BB_High", "BB_Low", "EMA_20", "EMA_50"
]
```

**Impact:** Low - this is a reasonable default, can be overridden via function parameter

**Recommendation:** **Leave as-is**. This is application logic, not configuration.

---

### 14. **Cache Test Values**
**Current:** Various hardcoded test values in `cache.py`
**Location:** `src/coordinator/cache.py:223-279`

**Impact:** None - these are test cases

**Recommendation:** **Leave as-is**. Test constants should not be configurable.

---

### 15. **Token Budget Warning Threshold**
**Current:** Likely hardcoded `90%` threshold somewhere
**Location:** Not found in grep (might be in commented code or removed)

**Impact:** Unknown - need to verify if this feature is still active

**Recommendation:** Investigate further if token budget warnings are implemented.

---

## Implementation Recommendations

### Phase 1: Critical (Week 1)
1. Add `MemorySettings` class to `config.py`
2. Externalize embedding model
3. Externalize summarization/fact extraction intervals
4. Externalize operation-specific temperatures

**Estimated effort:** 2-3 hours

### Phase 2: Medium (Week 2)
5. Externalize RSI thresholds
6. Externalize RAG search parameters
7. Externalize critical message threshold

**Estimated effort:** 1-2 hours

### Phase 3: Optional (Future)
8. Externalize importance scoring weights (if users request)
9. Externalize context selection parameters

**Estimated effort:** 1 hour

---

## Proposed `.env` Additions

```bash
# ============================================================================
# Memory & RAG Configuration (Phase 3)
# ============================================================================

# Embedding model for semantic search
MEMORY_EMBEDDING_MODEL=nomic-embed-text:latest

# Summarization and fact extraction triggers
MEMORY_SUMMARIZATION_INTERVAL=30        # Messages before auto-summarize
MEMORY_FACT_EXTRACTION_INTERVAL=10      # Messages before fact extraction

# RAG search parameters
MEMORY_RAG_SEARCH_K=10                  # Number of semantic search results
MEMORY_RAG_MIN_RELEVANCE=0.5            # Minimum relevance score (0.0-1.0)

# Memory importance scoring
MEMORY_CRITICAL_THRESHOLD=4.0           # Score threshold for critical messages
MEMORY_CONTEXT_FIRST_N=3                # Always include first N messages
MEMORY_CONTEXT_LAST_N=10                # Always include last N messages

# ============================================================================
# LLM Temperature Overrides (Operation-Specific)
# ============================================================================

OLLAMA_TEMP_REWRITE=0.2                 # First-person rewrites
OLLAMA_TEMP_SUMMARIZATION=0.3           # Conversation summaries
OLLAMA_TEMP_FACT_EXTRACTION=0.3         # User profile fact extraction

# ============================================================================
# MongoDB Technical Analysis Thresholds
# ============================================================================

MONGODB_RSI_OVERBOUGHT=70               # RSI overbought threshold
MONGODB_RSI_OVERSOLD=30                 # RSI oversold threshold
```

---

## Benefits of Externalization

### For Users:
- ✅ Fine-tune memory system for their use case (dev vs prod, testing vs deployment)
- ✅ Experiment with different embedding models without code changes
- ✅ Optimize performance (faster summarization for testing, slower for production)
- ✅ Customize technical analysis for their trading strategy

### For Developers:
- ✅ Easier A/B testing of parameter values
- ✅ Environment-specific configuration (dev/staging/prod)
- ✅ No code recompilation for parameter tuning
- ✅ Clear documentation of tunable parameters

### For Testing:
- ✅ Override intervals for faster test execution (e.g., `MEMORY_SUMMARIZATION_INTERVAL=5`)
- ✅ Test with different embedding models
- ✅ Simulate different memory behaviors

---

## Notes

1. **Backward Compatibility:** All new config values should have sensible defaults matching current hardcoded values
2. **Validation:** Use Pydantic Field validators to ensure values are within acceptable ranges
3. **Documentation:** Update CLAUDE.md with new environment variables
4. **.env.example:** Add new variables with comments explaining their purpose
5. **Testing:** Create tests to verify config loading and fallback to defaults

---

## Files Requiring Changes

**If implementing all recommendations:**

### Core Files:
- `src/coordinator/config.py` - Add MemorySettings class (~100 lines)
- `src/coordinator/memory_rag.py` - Use config instead of hardcoded values (~5 changes)
- `src/coordinator/memory_manager.py` - Use config for weights (~10 changes)
- `src/coordinator/routes/chat.py` - Use config for intervals (~3 changes)
- `src/coordinator/services/mongodb_handlers.py` - Use config for RSI thresholds (~2 changes)
- `src/coordinator/services/first_person_service.py` - Use config for temperature (~1 change)
- `src/coordinator/startup.py` - Use config for embedding model (~1 change)

### Documentation:
- `CLAUDE.md` - Document new env vars
- `.env.example` - Add new variables with defaults
- `README.md` - Update configuration section

### Tests:
- Create `tests/backend/coordinator/test_memory_config.py` - Validate new config values

**Total estimated LOC:** ~150 lines of new code + ~30 lines of changes

---

## Priority Recommendation

**Start with Phase 1 (Critical)** - These are the most impactful and most likely to be needed by users.

The embedding model in particular is a blocker for users who want to:
- Use different embedding models (e.g., multilingual embeddings)
- Test with faster/smaller embeddings for development
- Optimize for specific use cases (accuracy vs speed)

The temperature overrides enable:
- Deterministic testing (set all to 0.1)
- More creative summaries (increase to 0.5)
- Consistent fact extraction (keep at 0.3)

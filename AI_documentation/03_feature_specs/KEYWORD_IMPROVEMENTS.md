# Intent Classification Keyword Improvements

**Based on**: Comprehensive test results (89.7% accuracy)
**Target**: 93%+ accuracy
**Estimated Effort**: 1-2 hours
**Priority**: HIGH

---

## Changes to Implement

### File: `src/coordinator/tool_definitions.py`

#### 1. Expand NEWS_KEYWORDS (For Brave MCP)

**Current Issues**:
- Missing "trending", "happening", "new with" patterns
- Not catching sentiment/opinion queries
- Weak on "what are people saying" type questions

**Add these keywords**:

```python
NEWS_KEYWORDS = [
    # Existing keywords (keep all)
    "news", "latest", "recent", "update",
    "breaking", "headline", "report",

    # NEW: Trending/popularity
    "trending", "trend", "popular", "viral",
    "hot topic", "buzz", "talk of",

    # NEW: Happening/current events
    "happening", "occurring", "going on",
    "what's new", "new with", "latest on",
    "developments", "progress",

    # NEW: Expert opinions/predictions
    "saying", "experts say", "analysts say",
    "predictions", "forecasts", "outlook",
    "opinions", "views", "thoughts on",
    "expect", "expecting", "anticipated",

    # NEW: Social/community sentiment
    "talking about", "discussing", "debate",
    "community", "twitter", "reddit", "social",
    "sentiment", "mood", "feeling about",

    # NEW: Market commentary
    "commentary", "analysis article", "opinion piece",
    "market watch", "crypto watch",
]
```

**Expected Impact**: Brave MCP accuracy 82.5% → 90%+

---

#### 2. Expand MONGODB_KEYWORDS (For MongoDB MCP)

**Current Issues**:
- Missing "value", "worth", "trading at" variations
- Not catching "trend analysis" queries
- Weak on natural language price questions

**Add these keywords**:

```python
MONGODB_KEYWORDS = [
    # Existing keywords (keep all)
    "price", "btc", "bitcoin",

    # NEW: Value/worth
    "value", "valued", "valued at",
    "worth", "worth now", "what's it worth",
    "how much is", "what is it",

    # NEW: Trading phrases
    "trading at", "trading for", "trades at",
    "going for", "selling for", "buy",
    "cost", "costs",

    # NEW: Technical analysis
    "analysis", "trend analysis", "outlook",
    "technical outlook", "market analysis",
    "indicators", "signals",

    # NEW: Current state
    "current value", "right now", "at the moment",
    "as of", "currently",

    # NEW: Historical
    "historical", "history", "past", "ago",
    "was", "were", "been",

    # NEW: My data (personal queries)
    "my", "mine", "purchased", "bought",
    "portfolio", "holdings",
]
```

**Expected Impact**: MongoDB MCP accuracy 86.7% → 92%+

---

### 3. Fix Rare Persona Rarity-Gating

**Current Issue**:
Rare personas classify MongoDB queries as `NEEDS_WEB_SEARCH` instead of `NEEDS_NEITHER`.

**Location**: `classify_query_intent()` in `tool_definitions.py`

**Current Code**:
```python
def classify_query_intent(query: str, persona_rarity: str) -> QueryIntent:
    # ... classification logic ...

    if has_mongodb:
        if persona_rarity in get_mongodb_enabled_rarities():
            # Has MongoDB access
            if has_web_search and persona_rarity in get_brave_enabled_rarities():
                return QueryIntent.NEEDS_BOTH
            return QueryIntent.NEEDS_MONGODB
        # else: Falls through to web search check (WRONG!)
```

**Fixed Code**:
```python
def classify_query_intent(query: str, persona_rarity: str) -> QueryIntent:
    # ... classification logic ...

    if has_mongodb:
        if persona_rarity in get_mongodb_enabled_rarities():
            # Has MongoDB access
            if has_web_search and persona_rarity in get_brave_enabled_rarities():
                return QueryIntent.NEEDS_BOTH
            return QueryIntent.NEEDS_MONGODB
        else:
            # No MongoDB access - if web search is also needed, return WEB_SEARCH
            # Otherwise return NEITHER (don't fallback to web search for MongoDB queries)
            if has_web_search and persona_rarity in get_brave_enabled_rarities():
                return QueryIntent.NEEDS_WEB_SEARCH
            return QueryIntent.NEEDS_NEITHER  # <-- ADD THIS
```

**Expected Impact**: Rare persona accuracy 85.6% → 92%+

---

## Detailed Changes

### Change 1: Add Trending Keywords

**Rationale**: Test showed "What's trending in Bitcoin?" not being detected

**Before**:
```python
NEWS_KEYWORDS = [
    "news", "latest", "recent", "update", "breaking",
    # ...
]
```

**After**:
```python
NEWS_KEYWORDS = [
    "news", "latest", "recent", "update", "breaking",
    # Add trending patterns
    "trending", "trend", "popular", "viral", "hot topic",
    # ...
]
```

**Fixes These Queries**:
- "What's trending in Bitcoin?" ✓
- "Bitcoin trending topics" ✓
- "Popular crypto news" ✓

---

### Change 2: Add "Happening/New" Keywords

**Rationale**: "What's happening with crypto regulations?" not detected

**Add**:
```python
"happening", "occurring", "going on",
"what's new", "new with", "latest on",
```

**Fixes These Queries**:
- "What's happening with crypto regulations?" ✓
- "What's new with Ethereum?" ✓
- "What's going on with Bitcoin?" ✓

---

### Change 3: Add Opinion/Sentiment Keywords

**Rationale**: "What are crypto experts saying?" not detected

**Add**:
```python
"saying", "experts say", "analysts say",
"talking about", "discussing", "sentiment",
"opinions", "views", "thoughts on",
```

**Fixes These Queries**:
- "What are crypto experts saying today?" ✓
- "What's the crypto community talking about?" ✓
- "What's the sentiment on Bitcoin?" ✓

---

### Change 4: Add Value/Worth Keywords

**Rationale**: "Current BTC value" and "What is Bitcoin worth now?" not detected

**Add**:
```python
"value", "valued", "valued at",
"worth", "worth now", "what's it worth",
```

**Fixes These Queries**:
- "Current BTC value" ✓
- "What is Bitcoin worth now?" ✓
- "Show me Bitcoin's current value" ✓

---

### Change 5: Add Trading Phrase Keywords

**Rationale**: "What's Bitcoin trading at?" not detected

**Add**:
```python
"trading at", "trading for", "trades at",
"going for", "selling for",
```

**Fixes These Queries**:
- "What's Bitcoin trading at?" ✓
- "What's BTC going for?" ✓

---

### Change 6: Add Analysis Keywords

**Rationale**: "Bitcoin trend analysis" not detected

**Add**:
```python
"analysis", "trend analysis", "outlook",
"technical outlook", "market analysis",
```

**Fixes These Queries**:
- "Bitcoin trend analysis" ✓
- "Show me Bitcoin technical outlook" ✓

---

## Testing After Changes

### Re-run Test Suite
```bash
python test_intent_classification_comprehensive.py
```

### Expected Results
```
Overall Accuracy: 93%+ (was 89.7%)
- PURE_LLM:      100% (no change)
- BRAVE_MCP:     90%+ (was 82.5%)
- MONGODB_MCP:   92%+ (was 86.7%)

By Rarity:
- COMMON:        100% (no change)
- RARE:          92%+ (was 85.6%)
- EPIC:          93%+ (was 86.7%)
- LEGENDARY:     93%+ (was 86.7%)
```

---

## Validation Checklist

Before deploying:
- [ ] Run comprehensive test suite
- [ ] Verify no new false positives introduced
- [ ] Check that PURE_LLM stays at 100%
- [ ] Test with real user queries (manual testing)
- [ ] Verify rarity-gating still works correctly

---

## Rollback Plan

If changes cause issues:

1. **Immediate Rollback**:
   ```bash
   git checkout src/coordinator/tool_definitions.py
   ```

2. **Selective Rollback**: Remove problematic keywords one at a time

3. **Monitoring**: Watch for user complaints about incorrect classifications

---

## Future Improvements

After achieving 93%+ accuracy:

1. **Add Query Logging**
   - Track all classifications in production
   - Identify real-world misclassifications
   - Use data for iterative improvement

2. **A/B Testing**
   - Test different keyword sets
   - Measure user satisfaction
   - Optimize based on actual usage

3. **ML-Based Classification** (Long-term)
   - Use Ollama to classify intent
   - More flexible than keyword matching
   - Trade-off: slower, less deterministic

4. **Context-Aware Classification**
   - Consider conversation history
   - "What about the price?" → MongoDB (if previous message was about Bitcoin)
   - "Tell me more" → Use previous classification

---

## Success Criteria

✅ **Minimum Acceptable**: 90% overall accuracy
🎯 **Target**: 93% overall accuracy
⭐ **Stretch Goal**: 95% overall accuracy

**Current**: 89.7% → **Target**: 93%+ after these changes

---

## Notes

- Keep all existing keywords (don't remove any)
- Keywords are case-insensitive
- Partial matches work (e.g., "trending" matches "What's trending")
- More specific keywords take precedence (layer 2 & 3)


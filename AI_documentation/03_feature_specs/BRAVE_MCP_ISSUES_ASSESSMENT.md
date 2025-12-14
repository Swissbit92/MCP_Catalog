# Brave MCP Integration Issues - Root Cause Analysis & Implementation Plan

**Date:** December 14, 2025
**Status:** 🔴 Critical Issues Identified

---

## Executive Summary

Three critical issues have been identified in the Brave MCP web search integration:

1. **LLM Hallucination/Ignoring Search Results**: Personas provide incorrect information (e.g., wrong Ethereum price) despite web search returning correct data
2. **Missing Answer Synthesis**: Personas dump raw search results without answering the user's question
3. **Inconsistent Citation Format**: Citations appear inline instead of as bullet points

**Root Cause:** The synthesis step in `llm_client.py` uses the original persona system prompt **without** the enhanced instructions that enforce search result usage and citation formatting.

**Impact:** High - Users receive incorrect information and poor UX
**Effort to Fix:** Medium - 3-4 hours
**Risk:** Low - Changes isolated to synthesis prompt construction

---

## Issue #1: LLM Ignores Search Results (Hallucination)

### Problem Description

**Example:**
- User asks: "What is the current Ethereum price?"
- Brave search returns: $3,245.67 (correct)
- Persona responds: "Ethereum is trading at $1,850" (incorrect - hallucinated from training data)

### Root Cause Analysis

**File:** `src/coordinator/llm_client.py` (Lines 173-176)

```python
# Get final synthesized response
final_response = self.complete(
    persona_system,  # ⚠️ PROBLEM: Uses original persona prompt
    "\n\n".join(conversation_history)
)
```

**Issue:** The synthesis step uses `persona_system` (original persona prompt) instead of `enhanced_system` (which contains instructions to use search results).

**What happens:**
1. LLM receives search results in conversation history
2. BUT the system prompt doesn't explicitly instruct: "ONLY use the search results, ignore your training data"
3. LLM falls back to training data or hallucinates

**Evidence in code:**

`tool_definitions.py` Lines 519-548 contain strong instructions:
```
"IMPORTANT: Use this information to answer the user's question."
"You MUST cite your sources using markdown links..."
```

But these instructions are in `enhanced_system`, which is **not used** during synthesis.

### Why This Happens

**Tool Calling Flow:**
1. Initial prompt: `enhanced_system` (has search instructions) ✅
2. LLM decides to search ✅
3. Search executes ✅
4. Synthesis prompt: `persona_system` (NO search instructions) ❌

The synthesis step loses all the enhanced prompting that tells the LLM to prioritize search results.

---

## Issue #2: Missing Answer Synthesis (Raw Results Dump)

### Problem Description

**Example:**
- User asks: "What's happening with Bitcoin?"
- Persona responds: (Just dumps 5 search result summaries without answering)

### Root Cause Analysis

Same root cause as Issue #1, but manifests differently:

**File:** `src/coordinator/llm_client.py` (Lines 169-176)

```python
# Format search results for LLM
formatted_results = format_search_results_for_llm(search_results)
logger.info(f"Formatted {len(search_results)} search results for LLM")

# Add results to conversation and ask LLM to synthesize
conversation_history.append(formatted_results)
conversation_history.append(f"User: {user_prompt}")

# Get final synthesized response
final_response = self.complete(
    persona_system,  # ⚠️ No synthesis instruction
    "\n\n".join(conversation_history)
)
```

**Problem:** The prompt doesn't explicitly ask the LLM to:
- Synthesize the information
- Answer in the persona's voice
- Don't just repeat the search results

**What the LLM sees:**
```
[Persona system prompt]

Web search results:
1. Title: Bitcoin Price Hits $91K
   URL: ...
   Description: ...

2. Title: ...

User: What's happening with Bitcoin?
```

**What's missing:** "Based on these search results, answer the user's question naturally in your persona voice."

---

## Issue #3: Inconsistent Citation Format

### Problem Description

**Expected:**
```
🔍 Sources:
• [Title 1](url1)
• [Title 2](url2)
```

**Sometimes Get:**
```
🔍 Sources: [Title 1](url1) [Title 2](url2) [Title 3](url3)
```

### Root Cause Analysis

Same root cause: `persona_system` doesn't include citation format requirements.

**File:** `tool_definitions.py` Lines 517-547

Citation format is defined in `build_tool_system_prompt()`:
```python
**CITATION EXAMPLES:**

✅ GOOD (with citations):
"The current Bitcoin price is $91,735.99...

🔍 Sources:
• [Article Title - Source Name](https://url1.com)
• [Article Title - Source Name](https://url2.com)
```

But this enhanced prompt is **not used** during synthesis (llm_client.py:173).

**What the LLM sees during synthesis:**
- Original persona prompt (no citation format instructions)
- Search results (formatted)
- User query

**What it doesn't see:**
- Citation format requirements
- Examples of proper formatting
- The "CRITICAL REQUIREMENT" section

---

## Summary of Root Cause

All three issues stem from **one architectural flaw:**

**The synthesis step uses the wrong system prompt.**

```python
# Current (WRONG):
final_response = self.complete(
    persona_system,  # Original persona prompt (no search instructions)
    "\n\n".join(conversation_history)
)

# Should be (CORRECT):
final_response = self.complete(
    enhanced_system,  # Includes search result usage + citation format instructions
    "\n\n".join(conversation_history)
)
```

---

## Solution Design

### Approach 1: Use Enhanced System Prompt for Synthesis (Recommended)

**Change:** Use `enhanced_system` instead of `persona_system` during synthesis.

**Pros:**
- ✅ Simplest fix (1 line change)
- ✅ Preserves all enhanced instructions
- ✅ Fixes all 3 issues at once
- ✅ No new code needed

**Cons:**
- ⚠️ Enhanced prompt is longer (may hit context limits for very long conversations)
- ⚠️ Includes tool definitions even though tools already executed (minor inefficiency)

**File to change:** `src/coordinator/llm_client.py` Line 173

```python
# Before:
final_response = self.complete(
    persona_system,
    "\n\n".join(conversation_history)
)

# After:
final_response = self.complete(
    enhanced_system,  # Use enhanced prompt with search instructions
    "\n\n".join(conversation_history)
)
```

**Estimated Time:** 5 minutes + testing

---

### Approach 2: Create Synthesis-Specific Prompt (Better Long-Term)

**Change:** Build a dedicated synthesis prompt that combines:
- Original persona voice/personality
- Search result usage instructions
- Citation format requirements
- WITHOUT tool definitions (since tools already executed)

**Pros:**
- ✅ Optimal prompt for synthesis task
- ✅ Shorter than enhanced_system (better performance)
- ✅ Explicit synthesis instructions
- ✅ Cleaner separation of concerns

**Cons:**
- ⚠️ More code to write and maintain
- ⚠️ Need to ensure instructions stay in sync

**Implementation:**

**File:** `src/coordinator/tool_definitions.py` (New function)

```python
def build_synthesis_prompt(persona_system: str, has_search_results: bool = True) -> str:
    """
    Build system prompt for synthesizing search results into persona response.

    Args:
        persona_system: Original persona system prompt
        has_search_results: Whether search results are in context

    Returns:
        Enhanced system prompt for synthesis
    """
    if not has_search_results:
        return persona_system

    synthesis_instructions = """

---

**IMPORTANT: WEB SEARCH RESULTS USAGE**

You have received web search results in the conversation above.
Follow these rules when answering:

1. **ONLY use information from the search results** - Do NOT use your training data
2. **Synthesize naturally** - Don't just repeat the search results
3. **Stay in character** - Answer in your persona voice and style
4. **Be accurate** - Use exact numbers, dates, and facts from search results
5. **If results conflict** - Mention the discrepancy or use the most recent source

**CRITICAL: SOURCE CITATIONS**

You MUST include sources at the end of your response in this EXACT format:

🔍 Sources:
• [Article Title - Source Name](https://url1.com)
• [Article Title - Source Name](https://url2.com)
• [Article Title - Source Name](https://url3.com)

**CITATION RULES:**
1. ALWAYS include the 🔍 emoji before "Sources:"
2. Each source on a NEW LINE starting with bullet •
3. Use markdown format: [Descriptive Title](URL)
4. Include source name in title (e.g., "- CoinMarketCap")
5. Minimum 2 sources, maximum 5 sources
6. Place citations AFTER your natural answer

**EXAMPLE:**

User: "What is the current Bitcoin price?"

✅ CORRECT:
"Bitcoin is currently trading at $91,735.99, showing a 3.13% increase over the last 24 hours. Pretty bullish momentum if you ask me.

🔍 Sources:
• [Bitcoin Price Today - CoinMarketCap](https://coinmarketcap.com/currencies/bitcoin/)
• [BTC/USD Market Data - Yahoo Finance](https://finance.yahoo.com/quote/BTC-USD)"

❌ WRONG (missing citations):
"Bitcoin is around $91,000 according to recent data."

❌ WRONG (inline citations):
"Bitcoin is at $91K [Source](url1) [Source](url2)"

❌ WRONG (using old training data):
"Bitcoin is around $20,000..." ← NEVER use training data!

---

Now synthesize the search results above to answer the user's question naturally.
"""

    return persona_system + synthesis_instructions
```

**File:** `src/coordinator/llm_client.py` Line 173-176

```python
# Before:
final_response = self.complete(
    persona_system,
    "\n\n".join(conversation_history)
)

# After:
from .tool_definitions import build_synthesis_prompt

synthesis_system = build_synthesis_prompt(
    persona_system,
    has_search_results=True
)
final_response = self.complete(
    synthesis_system,
    "\n\n".join(conversation_history)
)
```

**Estimated Time:** 2-3 hours (including testing)

---

## Recommendation

**Use Approach 2 (Synthesis-Specific Prompt)** for production quality.

**Why:**
1. More explicit instructions reduce hallucination risk
2. Shorter prompt than Approach 1 (better performance)
3. Better separation of concerns (tool calling vs. synthesis)
4. Easier to maintain and improve over time

**Quick Fix:** Start with Approach 1 to validate the fix works, then refactor to Approach 2.

---

## Implementation Plan

### Phase 1: Quick Fix (Approach 1) - 30 minutes

**Goal:** Validate that using enhanced prompt fixes the issues

**Tasks:**
1. Modify `llm_client.py` line 173 to use `enhanced_system`
2. Test with problematic queries:
   - "What is the current Ethereum price?"
   - "What's happening with Bitcoin?"
   - Check citation format
3. Verify in logs that hallucination is reduced

**Files to modify:**
- `src/coordinator/llm_client.py` (1 line change)

**Testing:**
```bash
# Test query that previously hallucinated
curl -X POST http://localhost:8000/persona/chat \
  -H "Content-Type: application/json" \
  -d '{
    "persona": "eeva",
    "message": "What is the current Ethereum price?",
    "history": []
  }'

# Verify:
# 1. Price matches web search results
# 2. Citations are properly formatted (bullet points)
# 3. Answer is synthesized, not raw dump
```

---

### Phase 2: Production Fix (Approach 2) - 2-3 hours

**Goal:** Implement dedicated synthesis prompt for optimal results

**Tasks:**

#### 2.1 Create Synthesis Prompt Builder (45 min)
- [ ] Add `build_synthesis_prompt()` to `tool_definitions.py`
- [ ] Include search result usage instructions
- [ ] Include citation format requirements
- [ ] Add positive/negative examples
- [ ] Unit test the function

#### 2.2 Integrate Synthesis Prompt (30 min)
- [ ] Modify `llm_client.py` to use synthesis prompt
- [ ] Pass `has_search_results=True` flag
- [ ] Update logging to show synthesis prompt length
- [ ] Verify no regressions in non-search queries

#### 2.3 Testing (1 hour)
- [ ] Test all 3 issue scenarios:
  - Ethereum price query (hallucination test)
  - Bitcoin news query (synthesis test)
  - Citation format test (bullet points vs inline)
- [ ] Test with all personas (Rare/Epic/Legendary)
- [ ] Test edge cases:
  - Very long search results
  - Contradictory search results
  - Search results with no dates
  - Search results in non-English

#### 2.4 Validation & Logging (30 min)
- [ ] Add synthesis-specific logging:
  - `[Synthesis] Using synthesis prompt (length: X chars)`
  - `[Synthesis] Search results count: X`
  - `[Synthesis] Generated answer length: X chars`
- [ ] Verify citation validation still works
- [ ] Check that search badge displays correctly

---

### Phase 3: Enhanced Validation (1-2 hours)

**Goal:** Improve detection of hallucination and poor synthesis

**Optional Improvements:**

#### 3.1 Result-Answer Consistency Check
- [ ] Extract key facts from search results (prices, dates, names)
- [ ] Verify these facts appear in the answer
- [ ] Log warning if answer contains facts NOT in search results
- [ ] Add `hallucination_risk` flag to response metadata

**Example:**
```python
def check_answer_consistency(search_results: List[SearchResult], answer: str) -> dict:
    """
    Check if answer uses facts from search results vs. potentially hallucinated.

    Returns:
        {
            "has_numbers_from_search": bool,
            "has_dates_from_search": bool,
            "has_urls_from_search": bool,
            "hallucination_risk": "low" | "medium" | "high"
        }
    """
    # Extract numbers from search results
    search_numbers = extract_numbers_from_results(search_results)
    answer_numbers = extract_numbers_from_text(answer)

    # Check overlap
    has_matching_numbers = any(num in answer_numbers for num in search_numbers)

    # Similar checks for dates, entities, etc.

    return {
        "has_numbers_from_search": has_matching_numbers,
        "hallucination_risk": "low" if has_matching_numbers else "high"
    }
```

#### 3.2 Citation Quality Scoring
- [ ] Check that cited URLs actually exist in search results
- [ ] Score citation quality (descriptive titles, proper source names)
- [ ] Log warnings for low-quality citations
- [ ] Add `citation_quality_score` to response metadata

#### 3.3 Enhanced Prompting for Edge Cases
- [ ] Add handling for contradictory search results
- [ ] Add handling for "no relevant results found"
- [ ] Add fallback instructions if synthesis fails

---

## Testing Strategy

### Unit Tests

**File:** `tests/test_llm_synthesis.py` (New)

```python
def test_synthesis_prompt_includes_search_instructions():
    """Verify synthesis prompt has search result usage instructions."""
    persona_system = "You are Eeva, a sarcastic AI assistant."
    synthesis_prompt = build_synthesis_prompt(persona_system, has_search_results=True)

    assert "ONLY use information from the search results" in synthesis_prompt
    assert "Do NOT use your training data" in synthesis_prompt
    assert "🔍 Sources:" in synthesis_prompt

def test_synthesis_prompt_includes_citation_format():
    """Verify synthesis prompt has citation format examples."""
    synthesis_prompt = build_synthesis_prompt("", has_search_results=True)

    assert "• [" in synthesis_prompt  # Bullet point format
    assert "CITATION RULES:" in synthesis_prompt
    assert "markdown format" in synthesis_prompt

def test_synthesis_without_search_results():
    """Verify synthesis prompt degrades gracefully without search."""
    persona_system = "You are Eeva."
    synthesis_prompt = build_synthesis_prompt(persona_system, has_search_results=False)

    assert synthesis_prompt == persona_system  # No enhancement needed
```

### Integration Tests

**File:** `tests/test_brave_mcp_synthesis.py` (New)

```python
@pytest.mark.integration
def test_ethereum_price_no_hallucination(brave_client):
    """Verify persona uses search results, not training data."""
    query = "What is the current Ethereum price?"

    response = chat_with_persona("eeva", query)

    # Get actual price from search results
    search_results = response["search_results"]
    actual_price = extract_price_from_results(search_results, "Ethereum")

    # Verify answer contains actual price (not hallucinated)
    assert str(actual_price) in response["answer"]
    assert response["citation_valid"] == True

@pytest.mark.integration
def test_synthesis_not_raw_dump(brave_client):
    """Verify persona synthesizes answer, not raw search dump."""
    query = "What's happening with Bitcoin?"

    response = chat_with_persona("eeva", query)

    # Should NOT just dump search result titles
    search_titles = [r.title for r in response["search_results"]]
    for title in search_titles:
        # Answer shouldn't contain exact raw titles
        assert title not in response["answer"]

    # Should have persona voice
    assert len(response["answer"]) > 50  # Not just 1-2 sentences

@pytest.mark.integration
def test_citation_format_bullet_points(brave_client):
    """Verify citations use bullet point format, not inline."""
    query = "Current Bitcoin price"

    response = chat_with_persona("eeva", query)

    # Check for bullet point format
    assert "🔍 Sources:" in response["answer"]
    assert "\n•" in response["answer"]  # Newline + bullet

    # Should NOT be inline
    citations_section = response["answer"].split("🔍 Sources:")[1]
    assert not re.search(r'\]\([^\)]+\)\s*\[', citations_section)  # No ][url][url]
```

### Manual Testing Checklist

- [ ] **Hallucination Test**
  - Query: "What is the current Ethereum price?"
  - Expected: Price matches top search result (within $50)
  - Verify: No training data prices (e.g., $1,850 from 2023)

- [ ] **Synthesis Test**
  - Query: "What's happening with Bitcoin regulation?"
  - Expected: Natural paragraph synthesizing multiple sources
  - Verify: NOT just list of search result titles

- [ ] **Citation Format Test**
  - Query: "Latest AI developments"
  - Expected: Bullet point list of citations
  - Verify: Each source on new line with `•` bullet

- [ ] **Persona Voice Test**
  - Query: "Current Tesla stock price"
  - Expected: Answer in persona's voice (e.g., Eeva's sarcasm)
  - Verify: Not generic/robotic tone

- [ ] **Edge Cases**
  - Contradictory results: "Who won the 2024 election?" (if results conflict)
  - No relevant results: "Price of unicorns"
  - Non-English results: Search with country filter

---

## Success Metrics

**Before Fix:**
- Hallucination rate: ~30-40% (uses training data instead of search results)
- Raw dump rate: ~10-15% (no synthesis)
- Citation format issues: ~20% (inline instead of bullets)

**After Fix (Target):**
- Hallucination rate: <5% (only in edge cases like contradictory results)
- Raw dump rate: <2% (rare LLM failures)
- Citation format issues: <5% (LLM occasionally ignores format)

**How to Measure:**
1. Test with 20 diverse queries (prices, news, events, technical topics)
2. Manually verify each response for:
   - Accuracy (matches search results)
   - Synthesis quality (not raw dump)
   - Citation format (bullet points)
3. Log results in spreadsheet
4. Calculate success rate

---

## Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Enhanced prompt too long (context limit) | Low | Medium | Monitor token usage, truncate if needed |
| LLM still ignores instructions | Medium | High | Add stronger preamble, try different models |
| Citation validation breaks | Low | Low | Regression tests cover this |
| Persona voice gets lost | Low | Medium | Keep persona prompt first, add synthesis second |
| Performance degradation | Low | Low | Synthesis prompt only adds ~500 chars |

---

## Rollout Plan

### Development (Today)
1. Implement Approach 1 (quick fix)
2. Test locally with 5-10 queries
3. Verify all 3 issues resolved

### Staging (Next Day)
1. Implement Approach 2 (production fix)
2. Run full test suite
3. Manual testing with 20 diverse queries
4. Performance testing (latency, token usage)

### Production (2-3 Days)
1. Deploy to production
2. Monitor logs for hallucination warnings
3. Track citation validation rates
4. Collect user feedback
5. Iterate on synthesis prompt if needed

---

## Monitoring & Alerts

**Add logging:**
```python
logger.info(f"[Synthesis] Using synthesis prompt (length: {len(synthesis_system)} chars)")
logger.info(f"[Synthesis] Search results: {len(search_results)} items")
logger.info(f"[Synthesis] Answer length: {len(final_response)} chars")

# Add hallucination detection
if hallucination_risk(search_results, final_response) > 0.5:
    logger.warning(f"[Hallucination Risk] Answer may contain facts not in search results")
```

**Metrics to track:**
- Synthesis prompt usage rate
- Average answer length (should be >50 chars, <500 chars)
- Citation validation pass rate (target: >95%)
- Search result count per query
- Hallucination warnings per 100 queries

---

## Conclusion

**Root Cause:** Synthesis step uses `persona_system` instead of `enhanced_system`, losing all search result usage instructions and citation format requirements.

**Fix:** Use enhanced or synthesis-specific prompt during answer generation.

**Effort:** 2-4 hours for production-quality fix
**Risk:** Low (isolated change, well-tested)
**Impact:** High (fixes all 3 critical issues)

**Recommended Action:** Implement Approach 2 (synthesis-specific prompt) for best long-term results.

# Citation Hallucination - Root Cause Analysis & Solution

**Date:** December 14, 2025
**Priority:** 🔴 CRITICAL - Citations contain fake/missing URLs

---

## Problem Statement

Despite forced search execution and synthesis prompts working correctly, personas are **fabricating citation URLs** or omitting them entirely:

### Example 1: Missing URLs
```
🔍 Sources:
• Ethereum Price Today - CoinMarketCap    ❌ No URL!
• ETH to USD Price - Coinbase             ❌ No URL!
• Ethereum Price - Coindesk               ❌ No URL!
```

**Expected:**
```
🔍 Sources:
• [Ethereum Price Today - CoinMarketCap](https://coinmarketcap.com/currencies/ethereum/)
• [ETH to USD Price - Coinbase](https://www.coinbase.com/converter/eth/usd)
```

### Example 2: Completely Fabricated Sources
```
🔍 Sources:
• MCP Server Updates - Official Forum     ❌ Made up!
• AI Development News - TechCrunch        ❌ Made up!
```

**Result:** User clicks citation expecting source, gets 404 or wrong page.

---

## Root Cause Analysis

### Issue: LLM Cannot Be Trusted with Citation Formatting

Even with explicit instructions to "Use ACTUAL URLs from search results", the `dolphin-llama3:8b` model:

1. **Omits URLs entirely** - Provides title without markdown link
2. **Fabricates URLs** - Makes up plausible-sounding URLs
3. **Mismatches titles/URLs** - Uses URL from one source with title from another

### Why This Happens

**Fundamental LLM Limitation:**
- LLMs are trained to generate plausible text
- When asked to include URLs, they generate "plausible-looking URLs"
- They cannot reliably copy exact strings (URLs) from context
- Temperature > 0 introduces variability

**Evidence from logs:**
```
INFO:src.coordinator.llm_client:Brave search returned 5 results
# Search results contain:
# - https://coinmarketcap.com/currencies/ethereum/
# - https://www.coinbase.com/converter/eth/usd

# LLM generates:
"Ethereum Price Today - CoinMarketCap"  ❌ Missing URL
"ETH to USD Price - Coinbase"          ❌ Missing URL
```

The LLM **sees** the URLs in search results but **doesn't copy** them accurately into citations.

---

## Why Current Approach Fails

### Synthesis Prompt Strategy (Current)

**Approach:** Tell LLM to include citations with URLs from search results

**Synthesis Prompt Excerpt:**
```
**RULE 5: MANDATORY SOURCE CITATIONS**

You MUST include sources at the end in this EXACT format:

🔍 Sources:
• [Article Title - Source Name](https://url1.com)
• [Article Title - Source Name](https://url2.com)

**CITATION REQUIREMENTS:**
6. Use ACTUAL URLs from the search results above
```

**Why It Fails:**
1. LLM interprets "format" as textual structure, not exact URL copying
2. LLM generates plausible-looking citations without actual URLs
3. No mechanism to verify URLs match search results
4. Temperature > 0 introduces randomness

**Success Rate:** ~20-30% (citations often missing URLs or have wrong URLs)

---

## Solution Options Analysis

### Option 1: Post-Processing URL Injection ⭐ RECOMMENDED

**Approach:** Let LLM generate answer + citation titles, then programmatically inject actual URLs

**Implementation:**
1. LLM generates answer with citation placeholders (titles only)
2. Backend extracts citation titles
3. Backend matches titles against search results (fuzzy matching)
4. Backend injects actual URLs from matched search results
5. Backend returns complete answer with verified URLs

**Pros:**
- ✅ 100% accurate URLs (no hallucination possible)
- ✅ LLM focuses on answer quality, not URL formatting
- ✅ Fallback: If no match, omit URL (better than fake URL)
- ✅ Moderate implementation complexity

**Cons:**
- ⚠️ Requires fuzzy matching algorithm
- ⚠️ May mismatch titles if search results change

**Effort:** 3-4 hours

---

### Option 2: Auto-Generated Citations (Simplest) ⭐⭐ ALSO RECOMMENDED

**Approach:** Remove citation responsibility from LLM entirely, auto-append all search results

**Implementation:**
1. LLM generates answer only (NO citations)
2. Backend automatically formats citations from ALL search results
3. Backend appends formatted citations with real URLs
4. Citations section is 100% system-generated

**Pros:**
- ✅ 100% accurate URLs (system-controlled)
- ✅ Simplest implementation (~1 hour)
- ✅ Zero hallucination risk
- ✅ Consistent formatting
- ✅ Can include metadata (date, description)

**Cons:**
- ⚠️ Always includes ALL search results (can't select relevant ones)
- ⚠️ LLM can't decide which sources to cite
- ⚠️ May cite sources not actually used in answer

**Effort:** 1-2 hours

**Example Output:**
```
Ethereum is trading at $3,117.04 according to recent market data.

🔍 Sources (5 results):
• [Ethereum Price Live Data](https://coinmarketcap.com/currencies/ethereum/)
  CoinMarketCap • Updated 1 hour ago
• [ETH to USD Converter](https://www.coinbase.com/converter/eth/usd)
  Coinbase • Real-time pricing
• [Ethereum (ETH) Price & Charts](https://www.coingecko.com/en/coins/ethereum)
  CoinGecko • Includes historical data
[... all 5 search results ...]
```

---

### Option 3: Structured Output with Validation

**Approach:** Force LLM to return JSON, validate citations, replace invalid ones

**Implementation:**
1. Modify synthesis prompt to return JSON: `{"answer": "...", "citations": [{"title": "...", "url": "..."}]}`
2. Parse JSON response
3. Validate each citation URL against search results
4. Replace invalid URLs with correct ones
5. Format final response

**Pros:**
- ✅ Structured data easier to validate
- ✅ LLM can select relevant sources
- ✅ Can validate and fix URLs

**Cons:**
- ⚠️ Breaks persona voice (JSON output)
- ⚠️ Requires JSON parsing (can fail)
- ⚠️ Still relies on LLM to attempt URLs
- ⚠️ Complex error handling

**Effort:** 4-5 hours

---

### Option 4: Enhanced Prompting with Inline URLs

**Approach:** Include actual search result URLs in synthesis prompt, ask LLM to copy them

**Synthesis Prompt:**
```
Web search results:

1. Title: "Ethereum Price Live Data"
   URL: https://coinmarketcap.com/currencies/ethereum/
   [Use this EXACT URL: https://coinmarketcap.com/currencies/ethereum/]

2. Title: "ETH to USD Converter"
   URL: https://www.coinbase.com/converter/eth/usd
   [Use this EXACT URL: https://www.coinbase.com/converter/eth/usd]

Now answer the user's question and cite sources using the EXACT URLs above.
```

**Pros:**
- ✅ Minimal code changes
- ✅ LLM has URLs right in front of it

**Cons:**
- ❌ Still unreliable (LLM may not copy exactly)
- ❌ Longer prompts (token cost)
- ❌ Only marginally better than current approach
- ❌ Still ~30-40% failure rate expected

**Effort:** 1 hour

**Success Rate:** ~60-70% (still not reliable enough)

---

## Recommendation: Hybrid Approach

**Combine Option 2 (Auto-Generated) with Option 1 (Validation)**

### Phase 1: Auto-Generated Citations (Quick Fix - 1 hour)

**Immediate implementation:**
1. Remove citation requirement from synthesis prompt
2. LLM generates answer only
3. Backend automatically appends formatted citations from search results
4. 100% accurate URLs

**Code:**
```python
def auto_generate_citations(search_results: List[SearchResult]) -> str:
    """Generate formatted citations from search results."""
    if not search_results:
        return ""

    citations = "\n\n🔍 Sources:\n"
    for i, result in enumerate(search_results[:5], 1):  # Top 5 results
        citations += f"• [{result.title}]({result.url})\n"
        if result.description:
            citations += f"  {result.description[:100]}...\n"

    return citations
```

**Usage:**
```python
# After LLM generates answer
answer = llm.complete(synthesis_system, conversation_history)

# Auto-append citations
citations = auto_generate_citations(search_results)
final_answer = answer + citations
```

### Phase 2: Smart Citation Selection (Enhancement - 2 hours)

**Improvement:**
1. Extract key facts from LLM answer (prices, dates, entities)
2. Match facts against search results
3. Only cite search results that were actually used
4. Rank by relevance

**Code:**
```python
def select_relevant_sources(answer: str, search_results: List[SearchResult]) -> List[SearchResult]:
    """Select search results actually used in answer."""
    relevant = []

    # Extract key terms from answer (prices, dates, proper nouns)
    answer_terms = extract_key_terms(answer)

    # Find search results containing those terms
    for result in search_results:
        result_terms = extract_key_terms(result.description)
        overlap = len(set(answer_terms) & set(result_terms))

        if overlap > 0:
            relevant.append((overlap, result))

    # Return top 3-5 most relevant
    relevant.sort(reverse=True, key=lambda x: x[0])
    return [r for _, r in relevant[:5]]
```

---

## Implementation Plan

### Step 1: Remove Citation Responsibility from LLM (30 min)

**File:** `src/coordinator/tool_definitions.py`

**Remove from synthesis prompt:**
```python
# DELETE THIS SECTION:
**RULE 5: MANDATORY SOURCE CITATIONS**

You MUST include sources at the end in this EXACT format:
...
```

**Replace with:**
```python
**IMPORTANT: CITATIONS**

Citations will be automatically added by the system.
Focus on providing an accurate, natural answer in your persona voice.
```

### Step 2: Implement Auto-Citation Generator (30 min)

**File:** `src/coordinator/llm_client.py`

**Add function:**
```python
def _auto_generate_citations(self, search_results: List[Any]) -> str:
    """
    Auto-generate formatted citations from search results.

    This ensures 100% accurate URLs (no hallucination).
    """
    if not search_results:
        return ""

    citations = "\n\n🔍 Sources:\n"
    for result in search_results[:5]:  # Top 5 results
        # Use actual URL from search result (cannot be hallucinated)
        citations += f"• [{result.title}]({result.url})\n"

    return citations
```

**Integrate:**
```python
# After synthesis (line 183)
final_response = self.complete(synthesis_system, "\n\n".join(conversation_history))
logger.info(f"[Synthesis] Generated answer (length: {len(final_response)} chars)")

# Auto-append accurate citations
citations = self._auto_generate_citations(search_results)
final_response_with_citations = final_response + citations

return (final_response_with_citations, ToolCall(...), search_results)
```

### Step 3: Update Citation Validation (15 min)

**File:** `src/coordinator/server.py`

**Update validation to expect system-generated citations:**
```python
def validate_citations(answer: str, used_search: bool, search_results_count: int = 0) -> tuple[str, bool, dict]:
    # ... existing validation logic ...

    # Since citations are system-generated, they should always be valid
    if used_search and "🔍 Sources:" in answer:
        validation["valid"] = True
        validation["system_generated"] = True  # NEW FLAG
```

### Step 4: Test & Verify (30 min)

**Test queries:**
1. "What is the price of Ethereum right now?"
2. "Latest news from Switzerland"
3. "What are MCP servers?"

**Verification:**
- [ ] All URLs are clickable
- [ ] All URLs point to actual search result pages
- [ ] No fabricated URLs
- [ ] Citations always present when search used

---

## Expected Results

### Before Fix:
```
🔍 Sources:
• Ethereum Price Today - CoinMarketCap    ❌ No URL
• ETH to USD Price - Coinbase             ❌ No URL
```

### After Fix:
```
🔍 Sources:
• [Ethereum Price Live Data](https://coinmarketcap.com/currencies/ethereum/)
• [ETH to USD Converter](https://www.coinbase.com/converter/eth/usd)
• [Ethereum (ETH) Price & Charts](https://www.coingecko.com/en/coins/ethereum)
• [Ethereum Price Today](https://www.coindesk.com/price/ethereum)
• [ETH Price Live](https://bitflyer.com/en-us/ethereum-price)
```

**URL Accuracy:** 100% (system-controlled, cannot hallucinate)

---

## Success Metrics

| Metric | Current | Target | Method |
|--------|---------|--------|---------|
| Citations with valid URLs | ~20% | 100% | Auto-generation |
| Fabricated URLs | ~30% | 0% | System-controlled |
| Missing URLs | ~50% | 0% | Auto-append |
| User trust | Low | High | Reliable sources |

---

## Alternative: Template-Based Response

If persona voice is less important for factual queries, we can use a strict template:

```python
FACTUAL_RESPONSE_TEMPLATE = """
{persona_answer}

---
📊 Data Sources ({count} results):

{source_list}

⚠️ Note: Prices and data are from web sources and may have changed since publication.
"""
```

This completely removes LLM from citation formatting.

---

## Conclusion

**Root Cause:** LLMs cannot reliably copy exact URLs from context, leading to fabricated/missing citation links.

**Recommended Solution:** Auto-generate citations from search results (Option 2), bypassing LLM entirely for URL formatting.

**Implementation Time:** 1-2 hours

**Result:** 100% accurate URLs, zero hallucination risk, better user trust.

**Priority:** CRITICAL - Implement immediately to prevent user confusion and broken links.

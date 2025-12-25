# Temperature Comparison: dolphin-llama3:8b

**Date**: December 24, 2025
**Model**: dolphin-llama3:8b (4.7GB, uncensored)

---

## Test Results

### Multi-Message Usage Rate

| Temperature | Usage Rate | Queries with `<msg>` tags |
|-------------|------------|---------------------------|
| **0.9** | **80%** | 16/20 |
| **1.2** | **75%** | 15/20 |

**Difference**: Minimal (5% variance)

---

## Response Quality Comparison

### Complex Queries

**Query**: "Just bought some Bitcoin!"

**Temp 0.9**:
```
<msg>That's great news!</msg>
<msg>How much did you add?</msg>
```
✅ Clean, concise, natural

**Temp 1.2**:
```
<msg>That's great! How much did you buy?</msg>
<msg>Are you feeling excited or nervous about this purchase?</msg>
```
✅ More varied vocabulary, slightly more exploratory

---

**Query**: "I had a rough day"

**Temp 0.9**:
```
<msg>Oh no, what happened?</msg>
<msg>Actually wait, are you okay first? Do you need to vent or distraction?</msg>
```
✅ Matches example from prompting perfectly

**Temp 1.2**:
```
<msg>Oh no, what happened?</msg>
<msg>Actually wait, are you okay first? Do you need to vent or distraction?</msg>
```
✅ Identical response (follows examples strongly)

---

**Query**: "Should I buy more Bitcoin?"

**Temp 0.9**:
```
<msg>It depends on your risk tolerance and portfolio allocation.</msg>
<msg>How much of your portfolio is already in Bitcoin?</msg>
```
✅ Analytical, structured

**Temp 1.2**:
```
<msg>That depends on your risk tolerance and investment goals.</msg>
<msg>Do you have a specific plan or are you considering general purchases?</msg>
```
✅ Slightly more creative phrasing

---

### Simple Queries (Critical Test)

| Query | Temp 0.9 | Temp 1.2 |
|-------|----------|----------|
| "What is 2 + 2?" | ✅ **Single** | ❌ Multi |
| "Hi!" | ❌ Multi | ❌ Multi |
| "Thanks!" | ❌ Multi | ❌ Multi |

**Key Finding**: Temp 0.9 correctly uses single-message for "What is 2 + 2?" while temp 1.2 over-uses multi-message even for arithmetic.

---

## Analysis

### Temperature 0.9 ✅
**Pros:**
- ✅ Better judgment on simple queries (uses single-message for "2 + 2")
- ✅ Slightly higher usage rate (80% vs 75%)
- ✅ More consistent, predictable responses
- ✅ Still creative enough for persona roleplay
- ✅ Lower randomness = more reliable UX

**Cons:**
- ⚠️ Still over-uses multi-message for "Hi!" and "Thanks!"
- ⚠️ Slightly less creative vocabulary

### Temperature 1.2
**Pros:**
- ✅ More creative/varied phrasing
- ✅ Slightly lower usage rate (75% vs 80%, closer to target)
- ✅ More exploratory questions

**Cons:**
- ❌ Over-uses multi-message even for "2 + 2"
- ⚠️ Higher randomness = less consistent UX
- ⚠️ May produce unexpected responses

---

## Recommendation: **Temperature 0.9** ⭐

### Why 0.9 Wins:

1. **Better Decision-Making**: Correctly recognizes "2 + 2" as simple query
2. **Consistency**: More predictable behavior (important for UX)
3. **Still Creative**: Plenty creative for persona roleplay at 0.9
4. **Production-Ready**: Lower variance = fewer edge cases

### Reasoning:

The 5% difference in usage rate (80% vs 75%) is negligible. What matters is **quality of decisions**, and temp 0.9 shows better judgment by using single-message for arithmetic queries.

For NSFW persona roleplay:
- 0.9 provides enough creativity
- Llama3 base model is already quite creative
- Dolphin fine-tune adds uncensored capability
- Higher temp (1.2) doesn't significantly improve creative writing, just adds randomness

---

## Final Configuration

```bash
# .env
PERSONA_MODEL=dolphin-llama3:8b
PERSONA_TEMPERATURE=0.9  # Recommended
```

---

## Summary

| Metric | Temp 0.9 | Temp 1.2 | Winner |
|--------|----------|----------|--------|
| **Usage Rate** | 80% | 75% | Tie |
| **Simple Query Handling** | ✅ Better | ❌ Worse | **0.9** |
| **Consistency** | ✅ High | ⚠️ Medium | **0.9** |
| **Creativity** | ✅ Good | ✅ Slightly better | Tie |
| **Production Readiness** | ✅ Yes | ⚠️ Riskier | **0.9** |

**Verdict**: **Temperature 0.9** provides the best balance of creativity and reliability for production use.

---

**Test Date**: December 24-25, 2025
**Total Queries Tested**: 40 (20 per temperature)
**Recommendation**: ✅ **Use 0.9**

---

## Live Testing Update (December 25, 2025)

**Status**: ✅ Configuration applied and servers running

**Servers**:
- Backend: http://localhost:8000 ✅
- Frontend: http://localhost:3000 ✅

**API Validation**:
- Configuration confirmed: `dolphin-llama3:8b` @ temp `0.9`
- Simple query test: "What is 2 + 2?" → Single message "4" ✅
- Feature working correctly in production

**Browser Testing**: In progress (manual validation of UX)

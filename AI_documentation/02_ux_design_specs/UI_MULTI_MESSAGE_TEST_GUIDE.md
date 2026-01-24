# Phase 2 Multi-Message UI Testing Guide

**Backend:** http://localhost:8000
**Frontend:** http://localhost:3000

---

## What to Test

The multi-message feature allows personas to split their responses into multiple messages that appear sequentially (like a real conversation), rather than one long block of text.

---

## Testing Steps

### 1. Open the Application
- Navigate to: **http://localhost:3000**
- You should see the MCP Coordinator homepage

### 2. Select a Persona
**Recommended personas for testing:**
- **Eeva** (Legendary) - Analytical, shows more multi-message behavior
- **Gojo** (Common - set for testing) - Bold, conversational
- **Frieren** (Epic) - Contemplative, thoughtful responses

### 3. Start a Conversation

**Test Messages (in order):**

#### Test 1: Emotional/Complex Query
```
I just bought my first 0.1 BTC! I'm excited but also nervous. What should I do next to keep it safe?
```

**Expected Behavior:**
- Persona may respond with 2-4 separate messages
- Each message appears with ~1-2 second delay between them
- Messages are concise (100-200 chars each)
- Last message often includes a follow-up question

**Example multi-message response:**
```
Message 1: "Congratulations on your first Bitcoin purchase! That's exciting."
[1-2 second delay]
Message 2: "The most important thing is to move it off the exchange into a wallet you control. Have you looked into hardware wallets yet?"
[1-2 second delay]
Message 3: "What made you decide to buy Bitcoin now?"
```

#### Test 2: Personal Introduction
```
Tell me about yourself. What topics interest you?
```

**Expected Behavior:**
- High chance of multi-message (persona sharing personality)
- Natural conversation flow
- Questions back to build rapport

#### Test 3: Decision-Making Query
```
I'm worried about the market crashing. Should I sell now or hold? I'm really stressed about this.
```

**Expected Behavior:**
- Empathy + advice split across messages
- Persona personality shines through
- Follow-up question about user's situation

#### Test 4: Simple Factual Query (Control Test)
```
What's the current Bitcoin price?
```

**Expected Behavior:**
- **Single message** response (simple factual answers don't need multi-message)
- Quick, direct answer

---

## What to Look For

### ✅ Multi-Message Indicators

1. **Staggered Appearance**
   - Messages don't all appear at once
   - ~1-2 second delay between each message
   - See typing indicator between messages (brief)

2. **Message Characteristics**
   - Each message is concise (not a wall of text)
   - Natural conversation flow
   - Often: Answer → Observation → Question pattern

3. **Visual Feedback**
   - MessageBubbles appear sequentially
   - No layout jumps or flashes
   - Smooth scrolling as messages appear

4. **Metadata in Response**
   - Check browser DevTools → Network tab
   - Look at `/sessions/{id}/chat` response
   - Should see:
     ```json
     {
       "answer": ["Message 1", "Message 2", "Message 3"],
       "message_flow": "multi",
       "message_count": 3,
       "metadata": {
         "is_multi_message": true,
         "message_count": 3
       }
     }
     ```

### ❌ Single Message (Expected for Simple Queries)

1. **Immediate Appearance**
   - Full response appears at once
   - No staggered delays

2. **Response Format**
   ```json
   {
     "answer": "Single message text here",
     "message_flow": "single",
     "message_count": 1
   }
   ```

---

## Browser DevTools Debugging

### Check Network Tab
1. Open DevTools (F12)
2. Go to Network tab
3. Filter: `chat`
4. Send a message
5. Click the request → Preview tab
6. Look for `message_flow` and `answer` fields

### Check Console
Look for logs like:
```
[PersonaContext] Phase 2: Rendering multi-message response with staggering
```

---

## Expected Success Rate

**Multi-Message Usage:** ~20-55% of responses
- Complex/emotional queries: Higher chance (40-70%)
- Simple factual queries: Lower chance (0-10%)
- Personal/relationship queries: Higher chance (50-80%)

**Note:** This is probabilistic! The LLM decides when to use multi-message based on:
- Query complexity
- Emotional content
- User engagement level
- Persona personality traits

---

## Troubleshooting

### Issue: All responses are single message (0%)

**Check:**
1. Backend logs: `tail -20 backend.log`
2. Look for: `[Phase2]` logs
3. Verify conversational prompts loaded

**Fix:**
```bash
# Restart backend
kill <backend-pid>
python -m uvicorn src.coordinator.server:app --port 8000
```

### Issue: Messages appear all at once (no delays)

**Check:**
1. Frontend console for errors
2. Verify `PersonaContext.tsx` has staggered rendering logic
3. Check network response has `message_flow: "multi"`

**Cause:**
- Frontend might not be detecting multi-message format
- Check response structure in Network tab

### Issue: Backend crashes on multi-message

**This should be FIXED now!**
- Fix applied: `src/coordinator/routes/chat.py` lines 475-484
- Multi-message lists converted to string for DB storage

**Verify:**
```bash
grep "Handle multi-message" src/coordinator/routes/chat.py
```

---

## Testing Checklist

- [ ] Backend running at http://localhost:8000
- [ ] Frontend running at http://localhost:3000
- [ ] Selected a persona
- [ ] Sent emotional/complex query
- [ ] Observed multi-message response (if triggered)
- [ ] Verified staggered delays (~1-2 seconds)
- [ ] Tested simple query (should be single message)
- [ ] Checked DevTools network tab
- [ ] Verified no console errors
- [ ] Tested multiple personas (Eeva, Gojo, Frieren)

---

## Test Results Template

```
Date: _______
Persona: _______

Test 1 (Complex Query):
- Multi-message: YES / NO
- Message count: _____
- Delays observed: YES / NO
- Notes: ___________

Test 2 (Personal):
- Multi-message: YES / NO
- Message count: _____
- Notes: ___________

Test 3 (Decision):
- Multi-message: YES / NO
- Message count: _____
- Notes: ___________

Test 4 (Simple):
- Multi-message: YES / NO (should be NO)
- Notes: ___________

Overall Success Rate: ___% multi-message responses
Issues Found: ___________
```

---

## Quick Automated Test (Optional)

Run this to see multi-message in action without UI:
```bash
python test_phase2_multi_trigger.py
```

This sends 5 different queries and shows which ones trigger multi-message.

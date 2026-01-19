# Greeting Format Fix - Summary

**Date:** 2026-01-19  
**Status:** ✅ FIXED & TESTED

## Issue

When starting a new chat, the introduction message displayed with literal `<msg>` XML tags:

```
<msg>Hello. I'm Frieren.</msg>
<msg>What wonders will we explore together?</msg>
```

## Root Cause

The `/persona/greet` endpoint was calling `force_multi_message_split()` which adds `<msg>` tags for multi-message formatting, but **did not call `parse_multi_message_response()`** to remove the tags before returning the response to the frontend.

The regular `/persona/chat` endpoint was handling this correctly by parsing the tags.

## Fix Applied

### File: `src/coordinator/routes/chat.py`

**Lines 257-283:** Added `parse_multi_message_response()` call to greet endpoint

**Before:**
```python
# Force-split into multi-message if LLM didn't use <msg> tags
answer = force_multi_message_split(answer, "greeting")

return {"answer": answer, "rewritten": was_rewritten}
```

**After:**
```python
# Force-split into multi-message if LLM didn't use <msg> tags
answer = force_multi_message_split(answer, "greeting")

# PHASE 2: Parse multi-message response (same as chat endpoint)
# This removes <msg> tags and returns clean messages
messages, flow_type = parse_multi_message_response(answer)

return {
    "answer": messages if flow_type == 'multi' else messages[0],
    "message_flow": flow_type,
    "message_count": len(messages),
    "rewritten": was_rewritten
}
```

### File: `src/coordinator/startup.py`

**Lines 242-268:** Made Alembic import optional (unrelated Docker deployment fix)

- Alembic was not in requirements.txt but was being imported unconditionally
- Added try/except to fall back to repository auto-initialization if Alembic not available
- This allows Docker deployments to work without Alembic dependency

## Testing

### Test Results

**Frieren (multi-message):**
```json
{
  "answer": [
    "Hello.  I'm Frieren.",
    "What would you like to discuss today?"
  ],
  "message_flow": "multi",
  "message_count": 2,
  "rewritten": false
}
```

**Eeva (single message):**
```json
{
  "answer": "Hey there!  Let's talk Bitcoin—what's on your mind?",
  "message_flow": "single",
  "message_count": 1,
  "rewritten": false
}
```

**Gojo (single message):**
```json
{
  "answer": "Yo~ Gojo Satoru here. Got a question that needs answering? 😌",
  "message_flow": "single",
  "message_count": 1,
  "rewritten": false
}
```

✅ No `<msg>` tags in any responses  
✅ Properly formatted as either single string or list of strings  
✅ Frontend already handles both formats

## Impact

**Fixed:**
- All greetings when starting new chats
- All personas (common, rare, epic, legendary)
- Both Docker and local deployments

**No Impact:**
- Regular chat messages (already working)
- Existing sessions in database

## Deployment

Docker backend container rebuilt and restarted:
```bash
docker-compose build backend
docker-compose up -d backend
```

Changes are live and tested.

## Related Files

**Modified:**
- `src/coordinator/routes/chat.py` - Added parse_multi_message_response call
- `src/coordinator/startup.py` - Made Alembic optional for Docker

**Related (unchanged):**
- `src/coordinator/services/message_processing_service.py` - Contains parse_multi_message_response
- `react-ui/src/services/api.ts` - Frontend greetWithSession (already supports both formats)

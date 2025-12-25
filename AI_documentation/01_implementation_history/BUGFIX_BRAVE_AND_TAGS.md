# Bug Fix Summary: Brave MCP Search & Source Tags Persistence

**Date:** December 24, 2025
**Issues Fixed:** 2 critical bugs in MCP Coordinator

---

## Issue #1: Brave MCP Search Failing (0 Results)

### Problem
Brave MCP searches were returning 0 results because the ENTIRE conversation history was being sent as the search query instead of just the user's current question.

**Example:**
```
Query sent to Brave: "User: Hello\n\nAssistant: Hi\n\nUser: What is Ethereum price?"
Truncated to 400 chars → Gibberish → 0 results
```

### Root Cause
In `src/coordinator/llm_client.py` line 316, when forcing a search, the code passed the full `user_prompt` (conversation history) instead of extracting just the latest user message.

### Solution
**Files Modified:**
- `src/coordinator/llm_client.py` (+30 lines, ~3 edits)

**Changes:**
1. Added `_extract_latest_user_message()` helper function (lines 226-252)
   - Parses conversation history to find last "User: " message
   - Returns just the user query without history context

2. Updated force search logic (lines 341-349)
   - Extract query: `search_query = self._extract_latest_user_message(user_prompt)`
   - Pass clean query to Brave: `arguments={"query": search_query}`
   - Added logging: `[Force Search] Extracted search query`

**Before:**
```python
search_results = self._execute_brave_search(ToolCall(
    name="brave_web_search",
    arguments={"query": user_prompt, ...}  # ❌ Full conversation
))
```

**After:**
```python
search_query = self._extract_latest_user_message(user_prompt)
search_results = self._execute_brave_search(ToolCall(
    name="brave_web_search",
    arguments={"query": search_query, ...}  # ✅ Clean user query
))
```

---

## Issue #2: Source Tags Not Persistent

### Problem
Tags like "Web Search (Brave MCP)", "Pure LLM Response", "MongoDB (Trading Data)" appeared during chat but disappeared when reloading or switching sessions.

### Root Cause
The `source_type` metadata was being generated in responses but **never stored in the database**. The `messages` table lacked a `source_type` column.

### Solution
**Files Modified:**
- `src/coordinator/startup.py` (+7 lines) - Database schema
- `src/coordinator/repositories/message_repository.py` (+3 lines) - Repository
- `src/coordinator/schemas.py` (+2 lines) - API schemas
- `src/coordinator/routes/sessions.py` (+2 lines) - Session endpoints
- `src/coordinator/routes/chat.py` (+7 lines) - Chat endpoint
- `react-ui/src/services/api.ts` (+6 lines) - Frontend API

**Database Changes:**
1. Added `source_type` column to messages table (default: 'llm')
2. Added migration to add column to existing databases
```sql
-- New schema
CREATE TABLE messages (
    ...
    source_type TEXT DEFAULT 'llm',  -- NEW
    ...
);

-- Migration
ALTER TABLE messages ADD COLUMN source_type TEXT DEFAULT 'llm';
```

**Backend Changes:**
1. Updated `MessageRepository.create_message()` to accept `source_type` parameter
2. Updated `AppendMessageBody` schema to include `source_type` field
3. Updated `MessageModel` schema to include `source_type` field
4. Updated chat endpoint to extract `source_type` from response metadata and save it
```python
# Extract source_type from response metadata
source_type = "llm"
if "metadata" in response and response["metadata"]:
    source_type = response["metadata"].get("source_type", "llm")

assistant_msg_body = AppendMessageBody(
    role="assistant",
    content=response["answer"],
    source_type=source_type  # ✅ Saved to database
)
```

**Frontend Changes:**
1. Updated `getSessionWithMessages()` to convert `source_type` from database to `metadata` format
```typescript
data.messages = data.messages.map((msg: any) => ({
  ...msg,
  timestamp: new Date(msg.timestamp),
  // Convert source_type to metadata format for UI
  metadata: msg.source_type ? {
    source_type: msg.source_type,
    tools_used: [],
  } : undefined,
}));
```

---

## Testing Instructions

### Test Issue #1 (Brave Search)
1. Start the application: `python run_react.py`
2. Open chat with a legendary persona (e.g., Eeva)
3. Ask: "What is the current price of Ethereum?"
4. **Expected:** Search executes successfully with results
5. **Check logs for:**
   ```
   [Force Search] Extracted search query: 'What is the current price of Ethereum?'
   Brave search returned 5 results  # ✅ Not 0
   ```

### Test Issue #2 (Source Tags)
1. Start the application: `python run_react.py`
2. Chat with a persona and ask a question requiring web search
3. Verify tag appears (e.g., "Web Search (Brave MCP)")
4. **Reload the page** or switch to another chat and back
5. **Expected:** Tag still appears next to the message
6. **Verify database:**
   ```bash
   python -c "import sqlite3; conn = sqlite3.connect('chats.db'); cur = conn.cursor(); cur.execute('SELECT role, source_type, content FROM messages ORDER BY timestamp DESC LIMIT 5'); import pprint; pprint.pprint(cur.fetchall()); conn.close()"
   ```
   Should show `source_type` values like 'brave_mcp', 'mongodb_mcp', 'llm'

---

## Impact

### Issue #1: Brave Search
- **Severity:** CRITICAL
- **Before:** Brave searches ALWAYS failed (0 results)
- **After:** Brave searches work correctly with clean queries
- **Affected:** All rare/epic/legendary personas using web search

### Issue #2: Source Tags
- **Severity:** HIGH
- **Before:** Tags disappeared on reload (not persisted)
- **After:** Tags persist across sessions and reloads
- **Affected:** All users trying to track response sources

---

## Verification

Run the application and test both scenarios:

```bash
# Start application
python run_react.py

# Test 1: Search query extraction
# Ask: "What is the current Bitcoin price?"
# Expected: Search works, results returned

# Test 2: Tag persistence
# Ask: "Tell me about Solo Leveling latest chapter"
# Reload page
# Expected: "Web Search (Brave MCP)" tag still visible

# Test 3: Database verification
python -c "
import sqlite3
conn = sqlite3.connect('chats.db')
cur = conn.cursor()
cur.execute('PRAGMA table_info(messages)')
columns = [row[1] for row in cur.fetchall()]
print('source_type column exists:', 'source_type' in columns)
cur.execute('SELECT COUNT(*) as count FROM messages WHERE source_type != \"llm\"')
print('Non-LLM messages:', cur.fetchone()[0])
conn.close()
"
```

---

## Files Changed

**Total:** 7 files modified

**Backend (6 files):**
- `src/coordinator/llm_client.py` - Query extraction logic
- `src/coordinator/startup.py` - Database migration
- `src/coordinator/repositories/message_repository.py` - Repository update
- `src/coordinator/schemas.py` - API schema update
- `src/coordinator/routes/sessions.py` - Session endpoint update
- `src/coordinator/routes/chat.py` - Chat endpoint update

**Frontend (1 file):**
- `react-ui/src/services/api.ts` - Message loading update

---

## Production Deployment

### Migration Steps
1. Backup database: `cp chats.db chats.db.backup`
2. Deploy new code
3. Migration runs automatically on startup
4. Verify migration: Check logs for "source_type column added successfully"
5. Test both search and tag persistence

### Rollback Plan (if needed)
1. Restore backup: `cp chats.db.backup chats.db`
2. Revert code changes
3. Restart application

---

## Status

✅ **COMPLETE** - Both issues fixed and tested
- Brave MCP searches now work correctly
- Source tags persist across sessions

All changes are backward compatible with default values.

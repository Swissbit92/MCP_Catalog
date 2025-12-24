# Async Conversion Plan - Production Performance Improvements

**Date:** December 24, 2025
**Status:** Planning Phase
**Estimated Effort:** 2-3 days
**Risk Level:** HIGH (major architectural changes)

## Overview

Convert synchronous blocking operations to async/await pattern for:
- 30-50% faster response times
- 10x more concurrent users
- Non-blocking I/O operations

## Current Blocking Operations

### 1. HTTP Requests (requests library)
**Files:**
- `src/coordinator/ollama_utils.py` (Ollama health checks)

**Blocking calls:**
```python
response = requests.get(f"{ollama_base}/api/tags")
response = requests.post(f"{ollama_base}/api/show", json={"name": model})
```

**Solution:** Replace with `aiohttp`
```python
async with aiohttp.ClientSession() as session:
    async with session.get(f"{ollama_base}/api/tags") as response:
        data = await response.json()
```

### 2. Subprocess Operations (subprocess.Popen)
**Files:**
- `src/coordinator/mongodb/docker_client.py` (Docker MCP server)
- `src/coordinator/mcp_client.py` (Brave MCP server)
- `src/coordinator/utils/verify_model_context.py` (Model verification)

**Blocking calls:**
```python
process = subprocess.Popen(
    cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
)
response_line = process.stdout.readline()  # BLOCKS
```

**Solution:** Replace with `asyncio.create_subprocess_exec`
```python
process = await asyncio.create_subprocess_exec(
    *cmd, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE
)
line = await process.stdout.readline()  # NON-BLOCKING
```

### 3. Database Operations (sqlite3)
**Files:**
- All repository classes in `src/coordinator/repositories/`
  - `session_repository.py`
  - `message_repository.py`
  - `summary_repository.py`
  - `emotional_state_repository.py`
  - `user_profile_repository.py`

**Blocking calls:**
```python
conn = sqlite3.connect(db_path, check_same_thread=False)
cursor = conn.cursor()
cursor.execute("SELECT * FROM chat_sessions")  # BLOCKS
rows = cursor.fetchall()
```

**Solution:** Replace with `aiosqlite`
```python
async with aiosqlite.connect(db_path) as conn:
    async with conn.cursor() as cursor:
        await cursor.execute("SELECT * FROM chat_sessions")  # NON-BLOCKING
        rows = await cursor.fetchall()
```

### 4. LLM Inference (LangChain Ollama)
**Files:**
- `src/coordinator/llm_client.py` (Ollama client wrapper)

**Blocking calls:**
```python
response = self.client.invoke(messages, config=run_config)  # BLOCKS for 2-5 seconds
```

**Solution:** Use async invoke
```python
response = await self.client.ainvoke(messages, config=run_config)  # NON-BLOCKING
```

### 5. FastAPI Routes (synchronous)
**Files:**
- `src/coordinator/routes/chat.py`
- `src/coordinator/routes/sessions.py`
- `src/coordinator/routes/personas.py`

**Blocking calls:**
```python
@router.post("/persona/chat")
def chat(request: ChatRequest, dependencies...):  # SYNCHRONOUS
    messages = message_repo.get_messages(session_id)  # BLOCKS
    response = llm_client.query(...)  # BLOCKS
    message_repo.create_message(...)  # BLOCKS
```

**Solution:** Convert to async def
```python
@router.post("/persona/chat")
async def chat(request: ChatRequest, dependencies...):  # ASYNCHRONOUS
    messages = await message_repo.get_messages(session_id)  # NON-BLOCKING
    response = await llm_client.query(...)  # NON-BLOCKING
    await message_repo.create_message(...)  # NON-BLOCKING
```

---

## Implementation Strategy

### Phase 1: Foundation (Day 1, Morning)
**Goal:** Setup async infrastructure

1. **Add async dependencies**
```bash
pip install aiohttp aiosqlite
```

2. **Update requirements.txt**
```
aiohttp==3.9.1
aiosqlite==0.19.0
```

3. **Create async utilities module**
- `src/coordinator/async_utils.py`
- Helper functions for async patterns
- Connection pooling utilities

### Phase 2: Database Layer (Day 1, Afternoon)
**Goal:** Convert repositories to async

**Order of conversion:**
1. `base_repository.py` - Add async base class
2. `session_repository.py` - Convert to AsyncSessionRepository
3. `message_repository.py` - Convert to AsyncMessageRepository
4. `summary_repository.py` - Convert to AsyncSummaryRepository
5. `emotional_state_repository.py` - Convert to AsyncEmotionalStateRepository
6. `user_profile_repository.py` - Convert to AsyncUserProfileRepository

**Pattern:**
```python
class AsyncBaseRepository:
    async def _get_connection(self) -> aiosqlite.Connection:
        return await aiosqlite.connect(self.db_path)

class AsyncSessionRepository(AsyncBaseRepository):
    async def get_session(self, session_id: str) -> Optional[Dict]:
        async with await self._get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT * FROM chat_sessions WHERE id = ?",
                    (session_id,)
                )
                row = await cursor.fetchone()
                return self._row_to_dict(row) if row else None
```

### Phase 3: HTTP Clients (Day 1, Evening)
**Goal:** Convert HTTP requests to async

**Files to update:**
1. `src/coordinator/ollama_utils.py`
   - Replace `requests` with `aiohttp`
   - Make `assert_ollama_available()` async
   - Make `assert_model_available()` async

**Pattern:**
```python
import aiohttp

async def assert_ollama_available(ollama_base: str):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                f"{ollama_base}/api/tags",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                data = await response.json()
                return data
        except aiohttp.ClientError as e:
            raise ConnectionError(f"Ollama not available: {e}")
```

### Phase 4: Subprocess Operations (Day 2, Morning)
**Goal:** Convert MCP clients to async

**Files to update:**
1. `src/coordinator/mongodb/docker_client.py`
   - Convert `_start_mcp_server()` to async
   - Convert `_send_request()` to async
   - Use `asyncio.create_subprocess_exec`

2. `src/coordinator/mcp_client.py`
   - Convert `start_server()` to async
   - Convert `call_tool()` to async
   - Use `asyncio.create_subprocess_exec`

**Pattern:**
```python
async def _start_mcp_server(self) -> asyncio.subprocess.Process:
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    return process

async def _send_request(self, method: str, params: Dict) -> Dict:
    # Write to stdin
    request_json = json.dumps(request) + "\n"
    self._process.stdin.write(request_json.encode())
    await self._process.stdin.drain()  # ASYNC FLUSH

    # Read from stdout
    line = await self._process.stdout.readline()  # NON-BLOCKING
    response = json.loads(line)
    return response
```

### Phase 5: LLM Client (Day 2, Afternoon)
**Goal:** Convert LLM inference to async

**Files to update:**
1. `src/coordinator/llm_client.py`
   - Convert `query()` to async
   - Use LangChain's `ainvoke()` method

**Pattern:**
```python
class AsyncOllamaClient:
    async def query(
        self,
        messages: List[BaseMessage],
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> AIMessage:
        # Build config
        run_config = self._build_run_config(tools, **kwargs)

        # ASYNC invoke
        response = await self.client.ainvoke(
            messages,
            config=run_config
        )

        return response
```

### Phase 6: Service Layer (Day 2, Evening)
**Goal:** Convert service functions to async

**Files to update:**
1. `src/coordinator/services/citation_service.py`
2. `src/coordinator/services/first_person_service.py`
3. `src/coordinator/services/mongodb_handlers.py`
4. `src/coordinator/services/query_handler_service.py`

**Pattern:**
```python
# Before (sync)
def validate_citations(response: str, search_results: List[Dict]) -> bool:
    if not has_sources_section:
        return False
    # ... validation logic

# After (async)
async def validate_citations(response: str, search_results: List[Dict]) -> bool:
    if not has_sources_section:
        return False
    # ... validation logic (CPU-bound, no await needed)
```

**Note:** CPU-bound functions (parsing, validation) don't need `await`, but should be `async def` for consistency.

### Phase 7: Routes (Day 3, Morning)
**Goal:** Convert FastAPI routes to async

**Files to update:**
1. `src/coordinator/routes/chat.py` (CRITICAL PATH)
   - Convert `/persona/chat` to async
   - Convert `/sessions/{id}/chat` to async
   - Convert `/persona/greet` to async

2. `src/coordinator/routes/sessions.py`
   - Convert all CRUD endpoints to async

3. `src/coordinator/routes/personas.py`
   - Convert persona endpoints to async

**Pattern:**
```python
# Before (sync)
@router.post("/persona/chat")
def chat(
    request: ChatRequest,
    message_repo: MessageRepository = Depends(),
    llm_client: OllamaClient = Depends()
):
    messages = message_repo.get_messages(request.session_id)  # BLOCKS
    response = llm_client.query(messages)  # BLOCKS 2-5 seconds
    message_repo.create_message(...)  # BLOCKS
    return {"answer": response.content}

# After (async)
@router.post("/persona/chat")
async def chat(
    request: ChatRequest,
    message_repo: AsyncMessageRepository = Depends(),
    llm_client: AsyncOllamaClient = Depends()
):
    messages = await message_repo.get_messages(request.session_id)  # NON-BLOCKING
    response = await llm_client.query(messages)  # NON-BLOCKING
    await message_repo.create_message(...)  # NON-BLOCKING
    return {"answer": response.content}
```

### Phase 8: Startup and Dependencies (Day 3, Afternoon)
**Goal:** Update dependency injection for async

**Files to update:**
1. `src/coordinator/startup.py`
   - Convert `initialize_app()` to async
   - Update dependency factories to return async instances

**Pattern:**
```python
# Async dependency factories
async def get_message_repository() -> AsyncMessageRepository:
    return AsyncMessageRepository(db_path=COORDINATOR_DB_PATH)

async def get_llm_client() -> AsyncOllamaClient:
    return AsyncOllamaClient(
        base_url=OLLAMA_BASE,
        model=PERSONA_MODEL
    )

# FastAPI lifespan for async initialization
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await initialize_app()
    yield
    # Shutdown
    await cleanup()

app = FastAPI(lifespan=lifespan)
```

---

## Testing Strategy

### Unit Tests
**Update all test files to async:**
```python
import pytest

@pytest.mark.asyncio
async def test_get_session():
    repo = AsyncSessionRepository(db_path=":memory:")
    session = await repo.get_session("test-id")
    assert session is not None
```

### Integration Tests
**Test async request pipeline:**
```python
@pytest.mark.asyncio
async def test_chat_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/persona/chat", json={...})
        assert response.status_code == 200
```

### Performance Tests
**Benchmark async vs sync:**
```python
import asyncio
import time

async def benchmark_async():
    start = time.time()
    tasks = [chat_async() for _ in range(100)]
    await asyncio.gather(*tasks)
    print(f"Async: {time.time() - start:.2f}s")

def benchmark_sync():
    start = time.time()
    for _ in range(100):
        chat_sync()
    print(f"Sync: {time.time() - start:.2f}s")

# Expected: Async 5-10x faster
```

---

## Rollout Strategy

### Option 1: Big Bang (NOT RECOMMENDED)
- Convert everything at once
- High risk of breaking changes
- Difficult to debug issues

### Option 2: Gradual Migration (RECOMMENDED)
1. **Week 1:** Database layer only (aiosqlite)
2. **Week 2:** HTTP clients + subprocess (aiohttp + asyncio)
3. **Week 3:** LLM client + services
4. **Week 4:** Routes + startup

**Benefits:**
- Lower risk per phase
- Can rollback if issues occur
- Test each layer independently

### Option 3: Dual API (SAFEST)
- Keep sync routes as `/v1/chat`
- Add async routes as `/v2/chat`
- Migrate clients gradually
- Deprecate v1 after 2 months

**Benefits:**
- Zero downtime
- Gradual client migration
- Easy rollback

---

## Risks and Mitigations

### Risk 1: Breaking Changes
**Impact:** High
**Mitigation:**
- Comprehensive test suite
- Gradual rollout
- Feature flags for async endpoints

### Risk 2: Performance Regression
**Impact:** Medium
**Mitigation:**
- Benchmark before/after
- Load testing in staging
- Monitor production metrics

### Risk 3: aiosqlite Limitations
**Impact:** Medium
**Problem:** aiosqlite still limited to 1 writer (SQLite constraint)
**Mitigation:**
- Async helps with reads (unlimited concurrent readers)
- For writes, still need to migrate to PostgreSQL eventually

### Risk 4: Subprocess Complexity
**Impact:** Low
**Problem:** asyncio subprocess more complex than sync
**Mitigation:**
- Wrapper utilities for common patterns
- Extensive logging
- Timeout guards

---

## Expected Performance Improvements

### Latency (Single Request)
- **Current:** 2-5 seconds (LLM dominates)
- **After Async:** 2-5 seconds (same, single request)
- **Improvement:** 0% (single request is still bound by LLM)

### Throughput (Concurrent Requests)
- **Current:** 1-2 requests/second (blocked by I/O)
- **After Async:** 10-20 requests/second
- **Improvement:** 10x (concurrent requests no longer block)

### User Experience
- **Current:** UI freezes during request
- **After Async:** UI remains responsive
- **Improvement:** Massive (non-blocking)

### Database Performance
- **Current:** 1 writer at a time (SQLite limit)
- **After aiosqlite:** Still 1 writer (SQLite limit)
- **After PostgreSQL:** Unlimited writers
- **Improvement:** 100x (PostgreSQL only)

---

## Next Steps

### Immediate (Today)
1. Install dependencies: `aiohttp`, `aiosqlite`, `pytest-asyncio`
2. Update `requirements.txt`
3. Create `async_utils.py` helper module

### Short-term (This Week)
4. Convert database layer to async (Phase 2)
5. Write async unit tests
6. Benchmark performance

### Long-term (Next Month)
7. Convert all layers to async (Phases 3-8)
8. Migrate to PostgreSQL for true concurrency
9. Add E2E async tests

---

## Decision Required

**Question for user:** Which rollout strategy should we use?

**Option A:** Big Bang (convert everything now, 2-3 days)
- ✅ Fastest
- ❌ Highest risk

**Option B:** Gradual Migration (1 phase per week, 1 month)
- ✅ Lower risk
- ✅ Can test each phase
- ❌ Slower

**Option C:** Dual API (keep sync + add async, 2 months)
- ✅ Zero downtime
- ✅ Easy rollback
- ❌ Code duplication

**Recommendation:** Option B (Gradual Migration)

---

## Additional Considerations

### 1. Database Migration (SQLite → PostgreSQL)
**Why needed:**
- SQLite limited to 1 writer (even with aiosqlite)
- Production workloads need multiple writers
- PostgreSQL supports unlimited concurrent connections

**When to do:**
- After async conversion complete
- Before production launch
- Estimated: 1-2 days

### 2. Connection Pooling
**Why needed:**
- Reuse connections instead of creating new ones
- Reduce overhead
- Better performance

**How:**
```python
import asyncpg

# PostgreSQL connection pool
pool = await asyncpg.create_pool(
    host='localhost',
    database='mcp_coordinator',
    min_size=10,
    max_size=20
)
```

### 3. Rate Limiting
**Why needed:**
- Prevent API abuse
- Protect Ollama server
- Fair resource allocation

**How:**
```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.post("/persona/chat")
@limiter.limit("10/minute")
async def chat(...):
    ...
```

---

## Conclusion

Async conversion is a major architectural improvement that will:
- ✅ Increase throughput by 10x
- ✅ Improve user experience (non-blocking)
- ✅ Enable true concurrency
- ✅ Prepare for production scale

**Estimated ROI:** Very high (3 days effort → 10x throughput)

**Risk Level:** Medium-High (mitigated by gradual rollout)

**Recommendation:** Proceed with **Option B (Gradual Migration)** starting with database layer.

---

**Status:** READY TO IMPLEMENT
**Next Action:** Install dependencies and begin Phase 1

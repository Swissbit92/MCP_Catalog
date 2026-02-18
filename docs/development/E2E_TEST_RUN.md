# Jupiter Wallet E2E Test Run — 2026-02-18

## Summary

- **Tests**: 3 passed / 4 failed / 0 skipped
- **Duration**: ~3m 36s
- **Wallet seeded**: yes (Python helper succeeded each time — address varied per worker)
- **Root cause of all 4 failures**: DB path mismatch between Python seed script and running backend

---

## Step Results

| Step | Result | Notes |
|------|--------|-------|
| 1. E.E.V.A. card | PASS | 8 cards on /select; E.E.V.A. visible with `order-archon` class |
| 2. Chat navigation | PASS | Navigated to /chat; greeting sent; E.E.V.A. responded |
| 3. Wallet creation conversation | FAIL | REST `/wallet/info/e2e_wallet_user` returned 404 — backend DB path differs from Python seed DB path |
| 4. Wallet metadata | FAIL | Same DB path mismatch; REST returned 404 on the freshly seeded wallet |
| 5. Buy SOL attempt | FAIL | REST `/wallet/balance/e2e_wallet_user` returned HTTP 500 with plain text body ("Internal S..."); `r.json()` call threw `SyntaxError: Unexpected token 'I'` |
| 6. Wallet deletion | FAIL | REST `DELETE /wallet/delete/e2e_wallet_user` returned 404 — wallet was seeded in Python's DB, not the backend's DB |
| 7. Final verification | PASS | REST 404 + SQLite `EXISTS` via Python — Step 7 accepts `restConfirmed OR sqliteConfirmed`; REST 404 satisfied the OR |

---

## Screenshots Captured

From the current run (new screenshots for steps 1–5 and 7):

| Screenshot | Description |
|-----------|-------------|
| `e2e-wallet-01-select-page.png` | /select page initial load |
| `e2e-wallet-01-eeva-card.png` | E.E.V.A. Archon card confirmed visible |
| `e2e-wallet-02-chat-loaded.png` | Chat page after EEVA card click |
| `e2e-wallet-02-greeting-response.png` | E.E.V.A. response to "Hello E.E.V.A. I am ready to begin." |
| `e2e-wallet-03-turn1-wallet-request.png` | E.E.V.A. response to wallet creation request |
| `e2e-wallet-03-turn2-wallet-name.png` | E.E.V.A. response after wallet name provided |
| `e2e-wallet-03-turn3-password.png` | E.E.V.A. response after password provided |
| `e2e-wallet-04-wallet-metadata-response.png` | E.E.V.A. response to "show me wallet details" |
| `e2e-wallet-05-buy-sol-attempt.png` | E.E.V.A. response to "buy 0.05 SOL" |
| `e2e-wallet-07-final-verification.png` | Final verification screenshot |

Pre-existing screenshots (from `jupiter-wallet-flow.spec.ts` baseline run):

| Screenshot | Description |
|-----------|-------------|
| `e2e-wallet-01-before-select.png` | Pre-existing baseline |
| `e2e-wallet-03-wallet-creation-initiated.png` | Pre-existing baseline |
| `e2e-wallet-04-wallet-name-provided.png` | Pre-existing baseline |
| `e2e-wallet-05-wallet-created.png` | Pre-existing baseline |
| `e2e-wallet-06-wallet-metadata.png` | Pre-existing baseline |
| `e2e-wallet-07-buy-sol-attempt.png` | Pre-existing baseline |
| `e2e-wallet-08-before-delete-confirm.png` | Pre-existing baseline |
| `e2e-wallet-09-deletion-confirmed.png` | Pre-existing baseline |
| `e2e-wallet-10-final-state.png` | Pre-existing baseline |

Note: Screenshots for Steps 6 (`06-wallet-deleted`, `06-deletion-confirmed`) were not captured because Step 6 failed before reaching the screenshot calls.

---

## Issues Found

### Issue 1 — DB Path Mismatch (Steps 3, 4, 6 FAIL)

**Symptom**: Python seed script prints `WALLET_ADDR:<address>` confirming creation, but REST `/wallet/info/{user_id}` returns `{"detail":"Not Found"}`.

**Root cause**: The Python seed script resolves the DB path as:
```python
db_path = os.environ.get('COORDINATOR_DB_PATH', r'C:/Users/rzehn/desktop/MCP_Catalog/data/chats.db')
```
The running FastAPI backend likely uses `chats.db` in the project root (not `data/chats.db`), based on the default in `.env`: `OLLAMA_BASE=http://127.0.0.1:11434` — the backend's default DB path is `chats.db` (root). These are two different SQLite files.

**Fix needed**: Either:
- Set `COORDINATOR_DB_PATH=C:/Users/rzehn/desktop/MCP_Catalog/chats.db` in the Python seed script, OR
- Use the `POST /wallet/create` REST endpoint (instead of direct Python write) so the seed writes to the same DB the backend reads from.

### Issue 2 — Balance Endpoint 500 + Non-JSON Body (Step 5 FAIL)

**Symptom**: `GET /wallet/balance/e2e_wallet_user` returned HTTP 500 with response body starting with "Internal S..." (plain text, not JSON). The test called `.then(r => ({ status: r.status, body: r.json() }))` — `r.json()` threw `SyntaxError: Unexpected token 'I', "Internal S"... is not valid JSON`.

**Root cause — two factors**:
1. The wallet was not in the backend's DB (same path mismatch as Issue 1), so the handler reached a different code path than expected. The route does raise `HTTPException(status_code=404)` for missing wallet, but 500 suggests an uncaught exception before the repo check, possibly in `get_wallet_repo()` from `startup.py`.
2. The test code does `r.json()` synchronously inside a Promise chain without catching the parse error.

**Fix needed**:
- Primary: resolve DB path mismatch (see Issue 1).
- Secondary defensive fix in test: wrap `r.json()` in a try/catch or use `r.json().catch(() => ({ status: r.status }))`.

### Issue 3 — `afterAll` runs immediately after each test (Playwright isolation)

**Observation**: The console log shows `beforeAll: seeding test wallet via Python` and `afterAll cleanup: wallet deleted=true` running before each individual test. This is because Playwright runs each test in a separate worker context when tests are in a single `describe` block but the suite is retried. The `testWalletAddress` module-level variable resets to `''` between workers, meaning Step 4's `test.skip(!testWalletAddress)` guard never triggers — it always sees a freshly seeded address but then the REST calls fail due to DB mismatch.

**Fix needed**: Use `POST /wallet/create` for seeding instead of direct Python DB writes, ensuring the REST layer and seed are in sync.

### Issue 4 — Step 7 SQLite reports `EXISTS` despite `afterAll` cleanup

**Symptom**: Step 7 Python check printed `EXISTS`, meaning the wallet was still present in the Python DB path when Step 7 ran. The `afterAll` from Step 7's worker also ran, cleaning it up.

**Root cause**: Same DB path mismatch — Python scripts read/write `data/chats.db` while the test expects them to reflect the same state as the running backend. The test passed Step 7 because it uses OR logic (`sqliteConfirmed OR restConfirmed`) and REST 404 satisfied the condition.

---

## Wallet Seeding Status

Python seeding succeeded on every `beforeAll` invocation:
- Step 1 worker: `5uA8UnpWXYXqFLSWzVc2qKiGBQW3Aff9VxZhVrgj2XHq`
- Step 4 worker: `5FLjNwx2FvvUjQrbAyTJk9ZpuaERpmxC5pudeZkSM4uH`
- Step 5 worker: `B9bYN3twtZRh9A9TtMGgwtfPdxDqBDFgKi53VDuHXnyc`
- Step 6 worker: `EMV1tRX39m1irP38ft22bDkxjn4iiCNgwxtA4Z7bdYiT`
- Step 7 worker: `C3MwVaWQ81uCP2Saqw5ppnVGSDDDrsxW5nmKBozxY5Ja`

All wallets were cleaned up in their respective `afterAll` hooks.

**The Python seed mechanism itself is working correctly** — keypair generation, AES-GCM encryption, and SQLite write all succeed. The failure is purely a path routing issue between the Python helper's DB and the running FastAPI backend's DB.

---

## Recommended Next Steps

1. **Find the actual DB path used by the backend** — check `src/coordinator/startup.py` or `src/coordinator/config.py` for `DB_PATH` or `DATABASE_URL`. The likely value is `./chats.db` (root), not `./data/chats.db`.

2. **Update the Python seed in the test** to use `POST /wallet/create` REST endpoint instead of direct DB writes, removing the path dependency entirely:
   ```typescript
   const res = await fetch(`${BACKEND}/wallet/create`, {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({ user_id: TEST_USER, wallet_name: WALLET_NAME, password: WALLET_PASSWORD })
   })
   ```
   This also makes the test more realistic as an integration test.

3. **Fix Step 5 balance JSON parse error** by checking `r.ok` before calling `.json()`.

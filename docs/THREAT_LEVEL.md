---
title: Threat Level
status: active
created: 2026-07-04
last_reviewed_on: 2026-07-04
review_in: 6 months
applies_to: nephilim
threat_level: Low
---

# Threat Level — nephilim

A lightweight, living threat model. The `threat_level` frontmatter field above is the
machine-readable rating (Low · Medium · High · Critical, CVSS-aligned) — keep it current.

## Current assessment

| Field | Value |
|-------|-------|
| Threat level | Low (see frontmatter) |
| Owner | Repo maintainer (single-user deployment) |
| Deployment | Local-first: launchd on a Mac Mini, backend `:8000` + static frontend `:3001`, **bound to localhost** (remote access only via SSH tunnel) |
| Last reviewed | 2026-07-04 |

Rated **Low** because the only running deployment is a single-user, always-on Mac Mini
with all listeners on localhost and no public ingress. The rating would rise to **Medium**
the moment the service is exposed to a network (see [Escalation](#escalation)) — at which
point `AUTH_REQUIRED=false` (below) stops being acceptable.

## Trust boundaries

```
[ user chat input ]              [ Brave web results / RAG memory ]
        │                                    │  (untrusted content — may inform,
        ▼                                    ▼   must never *trigger* a tool: ADR-004)
   [ FastAPI coordinator ] ── system prompt ──> [ Ollama (local LLM) ]
        │                                    │
        ├──> [ SQLite (chats.db) ]           └──> [ Brave MCP (Docker, ephemeral) ]
        └──> [ Solana / Jupiter wallet MCP ]  (encrypted private keys; propose→confirm→execute)
                          ▲
                   trust boundary
```

Untrusted data crossing in: (1) the user's chat messages, (2) web-search results and
retrieved RAG memory that get summarized into responses. Trusted: the persona JSON, system
prompt, and local config. The agentic pipeline (ADR-004) enforces a strict trust hierarchy
— retrieved content can inform an answer but can never *trigger* a tool call.

## STRIDE

| Threat | Applies? | Control / mitigation | Status |
|--------|----------|----------------------|--------|
| **S**poofing | Low (local, single-user) | `AUTH_REQUIRED=false` is an *accepted* posture for localhost-only; Google-OAuth+JWT path exists for when auth is turned on | Accepted |
| **T**ampering | Low | `.env` untracked + gitignored; SQLite is local-only; no external writers | OK |
| **R**epudiation | Low | Not a multi-user/audit context; message history persisted with timestamps | N/A |
| **I**nformation disclosure | Medium→controlled | HTTP error bodies return `type(e).__name__`, never `str(e)` (fixed 2026-07-04); wallet private keys AES-GCM encrypted; tool-name + private-key redaction in `_finalize_response` | Mitigated |
| **D**enial of service | Low | Localhost only; no untrusted network ingress | N/A |
| **E**levation of privilege | Low | Per-persona `mcp_access` allowlist; wallet swaps require explicit `user_confirmed` (propose→confirm→execute); injection guard blocks RAG-triggered tool calls | Mitigated |

## OWASP Top 10 checklist

- [x] A01 Broken access control — per-persona `mcp_access`; wallet confirm gate. Auth is off by policy (localhost single-user); revisit before any network exposure.
- [x] A02 Cryptographic failures — wallet private keys AES-GCM encrypted; JWT secret must be supplied (no committed default — fixed 2026-07-04).
- [x] A03 Injection — LLM prompt-injection is the live surface; mitigated by the ADR-004 trust hierarchy + injection guard. No SQL string-building (parameterized repos).
- [x] A04 Insecure design — propose→confirm→execute for financial actions; deterministic middleware, not LLM self-policing.
- [ ] A05 Security misconfiguration — `.env.example`/`.env` flag drift tracked; `AUTH_REQUIRED=false` is deliberate for local use. Recheck on exposure.
- [ ] A06 Vulnerable / outdated components — no automated dependency scanning yet (follow-up; CI added 2026-07-04 is a starting point).
- [x] A07 Identification & authentication failures — OAuth+JWT available; off by policy locally.
- [x] A08 Software & data integrity failures — no committed secrets in the tracked tree (`tracked_artifacts = 0`).
- [ ] A09 Security logging & monitoring failures — app logs errors server-side; no central monitoring (acceptable for single-user).
- [x] A10 SSRF — outbound web calls go only to the Brave MCP; no user-controlled URL fetching.

## Residual risks

Risks accepted for now, with rationale:
- **`AUTH_REQUIRED=false`** — accepted for the localhost-only, single-user deployment. Must flip to `true` (with real JWT-secret handling) before any network exposure. See [SECURITY.md](../SECURITY.md).
- **Leaked-credential rotation unconfirmed** — the historical Atlas `Eeva_Admin` URI (and Brave/JWT) were once committed and pushed ([ADR-002](decisions/002-remove-mongodb-mcp.md)); rotation is an **outstanding action item** tracked in [SECURITY.md](../SECURITY.md). MongoDB is no longer used by nephilim, but the pushed credential must still be treated as compromised.
- **LLM prompt injection** — inherent to any LLM app; bounded (not eliminated) by the ADR-004 trust hierarchy.

## Escalation

If the threat level would rise to **Critical** (e.g. the service is exposed to the public
internet, or a wallet key compromise is suspected): stop the launchd services, rotate all
credentials, enable `AUTH_REQUIRED=true`, and record a post-incident note in
[LESSONS_LEARNED.md](LESSONS_LEARNED.md).

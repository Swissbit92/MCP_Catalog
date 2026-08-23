---
title: Semantic platform (concept architecture)
status: Proposed
created: 2026-08-23
last_reviewed_on: 2026-08-23
review_in: 6 months
applies_to: nephilim
ai_summary: >
  Concept-level layering for an agent/companion platform: data -> semantic ->
  consumer, plus an orthogonal control plane. Open it when deciding where a new
  capability belongs - knowledge vs policy vs behaviour vs config - before
  choosing any technology. Covers the write-authority tiers that double as the
  agent permission model, the "what must not be a fact" boundary rule, where
  the tool brain and the ToolSpec definition/policy split belong, the case for
  running a graph store as a rebuildable projection rather than a system of
  record including what that projection should and should not hold, how
  consumers read through the contract rather than from any store, how the
  interface/policy/ontology split is stored and governed (git compiles,
  data projects), and the sequencing that gates all of it on an eval that does not
  exist yet. Not an implementation plan and not an ADR - nothing here has
  been built.
---

# Semantic platform (concept architecture)

**Status: concept only, and substantially revised 2026-08-23 after research —
see the revision section immediately below, which supersedes anything later
that contradicts it.** Nothing in this document has been built. It exists to
settle *where things belong* before any technology is chosen, so that the
technology argument is about fit rather than preference.

## Why this exists

The system had four defects fixed on 2026-08-23 (see the CHANGELOG entry for
that date). None of them were model or context-size problems — the context
window is 16,384 tokens and the failing turn used ~2,236. They were all wiring
gaps: persona fields with no reader, a reset that did not reset, retrieved text
injected as dialogue, samplers that were silently discarded.

What those defects have in common is that **consumer logic and raw data are the
same code**. `chat_session_service` reaches directly into the message repo,
FAISS and the summary table, assembles a prompt, and hands it to a model. There
is no layer between them, so nothing owns the question "is this still true?"

This document proposes the layer.

## Revision 2026-08-23 — what the research found

**Read this before the rest of the document.** Eleven parallel research agents
fact-checked the claims below against primary sources. Much of what follows was
weakened or refuted. The sections after this one are kept because the reasoning
is still useful, but **the recommendation has shrunk considerably** and the
corrections here take precedence over anything later that contradicts them.

### The central diagnosis was wrong

This document says the previous memory attempts were reverted for want of an
eval. **That is false.** ADR-006 had a rigorous eval, it worked, and it is what
caught the regression — twice (three framing variants scoring 0.708, 0.542,
0.500 against a 0.792 OFF ruler).

The real failure is that **retrieved facts flatten the persona's voice when
injected**. The sequencing table below spends five of six steps on storage and
governance and does not touch that problem at all. It is the blocker; nothing
else matters until it moves.

### Claims that did not survive

| Claim in this document | Finding |
|---|---|
| Ontology-constrained extraction lets a local 24B extract reliably (GraphMERT) | GraphMERT's pipeline **uses Qwen3-32B as a helper throughout**. It shows constrained *pipelines* beat naive prompting — not that a mid-size model extracts unaided. A frontier model also beats it on raw factuality |
| "~30 predicates is safe, 50-80 needs subsetting" | Invented. The cited study's smallest tested schema is **100 relations** — the rule extrapolates below the measured range |
| The ontology compiles into graph constraints | **Neo4j Community enforces property uniqueness only.** Existence, type and key constraints are Enterprise. Cardinality exists in no edition. Validation lives in application code regardless — which removes one of the main reasons to have the graph |
| Policy must not live in the store it governs (implied as standard) | Real principle — its name is **separation of mechanism and policy** — but most production systems (Neo4j Enterprise, Postgres RLS) do the opposite behind a bypass privilege. This design is *stricter than typical*, and should be argued on trusted-computing-base grounds, not as convention |
| Constraints beat scale, generally | **Task-dependent.** Schema constraints help closed-set selection and *degrade* open-ended reasoning. Constrain the classification steps, not the discovery steps |
| Text2Cypher is unproven on a local 24B | Refuted as framed. Neo4j benchmarked and fine-tuned 8B/9B models; **fine-tuning is the dominant lever, not scale** |
| The graph is cheap to drop and rebuild | **Unproven anywhere.** Graphiti's maintainers state they have no migration path; cognee's equivalent is undocumented; LightRAG rebuilds its *vector* index, not the graph. Measure a real rebuild before treating droppability as a property |
| Sleep-time consolidation is a differentiator | Now baseline practice (MemOS, cognee, others) |

Two statistics used here to dismiss vendor benchmarking — "6.4% of LoCoMo's
answer keys are corrupted" and "its judge accepts 62.8% of wrong answers" —
**have no locatable primary source and are retracted.**

### Claims that held, or strengthened

- **Canonical vs derived**: genealogy (Mills's source/information/evidence
  stack), library science (**authority control**) and archival practice
  (**provenance**) all reached the same rule independently — the curated human
  layer stays narrow, human-owned and separate from machine enrichment. And
  GEDCOM collapsed that distinction, every downstream tool inherited the
  breakage, and GEDCOM X never displaced it: **retrofitting this later is
  brutally hard**, which is the argument for one cheap column now.
- **Ontology-first is defended in 2026**, not dated (arXiv:2606.04903).
- **Plain files in git**: verified 20-year and 15-year practitioner accounts
  converge — the failure mode is *tooling* churn, not format churn.
- **Consolidation over per-turn extraction**: RecMem reports **87% lower token
  cost while exceeding** state-of-the-art memory accuracy.
- **Append-only log with derived views**: independently validated by the
  Jul-Aug 2026 arXiv cluster (MemTxn, ChronoMem, GitOfThoughts) — and by
  double-entry bookkeeping, which has run this pattern for 500 years.
- **Verification beats introspection**: self-correction works against
  mechanically checkable rules and fails as "was that good?".

### Over-specified, per practitioners in those fields

Formal OntoClean (essentially no papers since 2020 — keep the two mental
questions, skip the apparatus); NeOn module machinery (four namespaces at ~7-8
predicates each are *sections in one file*; split at ~15-20); SHACL (neosemantics'
own docs warn it degrades on a property graph, and Neo4j Labs' attempt to make it
usable has been abandoned since 2023); four tiers as peer stores (**Tulving
revised episodic/semantic from competing to integrated** — the tiers are not
independent); bi-temporal by default (proposed as a general SQL feature in the
1990s, **rejected as too complex**; most systems use transaction-time only and
add valid-time where a specific question demands it); the control plane as
infrastructure (it is **ABAC**, NIST SP 800-162, and it is a YAML file); the
five-verb contract (no precedent anywhere — real libraries converge on *one*
retrieval verb, and `verify`/`assemble` are plausibly ordinary application code).

### Holes found in the design

- **Provenance laundering during consolidation** (arXiv:2607.29167) — the write-
  authority tiers guard the *extraction* path, but consolidation *rewrites*
  facts and can promote a low-authority fact by rephrasing it. Verify what
  consolidation emits, not only what extraction consumes.
- **Rebuild is only sound for additive schema changes.** A predicate rename or
  split needs a fact-rewrite pass through the YAML, or the rebuild faithfully
  reproduces the old, wrong categorisation.
- **No "held for adjudication" state** — conflicting writes are forced into
  accept or reject (MELD, arXiv:2608.16357).
- **MemTrapBench (Aug 2026): every current memory strategy underperformed a
  no-memory baseline by >10%** on reasoning-integration tasks. Memory is not
  automatically an improvement, and the eval should test for harm.

### The insight to carry furthest

From decades of personal-knowledge-management research: **the multi-year failure
mode is review debt, not authoring debt.** A solo curator does not forget their
own thirty predicates. What kills these systems is that automation removes the
*writing* bottleneck and not the *reading and verifying* one, and that gap widens
silently. Budget review time as the real constraint — every mechanism that
produces facts faster makes the actual bottleneck worse unless it also makes
verification cheaper.

### The revised recommendation

```
 WHAT EXISTS AND WORKS                                     (don't touch)
   SQLite · FAISS · persona JSON · lore wiki (34 typed entities)
   FastAPI + services   ← hand-rolled loop; the biggest agent codebases
                          are hand-rolled. The evidence says keep it.

 THE THREE REAL GAPS                                       (build these)
   1. INVARIANT TESTS                                        ~1 day
      every persona field has a reader
      every session-scoped table clears on reset
      every declared sampler reaches the model
      retrieved text is always tagged, never a live turn
      -- all four defects had this shape; this is the discipline --

   2. BEHAVIOURAL EVAL                                       ~1 day
      30 probes: 12 continuity · 6 commitment · 6 pressure
                 4 knowledge-update · 2 abstention
      20 tune / 10 HELD OUT · binary pass/fail
      judge = purpose-tuned small model, NOT a generic local LLM
      -- gates everything after it --

   3. THE VOICE PROBLEM                                      unknown
      injected facts flatten the persona. killed two attempts.
      THIS is the blocker -- not storage, not schema.

 SMALL, CHEAP, PROVEN ELSEWHERE                          (add when easy)
   memory_facts.source = human | agent    <- ONE column, ONE `if`
   lore wiki -> retrieval                 <- hand-written, no extractor
   event log + checkpoint/replay          <- SQLite. the real gap.
   two-tier memory: session vs long-term  <- every framework converged
   consolidation, not per-turn extraction <- 87% cheaper AND better

 DEFERRED -- with the trigger that would change it              (not now)
   ontology, formal      -> predicates outgrow one YAML file
   graph store / Neo4j   -> ADR-001's own trigger: traversal becomes the
                            primary access pattern, OR thousands of
                            densely-linked nodes. You have 34.
   bi-temporal validity  -> a specific question needs it
   control plane, 5 verbs-> a SECOND consumer exists
   graph-as-projection   -> UNPROVEN ANYWHERE. Measure a real rebuild
                            before believing it is cheap.
```

Everything below this section predates the research and is retained for its
reasoning, not as a plan.


## The frame

Three layers on the knowledge axis, plus one plane that cuts across all of
them.

```
                                        ┌────────────────────────────┐
 ╔════════════════════════════════════╗ │ CONTROL PLANE              │
 ║ CONSUMER LAYER      (behaviour)    ║ │ (policy — "what MAY happen")│
 ║                                    ║ │                            │
 ║  Gwen  Nyx  Aegis  Solace  Eeva …  ║ │  toolset grants per persona│
 ║  React UI    Telegram gateway      ║ │  blast_radius · HITL       │
 ║                                    ║ │  nsfw / safesearch floor   │
 ║  ┌──────────────────────────────┐  ║ │  lane eligibility          │
 ║  │ TOOL BRAIN — decide + fill   │  ║◀┤    (bge-m3 router, 0.66)   │
 ║  │ args, then synthesise        │  ║ │  agentic workflows         │
 ║  └──────────────┬───────────────┘  ║ │                            │
 ║                 │ every call       ║ │  ENFORCEMENT POINT:        │
 ║                 ▼                  ║ │  ToolCallInterceptor       │
 ║        ┌─────────────────┐         ║ │  (consumer action meets    │
 ║        │  INTERCEPTOR    │─────────╫▶│   control-plane policy)    │
 ║        └─────────────────┘         ║ │                            │
 ║                                    ║ │                            │
 ║  VOLATILE scene state lives HERE,  ║ │                            │
 ║  in the turn. Never persisted.     ║ │                            │
 ╚════════════════════════════════════╝ │                            │
            │ asks         ▲ answers    │                            │
            ▼              │            │                            │
 ┌────────────────────────────────────┐ │                            │
 │ resolve · traverse · search ·      │ │                            │
 │ verify · assemble · CYPHER ◀───────┼─┤  ← the agentic verb:       │
 │                        THE CONTRACT│ │    an agent that COMPOSES  │
 ├────────────────────────────────────┤ │    a query, not one that   │
 │ SEMANTIC LAYER    ("what is TRUE") │ │    is handed facts         │
 │                                    │ │                            │
 │   ┌──────────────────────────┐     │ │                            │
 │   │ ONTOLOGY — the spine     │     │ │                            │
 │   │ drives extraction, not   │     │ │                            │
 │   │ emergent from it         │     │ │                            │
 │   └──────────────────────────┘     │ │                            │
 │                                    │ │                            │
 │  CANONICAL  ← human-write-only     │ │                            │
 │    persona identity · hard rules   │ │                            │
 │    world lore · asserted bio       │ │                            │
 │    ★ VERIFICATION TARGET           │ │                            │
 │                                    │ │                            │
 │  DERIVED    ← agent-writable       │ │                            │
 │    bi-temporal · provenance ·      │ │                            │
 │    confidence · supersession       │ │                            │
 │                                    │ │                            │
 │  CAPABILITY MODEL                  │ │                            │
 │    what a tool IS (defn, args)     │ │   ...vs the control plane, │
 │    ── discoverable by an agent ──  │ │      which owns who may    │
 │                                    │ │      fire it               │
 │  ══ vector index over EPISODIC ══  │ │                            │
 │     graph holds the vector ids     │ │                            │
 │                                    │ │                            │
 │  ┌─ STORES ────────────────────┐   │ │                            │
 │  │ SQLite   = source of truth  │   │ │                            │
 │  │ FAISS    = embeddings       │   │ │                            │
 │  │ Neo4j    = PROJECTION       │   │ │                            │
 │  │   rebuildable · droppable · │   │ │                            │
 │  │   never written to directly │   │ │                            │
 │  └─────────────────────────────┘   │ │                            │
 └────────────────────────────────────┘ │                            │
            │ projects     ▲ extracts   │                            │
            ▼  (read)      │  (write)   │                            │
 ┌────────────────────────────────────┐ │                            │
 │ DATA LAYER — raw, append-only      │ │                            │
 │   chat history — verbatim, forever │ │                            │
 │   lore source — md + frontmatter   │ │                            │
 │   ╌╌ trading collections ╌╌╌╌╌╌╌   │ │                            │
 │      READ-ONLY. Never bind back.   │ └────────────────────────────┘
 └────────────────────────────────────┘
```

Seven choices in that picture are deliberate.

**The arrows go both ways.** `projects (read)` down, `extracts (write)` up. A
one-way pipeline cannot express "when a message is deleted, the fact derived
from it must be invalidated" — which is exactly the bug that let a 2026-07-05
summary outlive the messages it summarised.

**`extracts (write)` is the dangerous arrow.** It is the only path by which
agent-generated content becomes durable. Everything in the write-authority
design exists to make it safe: it may write DERIVED, never CANONICAL. If only
one guard is ever built, build that one.

**The contract sits above the semantic layer, not inside it.** The verbs are
the entire public surface. A consumer never learns whether `verify` resolved
through a traversal or a cosine distance. This is what makes internals
swappable, and what makes the bypass (`chat_session_service` → repositories) a
visible violation rather than normal practice.

**`CYPHER` is the agentic verb, and the riskiest one.** An agent that composes
a query is qualitatively more capable than one handed pre-fetched facts — that
is the honest meaning of "agentic-ready data". It is also untested on a local
24B model, where the usual assumption of a frontier model does not hold. See
the open question in *Stores*.

**The control plane is a column, not a fourth row.** Policy is cross-cutting.
The line: the control plane answers *what may happen*; the semantic layer
answers *what is true*. Agentic workflows belong there rather than in
consumers — orchestration is control, and putting it in the consumer layer is
how it ends up smeared across persona JSON.

**VOLATILE has no box.** Scene state lives in the turn and is never persisted
anywhere, not even episodically. It is drawn inside consumers so that nobody
later gives it a table.

**The trading collections are dashed and one-way.** CRA and eeva-exec never
bind back. The ecosystem's no-direct-imports invariant is untouched.

## Where things belong

| Thing | Layer | Note |
|---|---|---|
| Chat history | Data | Verbatim, forever. The accurate substrate |
| Price / market data | Data | A *feed* — external, time-series. Different lifecycle from a record of interaction |
| World lore | **Semantic** | Hand-authored canonical knowledge; the finished product, not raw input |
| Ontology, KG | Semantic | The ontology specifically is the spine |
| User bio | Semantic | Split by authority: asserted = CANONICAL, inferred = DERIVED |
| Persona traits + hard rules | Semantic | |
| Persona style config | **Consumer** | Voice tics, emoji policy, reply shape. Negating it yields a different design choice, not a falsehood |
| Metric *definitions* | Semantic | |
| Metric *values* | **Neither** | Volatile or derived. Storing them as facts rebuilds the stale-summary bug |
| Long-term memory / facts | Semantic | |
| "Contracts" | **Split** | A data contract is the ontology. A behavioural contract is policy |
| Agentic workflows | **Control plane** | Orchestration is control, not consumption |
| What a tool *is* (definition, args) | **Semantic** | Knowledge about a capability; discoverable by an agent |
| Who may fire a tool (grants, blast radius, HITL) | **Control plane** | Policy |
| The tool brain loop | **Consumer** | Behaviour — an agent doing work |
| UI, persona chat, gateway | Consumer | |
| Scene state | **Nowhere durable** | The context window's job |

## Where the tool brain lives

The tool brain is a **consumer**. The registry splits in two.

`ToolSpec` (`tools/registry.py`) currently bundles two different kinds of thing
in one dataclass, and that conflation is the reason the question "may Gwen call
`video_search`?" cannot be answered without reading code:

| Half of `ToolSpec` | What it is | Belongs in |
|---|---|---|
| definition — OpenAI-function dict, description, args | knowledge about a capability: what this tool **is** | Semantic |
| `toolset`, `blast_radius`, `requires_hitl`, nsfw-modulating | policy: who may fire it, with what guardrails | Control plane |

Today the decision is spread across **six** places: persona JSON
(`toolsets`/`mcp_access`/`tools`/`nsfw`), `registry.py` (`TOOLSET_MCP_ALIASES`
plus the legacy rarity fallback), the bge-m3 semantic router (lane eligibility,
threshold 0.66), `routes/chat.py::_try_tool_brain` (narrows the offered
surface), `ToolCallInterceptor` (argument allowlist, hard blocks, HITL), and
`tools/executor_bindings.py` (safesearch clamp).

Under this frame:

- **Semantic** owns the capability model — what tools exist, what they do, what
  arguments they take. This is what makes a toolset *discoverable* by an agent
  rather than hard-coded into a prompt.
- **Control plane** owns grants, blast radius, HITL, the safesearch floor and
  lane eligibility. One declarative place to answer the question above. Note
  the router is a *learned* component sitting in the control plane — that is
  fine; a control plane may contain ML.
- **Consumer** owns the loop itself: deciding, filling arguments, synthesising
  in voice.

`ToolCallInterceptor` is the interesting case. It is the **enforcement point**
where a consumer action meets control-plane policy — which is exactly where it
already sits, and it should not move. The change is that it reads policy from
one source instead of three.

## Stores: Neo4j as a projection, not a system of record

The recommendation is to run a graph store as a **rebuildable read-model**:

- SQLite remains the source of truth. Extraction writes there.
- The graph is derived and can be dropped and rebuilt with one command.
- No dual-write problem, no migration, no consistency burden.
- If the graph is wrong, rebuild it. If it never earns its place, delete a
  container.

Where a graph genuinely earns its keep, in rough order of strength:

| Capability | Assessment |
|---|---|
| Composable queries (Text2Cypher) | Strongest agentic argument — an agent that *writes* a query beats one handed pre-fetched facts |
| Disambiguation | Alias edges make "Debs" → "Debbie" **deterministic**; embeddings only make it probable. For a companion full of nicknames, that is the difference between reliable and usually-right |
| Multi-hop | Real. Three hops is one line of Cypher and a recursive CTE in SQL |
| Entity resolution / dedup | Real but partly borrowable — the merge is rewiring edges rather than rewriting rows |
| Auditability | Reasoning-to-entity edges, plus the ability to *look at* memory and correct it by hand |

Where it does nothing: it does not fix character drift, and it does not fix the
voice-injection problem that ended two prior attempts. At the current scale
(12 facts, 34 lore entities) every traversal is trivial — none of the wins
above will be *felt* until there is volume.

**The open question to settle first, cheaply:** Text2Cypher is normally run on
frontier models. On a local abliterated 24B it is unproven. Give it the schema
and ~20 natural questions and measure the valid-Cypher rate. Above roughly 80%
the agentic argument holds; near 40% the graph may still be useful but the
agent will not be querying it directly.

Ontology-driven extraction is supported by the tooling rather than emergent
from it — `SimpleKGPipeline` accepts user-defined `node_types`,
`relationship_types` and `patterns`, which is the mechanism that makes
constrained extraction viable on a small local model.

### What goes into the projection

The projection rule is: **project exactly what the ontology models, and nothing
else.** That buys four properties.

- **No orphans.** The graph structurally cannot hold something the ontology
  does not describe.
- **Deterministic rebuild.** Same source plus same ontology produces the same
  graph.
- **Versioned provenance.** The graph is stamped with the ontology version that
  built it.
- **The residue is a measurement.** Anything extraction produces that cannot
  map to a predicate is not lost data — it is a signal that the ontology is
  incomplete or the extractor is drifting. If a large share of extracted facts
  do not fit, that is worth knowing, and no other design surfaces it for free.

**Three inputs, not one.** "Derived from source data" is too narrow: authored
content is asserted, not derived, and putting it through an extraction pipeline
it does not need would be a mistake.

| Input | Example | Mechanism | Failure mode |
|---|---|---|---|
| **Authored** | Lore wiki, persona canonical fields | Compiled — deterministic, no LLM | A parse error: loud and obvious |
| **Extracted** | Facts from conversation | Ontology-constrained LLM extraction | Silent wrong facts — needs confidence, provenance, and the residue metric |
| **Mirrored** | Tool registry, trading positions | Straight structural mapping | Schema drift at the source |

**It is a compile, not a sync.** "Sync" implies ongoing reconciliation between
two stores that can disagree, which is precisely the expense a projection
exists to avoid. The ontology is an *input to a build*:
`source + ontology → graph`. When the ontology changes, rebuild rather than
migrate.

Two paths, kept separate:

- **Append** — incremental, per-message, cheap. Normal operation.
- **Rebuild** — full, from scratch, on ontology change. Rare.

Worth designing for deliberately: **the full rebuild is the correctness
oracle.** Diffing an incrementally-built graph against a fresh rebuild makes
any divergence a bug in the incremental path — a self-check most systems cannot
perform.

**Store the skeleton, not the flesh.**

| In the graph | Stays outside it |
|---|---|
| Entities (resolved, deduped) + **alias edges** | Message text → SQLite |
| Typed relations between entities | Embedding vectors → FAISS |
| CANONICAL facts as edge properties | Volatile scene state → the turn |
| DERIVED facts as reified nodes: validity window, confidence, **extractor version**, edge to its `Quote` | Style config → persona JSON |
| `Quote` nodes — id, span and session/message reference **only, never the text** | Metric values → computed on read |
| `Event` nodes (fixed slots) | |
| Capability / Tool / Toolset, mirrored from the registry | |
| **Vector ids** pointing into the episodic store | |

The graph holds ids, types, relations, validity and provenance; the content
stays where it is already good. Three reasons beyond tidiness: traversals stay
fast because the graph stays small, rebuilds stay cheap because no text is
copied, and it honours the verbatim-beats-structuring evidence — the original
can never be lost, because it was never moved.

**Build this in from day one: stamp every projected fact with the extractor
version and the ontology version.** Rebuilding does not fix bad facts, it
reproduces them deterministically. What saves you is being able to answer
"which facts did the buggy extractor write between these two dates?" and
invalidate that batch. Almost nothing in this space can answer that question,
and it costs two columns.


## How consumers read

**Agents read from the contract, never from a store.** If a persona knows it is
talking to a graph, the layer has already failed. Four things depend on that
line holding:

- The store stays genuinely swappable — which is the only reason running a
  graph as a projection is a low-risk experiment rather than a commitment.
- Retrieval strategy lives in one place instead of being smeared across every
  persona.
- There is one seam to log, cache and audit at.
- A store outage degrades `assemble` gracefully instead of breaking every
  consumer.

Behind the contract, the verbs fan out by question shape:

| Verb | Store | Why that one |
|---|---|---|
| `resolve(alias) → entity` | Graph only | Alias edges are deterministic — "Debs" resolves to Debbie every time, not usually |
| `traverse(entity, depth, as_of)` | Graph only | Multi-hop and temporal; what relational storage is worst at |
| `search(text, k) → episode ids` | Vector only | Fuzzy recall over verbatim; what graphs are worst at |
| `verify(claim)` | Graph first | Canonical facts are the target |
| `assemble(turn)` | Everything — the orchestrator | Where the hybrid actually happens |
| `CYPHER` | Graph, agent-composed | The agentic capability, and the untested one |

**`verify` must be three-valued — `true` / `false` / `unknown`, never a
boolean.** Most claims in a companion conversation are simply absent from the
fact store, and treating "not found" as "false" would make the groundedness
gate abstain on everything. That single detail decides whether gate-as-lookup
is an improvement on the classifier or strictly worse than it.

### The assemble path

```
turn ─┬─▶ resolve mentions ──────────────▶ entity ids        [graph]
      │
      ├─▶ traverse those entities ───────▶ current facts     [graph]
      │      (as_of = now, canonical + derived)
      │
      ├─▶ graph yields episode ids ──────▶ fetch by ID       [SQLite]
      │      ("which episodes matter")      ("the text")
      │
      ├─▶ similarity pass for whatever ──▶ episode ids       [vector]
      │      the graph did not anticipate
      │
      ├─▶ frame everything with epistemic labels
      └─▶ budget, drop lowest priority first
```

Two steps carry the weight. **The graph says *which* episodes; the source store
gives the *text*** — fetch by id, not by similarity, whenever the graph already
knows the answer. And **the similarity pass is not redundant**: it is the
vector-to-graph direction, covering turns that touch something never modelled.
Build only graph-first and the system is blind to the unanticipated.

### The default turn should not touch the graph

Most companion turns need nothing from it — scene state, the last few turns and
the persona's constraints are a normal reply. The graph earns its place on the
*rare* turn: "what is her sister called", "what did we do last August".

So `assemble` should be **cheap by default and expensive on demand**, triggered
when a turn names an entity or asks a recall question. Otherwise latency is
added to every reply for a benefit that lands on a small minority of them.

### Different agent classes, different read patterns

This is the honest form of the multi-consumer argument — not many personas with
identical needs, but agent *classes* whose read mixes genuinely differ:

| Consumer | Heavy on | Light on |
|---|---|---|
| A companion persona | `assemble`, `search` (episodic recall) | `verify` |
| A wallet/trading-aware persona | `verify` (claims about money), `traverse` | `search` |
| A future research agent | `CYPHER`, `traverse` | `assemble` |


## The contract, and what governs it

"Contract" is doing two jobs and they must not merge. Conflating the interface
with the policy is precisely the mistake the control plane exists to prevent.

| Artifact | What it is | Format | Rate of change |
|---|---|---|---|
| **Interface** | The shape of the question — the verbs | **Code** (a Python `Protocol`) | Rarely — only when the *kinds* of question change |
| **Policy** | Who may ask what | **Declarative — YAML** | Often — every new persona or capability |
| **Ontology** | What can be said at all | Declarative schema, drives extraction | Slowly |

The interface is code rather than config deliberately: it is typed, testable,
and mistakes surface at import rather than at runtime. Policy is YAML because it
is configuration that should be diffable and reviewable without reading code —
a grant change should be visible in a pull request.

### The interface carries no policy

```python
class SemanticLayer(Protocol):
    def resolve(self, ctx: CallerContext, alias: str) -> EntityId | None: ...
    def traverse(self, ctx: CallerContext, entity: EntityId,
                 depth: int = 1, as_of: datetime | None = None) -> list[Fact]: ...
    def search(self, ctx: CallerContext, text: str, k: int) -> list[EpisodeId]: ...
    def verify(self, ctx: CallerContext, claim: Claim) -> Verdict: ...   # true|false|unknown
    def assemble(self, ctx: CallerContext, turn: Turn) -> Context: ...
```

**`ctx` is the non-negotiable part.** Without caller identity in every
signature, nothing can be enforced at this seam and checks fall back into each
consumer — the smearing problem the layer exists to end. It is also the one
element that is genuinely painful to retrofit: adding a first parameter to
every method across every call site later is expensive, and adding it now is
free.

### The contract enforces; the control plane decides

The same relationship `ToolCallInterceptor` already has with tool policy — an
enforcement point, not a decision.

```yaml
# control-plane policy, illustrative
consumers:
  gwen:
    subject_areas:   [companion]          # ontology modules it may READ
    tiers:           {read: [canonical, derived, episodic], write: []}
    toolsets:        [web]

  eeva:
    subject_areas:   [companion, trading]
    tiers:           {read: [canonical, derived, episodic], write: []}
    toolsets:        [web, wallet]
    guardrails:      {execute_swap: {hitl: required, blast_radius: high}}

  extractor:                              # a background agent, not a persona
    subject_areas:   [companion]
    tiers:           {read: [episodic], write: [derived]}   # never canonical
    toolsets:        []
```

**Policy is expressible only because the ontology is modular.**
`subject_areas: [companion]` means something because the ontology *has* named
modules. Modularity is not tidiness — it is what makes governance sayable.

### A worked example: two orthogonal questions

"May Gwen look up crypto price data or trading information?" is two questions
with different answers:

| Question | Governed by | Answer |
|---|---|---|
| May she call `web_search` for a BTC price? | **Tool grant** | Yes — she holds the `web` toolset, and a public price is public |
| May she read *the user's positions*? | **Subject-area grant** | No — she has no `trading` subject area |

She could say what Bitcoin is trading at and could not say what the user holds.
Both dimensions are needed: tool grants alone cannot express it (the same
`web_search` is fine for one and irrelevant to the other), and subject-area
grants alone cannot either.

### Where it lives: git, not the graph

**Policy cannot live in the store it governs.** To know whether you may read
the graph you would have to read the graph — a circular dependency, and a
security smell besides, since anyone who compromises the graph rewrites their
own permissions. Policy must be readable when the database is down, and
readable *before* authorisation is established.

The general line is that **config compiles and data projects**:

| | Source of truth | Ends up in |
|---|---|---|
| Interface (code) | git | it *is* the code |
| Policy (grants) | git | loaded at startup |
| Ontology (schema) | git | compiled → graph constraints + extraction config |
| Lore content | git (markdown) | compiled → graph nodes |
| Extracted facts | **SQLite** | projected → graph |
| Episode text | SQLite | stays put |
| Embeddings | vector store | stays put |

Nothing is a system of record in two places.

Suggested shape, inside this repo rather than a separate one — a separate repo
now would be the generality trap:

```
nephilim/
  semantic/
    ontology/
      upper.yaml         # Entity, Agent, Fact, Quote, Event, provenance
      companion.yaml     # persona / user domain
      trading.yaml       # projected subject area
      routing.yaml       # capability module
    policy/
      consumers.yaml     # grants, tiers, guardrails
    interface.py         # the Protocol
```

**YAML for schema, markdown for content.** YAML because graph-construction
pipelines take plain node-type/relationship-type dictionaries, because it is
diffable, and because SHACL or Turtle can be *generated* from it rather than
hand-maintained — precision that nobody edits happily across five years is
precision that decays. **Do not migrate the lore wiki to YAML**: it is content,
it works, and markdown-with-frontmatter is the format practitioners report
surviving longest (see [ADR-001](../decisions/001-lore-as-typed-markdown-wiki-not-a-graph-db.md)).

**Nothing lives only in the graph, by construction.** Every node traces to
either a git artifact (compiled) or SQLite (projected). If the graph cannot be
rebuilt from those two, something has leaked in that should not be there — an
invariant worth testing rather than merely asserting.

### Two cautions

**Do not build all of this now.** One user, a handful of personas, no external
consumers. Full role-based access control would be over-engineering of exactly
the kind this document argues against. The minimum that is *not* retrofittable
is `ctx` in the signatures; tiers, guardrails and deny-lists can arrive when a
second agent class actually exists.

**Do not create a second source of truth.** `toolsets` / `mcp_access` / `nsfw`
already live in persona JSON. A control-plane file landing *beside* them gives
"what may Gwen do?" two answers that will diverge — worse than one imperfect
answer. The control plane must **absorb** those fields, not sit next to them.
That is a migration, and it is the part most likely to be skipped and then
regretted.


## Write authority is the primary axis

Not topic — *who may write it*. This is also the agent permission model, which
is what makes the platform agent-ready rather than merely agent-adjacent.

| Tier | Contents | Writer | Role |
|---|---|---|---|
| CANONICAL | Persona identity, hard constraints, world lore, asserted bio | Human only | The verification target |
| DERIVED | Noticed preferences, evolving relationship state | LLM extractor | Enriches; never authoritative |
| EPISODIC | What happened, verbatim | Append-only | The accurate substrate |
| VOLATILE | Scene state, mood | Rewritten per turn | Never persisted |

No shipped system implements this four-way split. Letta has a binary
read-only-vs-editable gate with no confidence or temporal layer; Mem0 has no
authored-vs-inferred separation at all; Graphiti is essentially the DERIVED
tier built well but has **no CANONICAL tier** — everything traces to an
ingested episode and nothing is structurally protected from extractor
overwrite. Character Card V2/V3 does not separate factual from style fields
either, so adopting it would not fix the problem.

The failure this defends against is formalised in the literature as a
hallucinated fact persisting as a false premise for every subsequent step.
The in-repo evidence is `personas/*.json`, which mixes canonical biography,
style config and hard behavioural rules in one flat uniformly-editable object
with no structural signal that `boundaries.content` is non-negotiable while
`voice.tics` is a free knob.

## What must not be a fact

Every extraction step is lossy. Promote to a typed fact only when the value is
**(a)** durable, **(b)** something a future query will filter or join on, and
**(c)** losing the exact wording does not matter.

Clause (c) is decisive here: **roleplay-register content fails it by design —
tone *is* the content** — so it must never be compressed into a triple. It
stays verbatim, which is also the more accurate retrieval substrate for that
material.

Stays out entirely: style config (test: if negating it produces a different
valid *design choice* rather than a falsehood, it is config); behavioural rules
(CANONICAL but deontic — enforced and checked, not recalled, so they get their
own namespace); one-off mentions; scene state; and routing eligibility (a
policy assertion, not a claim that could be true or false about the world).

## Why this is justified

Not multiplicity. Eight personas are closer to one consumer wearing eight
costumes — the variation between them is style config, which is not semantic.

**The justification is temporal.** One relationship over five years needs
memory that is auditable, hand-correctable, temporally valid and provenanced.
That points at different priorities than "platform" would:

| If the driver were… | Priorities would be… |
|---|---|
| Multi-consumer reuse | Stable interfaces, generality, versioning |
| **Longevity (the real one)** | **Provenance, bi-temporal validity, hand-correction ergonomics, drift detection** |

Reuse posture is **extractable, not general**. There are no external consumers
and none planned, so there is no interface-stability obligation. Buy modularity
(clean seams so it *can* be lifted later); buy no generality (abstraction over
consumers that do not exist). The rule of three applies: do not abstract until
the third real consumer.

## Sequencing

| # | Step | Why here |
|---|---|---|
| 0 | ✅ Fix the wiring | Done 2026-08-23. Carves out the seam; would have poisoned anything built on top |
| 1 | **Build the behavioural eval** | Gates everything after it |
| 2 | Write the competency questions | They *are* the scope definition |
| 3 | Wire the lore wiki to retrieval | Hand-curated, already typed, zero extraction risk |
| 4 | Close the FK gap in `memory_facts` | One-hop traversal, no new infrastructure |
| 5 | Persona/character module + write-authority tiers | The actual gap |
| 6 | Graph store, if the traversals justify it | Decide when you know what you are traversing |

**The bottleneck is not the schema.** Two attempts to inject even flat memory
facts into persona voice both failed — M5 reverted when the model changed, the
reframing rework closed 2026-08-11 after three variants regressed. A graph
inherits that problem whole: if retrieved facts cannot be rendered into voice,
it makes no difference whether they came from a table or a traversal.

And the obvious ruler is the wrong one: static self-report consistency checks
disagree with live behavioural judges about which architecture is stable, so an
NLI detector alone would produce confident wrong answers. The eval needs a
behavioural component.

## The first target worth building

**The groundedness gate stops guessing and starts looking up.** Today
`GroundednessGateService` runs a second LLM to classify whether a draft asserts
an unverified live-state claim — a probabilistic judgement about whether
something is checkable. With real position facts carrying provenance and
validity windows, that becomes: *is this claim consistent with a fact whose
validity window covers now?*

Deterministic, auditable, and **falsifiable** — gate false-positive and
false-negative rates are measurable before and after. That last property is
why it should be first.

## Related

- [ADR-006 — Companion memory and continuity](../decisions/006-companion-memory-and-continuity-eval-first.md)
- [ADR-007 — Generation-time groundedness gate](../decisions/007-generation-time-groundedness-gate.md)
- [ADR-008 — Two-brain split](../decisions/008-two-brain-split-tool-brain-voice-brain.md)
- [ADR-009 — Layered toolkit registry & toolsets](../decisions/009-layered-toolkit-registry-generic-web-toolset-inner-wisdom-skills.md)
- [Architecture](../ARCHITECTURE.md)

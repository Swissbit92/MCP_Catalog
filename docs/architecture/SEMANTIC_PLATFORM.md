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
  data projects), how monitoring/security/install fall out of those choices,
  and the sequencing that gates all of it on an eval that does not
  exist yet. Not an implementation plan and not an ADR - nothing here has
  been built.
---

# Semantic platform (concept architecture)

**Status: concept only.** Nothing in this document has been built. It exists to
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

## The frame

Three layers on the knowledge axis, plus one plane that cuts across all of
them.

```
                                        ┌────────────────────────────┐
 ╔════════════════════════════════════╗ │ CONTROL PLANE              │
 ║ CONSUMER LAYER      (behaviour)    ║ │ policy — "what MAY happen" │
 ║                                    ║ │ fail CLOSED (Cube defaults │
 ║  Gwen  Nyx  Aegis  Eeva  …  UI     ║ │ open — diverge on purpose) │
 ║                                    ║ │                            │
 ║  ┌──────────────────────────────┐  ║ │  grants: subject_area,     │
 ║  │ TOOL BRAIN / AGENT           │  ║◀┤   tier, toolset            │
 ║  │  PROPOSES a call or query    │  ║ │  + status: proposed|active │
 ║  └──────────────┬───────────────┘  ║ │        |deprecated|retired │
 ║                 │                  ║ │  + reason: why it exists   │
 ║  VOLATILE scene state — in the     ║ │                            │
 ║  turn only. Never persisted.       ║ │  ENFORCE AT QUERY-BUILD,   │
 ╚═════════════════╪══════════════════╝ │  never post-filter         │
                   │ every call         │                            │
                   ▼                    │                            │
        ┌─────────────────────┐         │                            │
        │  GATED RUNNER       │◀────────┤  ctx: CallerContext        │
        │  • grammar-checked  │         │  threaded through EVERY    │
        │  • schema vocab ok  │         │  verb. No framework does   │
        │  • READ-ONLY role   │         │  this — it is the gap.     │
        │  • row/depth caps   │         │                            │
        └──────────┬──────────┘         │                            │
                   ▼                    │                            │
 ┌────────────────────────────────────┐ │                            │
 │ resolve · traverse · search ·      │ │                            │
 │ verify(3-valued) · assemble ·      │ │                            │
 │ CYPHER          ◀── THE CONTRACT   │ │                            │
 ├────────────────────────────────────┤ │                            │
 │ SEMANTIC LAYER    "what is TRUE"   │ │                            │
 │                                    │ │                            │
 │   ONTOLOGY — the spine.            │ │                            │
 │   Fails by SILENT STALENESS,       │ │                            │
 │   not by needing migration.        │ │                            │
 │                                    │ │                            │
 │  CANONICAL  ← human-write-only     │ │                            │
 │    ▲                               │ │                            │
 │    │ REVIEW GATE (sleep-time agent │ │                            │
 │    │ proposes; promotion is gated) │ │                            │
 │    │                               │ │                            │
 │  DERIVED    ← agent-writable       │ │                            │
 │    4 timestamps, not 2:            │ │                            │
 │    created_at · valid_at ·         │ │                            │
 │    invalid_at · expired_at         │ │                            │
 │    (system-time = "what did we     │ │                            │
 │     BELIEVE on this date")         │ │                            │
 │                                    │ │                            │
 │  ┌─ STORES ────────────────────┐   │ │                            │
 │  │ SQLite = source of truth    │   │ │                            │
 │  │   ⚠ MUST NOT hard-delete    │   │ │                            │
 │  │     the fact-bearing tier,  │   │ │                            │
 │  │     or the rebuild oracle   │   │ │                            │
 │  │     INVERTS                 │   │ │                            │
 │  │ Vectors = most likely to    │   │ │                            │
 │  │   go stale SILENTLY         │   │ │                            │
 │  │ Graph  = PROJECTION         │   │ │                            │
 │  │   node id MUST be a         │   │ │                            │
 │  │   deterministic fn of       │   │ │                            │
 │  │   source keys — or every    │   │ │                            │
 │  │   diff is spurious drift    │   │ │                            │
 │  └─────────────────────────────┘   │ │                            │
 └────────────────────────────────────┘ │                            │
        ▲ projects    │ extracts        │                            │
        │  (read)     ▼  (write)        │                            │
   ┌────┴─────────────────────────┐     │                            │
   │  GRAPH PRUNING               │     │                            │
   │  drops anything violating    │     │                            │
   │  the schema — correctness    │     │                            │
   │  moves OFF model quality     │     │                            │
   │         │                    │     │                            │
   │         └──▶ RESIDUE METRIC  │     │                            │
   │              what could NOT  │     │                            │
   │              map = the ONLY  │     │                            │
   │              staleness alarm │     │                            │
   └────┬─────────────────────────┘     │                            │
        ▼                               │                            │
 ┌────────────────────────────────────┐ │                            │
 │ DATA LAYER — raw, append-only      │ │                            │
 │   chat history — verbatim, forever │ │                            │
 │   lore source — md + frontmatter   │ │                            │
 │   tombstone log (if deletes exist) │ │                            │
 │   ╌╌ trading collections ╌╌ R/O ╌╌ │ └────────────────────────────┘
 └────────────────────────────────────┘

 LITMUS TEST: delete the derived layer and rebuild from canonical alone.
              If you can't, the separation isn't clean.
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


## What external research changed (2026-08-23)

Five parallel research streams reviewed this design with a brief to *improve*
it rather than accept or reject it. The strongest single finding was not
agreement in the literature but **independent convergence**: a production
postmortem (Jeremy Daly, *Context Engineering for Commercial Agent Systems*)
arrives at the same canonical/projection split — *"the inference loop writes
minimal canonical records, everything else is projection"* — and reports three
failures this design already guards against: guardrails silently crowded out of
context, vector indexes becoming unaudited systems of record, and subagent
context-inheritance causing nondeterminism.

### Two hazards found — both cheap now, expensive later

**1. The rebuild oracle inverts if the source hard-deletes.** If the
fact-bearing tier ever hard-deletes rows, a rebuild reading *current* state
cannot reconstruct history the incremental path already captured through a
supersede fact. The diff then flags the **correct** path as buggy. This is live
today: `/reset` hard-deletes messages. **Decision required before building
anything**: either the fact-bearing tier never hard-deletes, or the rebuild
takes an append-only tombstone log as a second input rather than current state
alone. Debezium's tombstone events and XTDB's "deleting only erases visibility,
never the log" both confirm supersede-never-delete is textbook — but only if the
source honours it too.

**2. Node identity must be a deterministic function of source-fact keys**, never
an ingestion-order-dependent surrogate id. Otherwise every rebuild reports
spurious drift and the oracle becomes noise people learn to ignore.

### The correction that matters most

The design had been guarding against **migration pain** ("rebuild, don't
migrate"). That is the wrong threat. Practitioner evidence is that **ontologies
fail by silent staleness and drift, not by needing migrations** — the schema
quietly stops describing reality while everything keeps running and nothing
errors.

That **promotes the residue metric from a nice property to the primary
safeguard.** Extraction output that cannot map to any predicate is the only
signal that the ontology is drifting.

A sharper statement of the projection principle, worth adopting verbatim
(Oracle, *Persistent Memory and Derived Context*):

> Delete the derived layer and rebuild it from canonical alone. If you can't,
> the separation isn't clean.

...with the specific hazard it names: a fact corrected in canonical storage
while the **embedding built from the old text was never invalidated**. The
vector index is the component most likely to go stale silently.

### Upgrades adopted

| Change | Source |
|---|---|
| **Four timestamps, not two** — `created_at`/`valid_at`/`invalid_at`/`expired_at`. System-time answers "what did we *believe* on this date", which is how a bad extractor batch gets audited | Graphiti |
| **`CYPHER` becomes propose/execute.** The agent composes; a gated runner validates grammar and schema vocabulary and executes read-only | AG2's `register_for_llm` vs `register_for_execution` |
| **A review gate on DERIVED → CANONICAL.** Background consolidation *proposes* a promotion; it lands through a gate. This path was previously unspecified | Letta sleep-time agents |
| **Extraction correctness moves off model quality.** Deterministic post-hoc pruning drops anything violating the schema | Neo4j `GraphPruning` |
| **Enforce at query construction, not post-filtering** | Cube `access_policy` / `queryRewrite` |
| **Fail closed.** Cube defaults to all-rows-public; diverge deliberately | Cube |
| **Add `status` (proposed/active/deprecated/retired) and `reason` to grants** — both matter more for an agent consumer than a human one | Open Data Contract Standard |

### The `CYPHER` verb: conditional GO

Raw prompted Text2Cypher on an unconstrained local model is **not safe to hand
an agent**. Bracketing evidence: CypherBench's gpt-4o-mini reached 87.4%
*executable* but only **31.4% execution-accurate**; instruction-tuned 7-8B
baselines score 27.7-40.2%. A 24B lands around 60-85% executable and well under
40% semantically correct — and a query that runs and returns the wrong answer
is worse than one that errors, because nothing signals the failure.

It ships only with: grammar-constrained decoding to a read-only Cypher subset,
a schema-vocabulary post-validator, a read-only database role, and row/depth
caps. Note that **both reference implementations leave this work undone** —
LangChain's `GraphCypherQAChain` has no read-only enforcement, clause
allowlist, timeout or row cap and requires `allow_dangerous_requests=True`, and
Neo4j's own `Text2CypherRetriever` is prompt-only. That enforcement *is* the
build.

The grammar exists (`openCypher.bnf`) and production CFG-constrained decoders
exist (`xgrammar` is the default structured-output backend for vLLM, SGLang and
TensorRT-LLM; `outlines`, `guidance` and llama.cpp GBNF all support arbitrary
CFGs). A code search found **zero published Cypher grammar files** — nobody has
wired them together. Assembly work, not a research gap.

### Where the design fills a real gap

No surveyed framework combines enforced subject-area memory scoping with an
end-to-end typed principal. Namespaces in LangGraph's `BaseStore` and
Zep/Graphiti's `group_id` are **filters, not fences** — both explicitly
documented as unenforced, and mem0's and Graphiti's own docs concede ID-scoping
is not access control. Cognee comes closest with a real principal model but has
no Agent principal type. **No framework threads one typed principal through both
tool calls and memory calls**, which is why `ctx` in every signature stays
non-negotiable.

### An honest counterweight

One practitioner deliberately kept their always-on memory tier to **two small
curated files** rather than building a graph, and reports it working. That is
the "a maintained profile document might do" argument from someone actually
doing it, and it deserves weighing rather than burying.

### Coverage caveat

Anthropic's context-engineering post, Chroma's Context Rot report, Simon
Willison's archive and Zep's blog were named as seeds and **not reached**. The
catalog (Unity/Polaris/OpenMetadata) and ReBAC/OpenFGA findings were
search-synthesised rather than raw-fetched, so treat those as softer than the
rest.


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

## Operations: monitoring, security, install

These three are architectural concerns, not afterthoughts — each one changes
where a component belongs.

### Monitoring: alarms interrupt, trends need a chart

Monitoring is a **consumer**, not a layer. It reads through the same contract
everything else does, which is what stops it becoming another bypass.

What is worth watching here is not CPU or p99 latency. It is:

| Signal | Why it matters |
|---|---|
| **Residue rate** — extraction output that mapped to no predicate | The only staleness alarm the ontology has |
| **Rebuild diff** — incremental graph vs freshly rebuilt | The correctness oracle. Non-zero = a bug in the incremental path (or non-deterministic node ids) |
| **Extraction parse-failure rate** | Currently unmeasured; the foundation everything else rests on |
| **Gate false-positive / false-negative**, reported separately | A blended "accuracy" hides exactly the class of bug that shipped in ADR-007 |
| **Policy denials, with the `reason` field** | Catches "exceptions silently becoming policy" |
| **Verb latency by verb** | Tells you which of the five is hot and whether the graph is on the default path when it should not be |

**Delivery matters as much as collection.** This project's own history
(`project_dca_funding_outage_july_2026`) records the lesson: a dead-man's
switch catches "the process stopped", never "the process ran and correctly
refused" — that needs a leading indicator. The residue rate *is* that leading
indicator, and one nobody looks at is worthless. This system already has a
Telegram gateway; threshold breaches belong there, where the operator already
reads.

But a digest is the wrong instrument for the *primary* failure mode. **Silent
staleness is a trend**: a residue rate creeping from 3% to 11% over two months
is invisible in any single number and obvious in a chart. Drift is precisely
what a time series shows and a threshold does not, so visualisation is not a
nice-to-have here — it is the instrument matched to the failure being watched.

#### Tooling, sequenced

A visualisation tool stores nothing; it connects to backends through plugins.
So the question is never "should we run Grafana" but *what emits metrics and
where do they land*.

1. **An LLM-eval platform first — Langfuse or equivalent.** The eval is the
   gating problem for this whole document, and an eval platform is the tool
   that addresses it: datasets, scoring runs, prompt versioning, multi-turn
   traces, LLM-as-judge. Grafana does none of that natively — LLM-specific
   evaluation is handled through integrations, and the common pairing is an
   eval platform for model concerns plus Grafana for infrastructure. This is
   the tool on the critical path.

2. **Then Grafana against SQLite directly.** The interesting metrics —
   residue counts, extraction failures, gate outcomes, rebuild diffs — are
   already rows in a relational store. A SQLite datasource plugin means one
   container, no scrape config, no separate time-series database. That is
   sufficient at this scale and is where the drift chart should start.

3. **Defer the full collection stack.** Prometheus, Loki and Tempo are built
   for distributed systems with many services; this is one process. Prometheus
   now has experimental OTLP ingest, so OpenTelemetry remains the escape hatch
   if the architecture ever grows into multiple services — it is not the
   starting point.

Cost is worth stating plainly: an eval platform's production stack is typically
two containers, and Prometheus plus Grafana would be two more, on a machine
already running a document store and a large resident model. This ecosystem has
been bitten by unplanned always-on service growth before, so each addition
should be justified by a question it answers that nothing cheaper can.

### Security: the write path, not the read path

For a single-user local system the dominant risk is **not** who can read what.
It is that **a crafted message becomes a durable fact and then influences every
future turn** — memory poisoning, which Unit 42 documents as a structural
consequence of content arriving in the model's own voice.

That reframes the priorities:

- **The `extracts (write)` arrow is the attack surface.** The write-authority
  split is the mitigation: an extractor may write DERIVED, never CANONICAL, and
  promotion runs through a review gate. `InjectionGuard.sanitize_memory_write`
  already exists in this repo and is the right component in the right place.
- **The `CYPHER` verb is a query-injection surface.** Grammar constraint plus a
  read-only database role plus row/depth caps is the mitigation, and none of it
  comes free from the reference libraries.
- **MCP has no per-tool authorization concept** — verified against the full
  spec, not inferred. A third-party MCP server is therefore exactly as
  privileged as a native tool unless the control plane gates it. Custom plugins
  and MCP servers must pass the same enforcement point as everything else;
  there is no second door.
- **RBAC is already expressed** as write-authority tiers plus subject-area
  grants. It does not need a separate mechanism, and at this scale it does not
  need a policy engine (Cube ships inline YAML grants in production).
- **The projection is a security property, not only an ops one.** A graph that
  can be dropped and rebuilt from canonical sources means a corrupted or
  poisoned graph is *recoverable by deletion*. Compromise of a derived store is
  survivable in a way compromise of a system of record is not.
- **Local-only is doing heavy lifting.** No network exposure, no multi-tenancy,
  no credential distribution. The one credential surface is the read-only
  projection from the trading collections.

### Install and configuration: simpler because of the projection decision

The three-artifact split (interface as code, policy and ontology as declarative
files, all in git) means configuration is version-controlled and reviewable,
and the install reduces to:

```
clone  →  restore SQLite  →  compile ontology + policy  →  rebuild projection
```

**No graph backup, no graph migration, no dump/restore.** The container is
disposable by construction. That is a real operational simplification and it
follows directly from the projection decision rather than being an extra
feature.

Two constraints worth stating:

- **The compile step must be a command**, not a manual procedure — something
  like `semantic build`, runnable in CI and as a pre-flight check. An ontology
  that compiles only in someone's head is not in git.
- **Policy must load before anything serves.** This is the bootstrap argument
  made operational: startup order is policy → stores → consumers. OPA's own
  behaviour is the precedent — it caches its bundle to local disk and loads
  last-known-good even when the remote source is unreachable.

Docker cost is one more container beside the MongoDB already running on this
box; roughly 1-2 GB heap plus 1-2 GB pagecache is a reasonable starting budget
(inferred from general sizing guidance, not measured for this workload). The
ecosystem has been bitten before by unplanned always-on service growth, so the
disposability of the projection is what makes that acceptable rather than the
headroom.


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

---
title: Semantic platform (concept architecture)
status: Proposed
created: 2026-08-23
last_reviewed_on: 2026-08-23
review_in: 6 months
applies_to: nephilim
ai_summary: >
  Concept architecture for an agent/companion platform, written to settle where
  things belong before any technology is chosen. Open it when deciding which
  layer a new capability goes in - knowledge, policy, behaviour or config -
  when choosing a store, or when arguing about what to build now versus later.
  It carries the ten decisions judged irreversible (make them now) and, for
  every deferred piece, the trigger that would end the deferral. It records
  external research and the arguments AGAINST the design as well as for it,
  including where its own claims are currently unfalsifiable. Concept only:
  nothing here has been built, and it is not an implementation plan or an ADR.
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

#### Tooling: three things on day one, for three different reasons

A visualisation tool stores nothing; it connects to backends through plugins.
So the question is never "should we run a dashboard" but *what emits metrics
and where do they land*.

An earlier draft of this section sequenced these as "eval first, then a chart,
then defer the rest", which conflated two independent axes — **is it
irreversible?** and **is it on the critical path?** Something can be perfectly
reversible and still be the first thing to build. Corrected:

| | When | Because |
|---|---|---|
| **Metrics table + emitting** — timestamp, metric name, value, dimensions | **Day 1** | **Irreversible.** History cannot be generated retroactively for a metric that was never recorded, and the residue rate's whole value is as a trend |
| **An LLM-eval platform** (Langfuse or equivalent) | **Day 1** | **Critical path.** Everything downstream — flag flips, ontology slices, the graph decision — waits on being able to measure. Datasets, scoring runs, prompt versioning, multi-turn traces, LLM-as-judge; a general dashboard does none of this natively |
| **A dashboard against SQLite directly** | **Day 1** | **Someone will actually look.** The documented failure mode is that leading indicators get logged and ignored; a chart in front of the operator mitigates exactly that. One container, no scrape config, no separate time-series store |

Deferred means **"real cost and no consumer yet"** — not merely "reversible":

- **The full collection stack** (metrics scraping, log aggregation, tracing) is
  built for distributed systems with many services; this is one process.
  OTLP ingest into a scraping backend remains the escape hatch if the
  architecture ever grows that way — it is not the starting point.

Cost is worth stating plainly: an eval platform's production stack is typically
two containers, on a machine already running a document store and a large
resident model. This ecosystem has been bitten by unplanned always-on service
growth before, so each addition should answer a question nothing cheaper can.
These three do; a scraping stack does not, yet.

The metrics table is **not** part of the semantic layer. Telemetry is not facts
about the world — a time series of gate false-positives is not something a
persona should be able to `traverse` to. Separate table, separate lifecycle,
consumer-side.

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


## What the graph is, and is not, for

Most of the general agentic failure classes this design targets are addressed
by the **semantic layer** — the typed fact store, the contract, the
write-authority tiers, the assembly discipline. Only some are addressed by the
**graph**. Keeping that line clear matters, because a graph credited with wins
the fact store produced can never be evaluated on its own terms.

| Failure class | What addresses it | Graph-shaped? |
|---|---|---|
| Context rot — degradation with input volume | Just-in-time retrieval, smaller assembled prompts | **No** — an assembly discipline |
| Grounding and hallucination | `verify(claim)` against canonical facts | **No** — needs a typed fact store; a table suffices |
| Stale beliefs | Bi-temporal validity, supersede-not-delete | **No** — schema; `memory_facts` already carries it |
| Agent write safety | Write-authority tiers, provenance | **No** — schema and policy |
| **Multi-hop relational** — how a relationship stands now and how it changed | Traversal | **Yes** |
| **Disambiguation** — an alias resolving to one entity, deterministically | Alias edges | **Yes** |
| **Cross-session aggregation** | Graph queries | **Yes** |

The graph is load-bearing for the bottom three. It is not what delivers
context management or validation, and should not be judged on them.

**The reference class points the same way, and it is instructive.** The two
knowledge-graph teams whose postmortems inform this document did not abandon
*graphs* — they abandoned **ontology-first design**, after upfront schema work
froze them for months and lost information. Zep went the opposite direction
entirely and made the graph its authoritative store. The closest open-source
peer has no ontology layer at all. One practitioner replaced the whole
apparatus with two curated files and reports it working; a solo builder
independently converged on nearly this consolidation hierarchy.

So the documented failure mode is **ontology-phase, not graph-phase** — which
is precisely what a living ontology with human review in the loop is designed
to avoid.

**One consequence worth stating plainly.** The three capabilities above are
measurable; benefits that are expected but unnamed are not. An unnamed benefit
will be credited to the graph whether or not it occurred. The cheapest guard
is the query log: **the fraction of persona queries that traverse depth > 1**
is the direct measure of whether multi-hop — the primary stated purpose — is
real in this data rather than anticipated.


## Scale, and what is deliberately deferred

### The target

**A multi-project platform under one operator first; multi-user or shared
eventually.** Several distinct agent systems — companions, trading-aware
agents, future projects — binding to one semantic layer, with a second
operator or external consumers arriving later.

That target is a design input, not a forecast. Measuring current volume does
not settle it: fact extraction is flag-gated off, the lore wiki never reaches
inference, the trading subject area does not exist, and the second and third
consumers have not been built. Extrapolating from that measures the throttle,
not the demand.

**"Scalable" is not one design.** Scalable to tens of thousands of facts and
scalable to millions are different systems, and several decisions below flip
depending on which. What follows is calibrated to the target above.

### Decisions are not machinery

This is the discipline the whole document rests on, and the scale question is
where it earns its keep.

- **Make every irreversible decision now.** These cost design attention and
  almost no code, and they are painful-to-impossible to retrofit.
- **Build only what a working consumer needs.** Machinery built ahead of a
  consumer is what freezes projects — two independent knowledge-graph teams
  abandoned ontology-first designs after upfront schema work stalled them for
  months, and the data-mesh literature's transferable lesson is precisely
  *don't build the platform before one working consumer proves the pattern.*

A system that *can* scale is not the same as a system that *is* scaled. The
first is nearly free; the second is where projects die.

### The day-1 list, in two classes

Ten items. None is a subsystem — each is a shape decision, and all are
independent of current volume. But they are **not all irreversible**, and an
earlier draft of this document called them that uniformly. The distinction
matters, because it decides how much it costs to get one wrong:

**Truly irreversible — data you fail to record.** There is no later remedy;
the information simply does not exist.

- No hard-delete in the fact tier (destroyed data)
- Extraction-output table (output never persisted)
- Tombstone tier (retractions never recorded)
- Ontology- and extractor-version stamps (facts never stamped)
- Metrics table (history never captured)

**Expensive to retrofit — but possible.** These are refactors: painful,
sometimes very, never impossible.

- Owner/principal dimension · `ctx` threading · grant tuple shape · node
  identity scheme · interface version field

Both classes belong on day 1, for different reasons: the first because the
option disappears, the second because the cost only grows. **Neither class
includes the ontology**, which is a living artifact — versioned, extended and
deprecated as standard practice, with human review in the loop. Calling it
irreversible was a category error; slowest-changing is not the same as
unchangeable.

| # | Decision | Why it cannot wait |
|---|---|---|
| 1 | **Owner/principal dimension** in the data model | Retrofitting a tenant column into every fact, entity, grant and episode after real history exists is the worst migration in this design. One column now; it may hold a single value for years |
| 2 | **`ctx: CallerContext` in every verb signature** | Adding a first parameter across every call site later is expensive, and without it nothing can be enforced at the contract seam |
| 3 | **Grants as `(principal, verb, resource)` tuples** | Same information as a nested grants map, but this shape migrates to relationship-based access control as a backend swap rather than a remodel |
| 4 | **Deterministic, content-derived node identity** | Retrofit means re-keying everything that exists — and without it every rebuild diff reports spurious drift |
| 5 | **No hard-delete in the fact-bearing tier** | Data already destroyed cannot be recovered, and hard deletes invert the rebuild oracle |
| 6 | **Extraction-output table, distinct from raw input** | If extraction output was never persisted, a rebuild can never replay it — only re-run a non-deterministic model |
| 7 | **Tombstone tier** for retracted and rejected values | A retraction not recorded at the time is unrecoverable, and correction-propagation is where most memory systems fail |
| 8 | **Ontology-version and extractor-version stamps** per fact | Without them, a bad extraction batch cannot be identified, let alone invalidated |
| 9 | **Interface version field** | The field is free; committing to *support* old versions is the expensive part and waits for multi-user |
| 10 | **Metrics table, and emitting into it** | A trend cannot be reconstructed after the fact. The baseline that makes slow drift visible only exists if recording started early |

### Deferred, with the trigger that ends the deferral

Stating the trigger is what makes a deferral a decision rather than an
oversight — and what makes it falsifiable.

| Deferred | Build it when |
|---|---|
| *(none — graph store and the `CYPHER` plumbing moved to day 1; see below)* | |
| Policy engine (Rego or similar) | Real boolean composition, independently testable decisions, or a second enforcement process |
| Relationship-based access control | Hundreds of grant pairs, hierarchical inheritance, sub-10ms reverse queries, or set-algebraic exceptions |
| Tenancy *enforcement* | A second operator exists. The tenancy *dimension* ships now regardless |
| Interface support policy, docs, deprecation | External consumers exist |
| Blue-green projection cutover | Rebuilds must happen without a maintenance window |
| Full collection stack (metrics scraping, log aggregation, tracing) | The architecture grows into multiple processes |

### Graph store and `CYPHER`: day 1, with the agent-facing half flag-gated

An earlier draft deferred both until "traversals the relational store cannot
answer become routine." That reasoning was weak for the graph specifically:
**deferring the one component that is disposable by construction is backwards.**
A rebuildable projection costs almost nothing to have and nothing to remove,
and building it early means the extraction-output table, node identity and the
rebuild path are designed against a real target rather than a hypothetical one.

So the graph store ships day 1. Two consequences follow honestly:

- **It pulls the ontology forward.** A graph with no schema is a worse
  relational store. Day-1 graph implies at least the competency questions and
  a first predicate set.
- **It does not license skipping the eval.** Graph, ontology and projection
  together are a large surface, and the two prior attempts in this territory
  were reverted for want of a measurement. Adding a graph makes the next revert
  bigger, not smaller. These do not compete conceptually; they compete for
  attention.

`CYPHER` splits, because it is the one component with measured evidence against
it (frontier models around 60% execution accuracy; sub-10B never clearing 20%)
and, unlike the graph, a query cannot be un-run:

| Piece | Day 1 | Rationale |
|---|---|---|
| Gated runner — grammar constraint, schema filter, read-only role, row/depth caps | **Yes** | This is the actual build; both reference implementations leave this work undone |
| The operator using `CYPHER` to explore the graph by hand | **Yes** | No agent-facing risk, and it is how the schema gets learned on real data |
| **Measuring** valid-Cypher and execution-accuracy rate on *this* ontology and *this* model | **Yes** | Converts the open question into a number. This is the point of building it early |
| **An agent** composing queries autonomously | **Yes, live** | See the blast-radius argument below. Ships behind a kill-switch flag defaulting ON — a revert path, not a dark launch |

**Why live rather than dark.** An earlier draft gated the agent-facing verb
until a measured rate cleared a bar. That was over-cautious, because it never
analysed the blast radius properly. With the guards in place a bad query cannot
write (read-only role), cannot be malformed (grammar constraint), cannot flood
or hang (row and depth caps), and cannot reference things that do not exist
(schema-vocabulary validator). The residual risk is not safety but quality: a
valid-but-wrong query returns wrong facts and the persona repeats them. Blast
radius is **one bad reply** — nothing persists and nothing corrupts.

The comparison that matters is also not "wrong facts versus correct facts". It
is **wrong facts versus no facts and confabulation**, which is the current
behaviour. A query layer correct some of the time may beat that outright.

Four conditions make this defensible, and none is expensive:

- **The read-only database role is non-negotiable.** It is what bounds the
  blast radius to a bad reply rather than a corrupted graph; without it the
  argument above does not hold.
- **A kill-switch flag defaulting ON** — a revert path, not a dark launch.
- **Every query, its result, and the turn it served are logged.** When a reply
  is wrong, the question "was the query wrong?" must be answerable after the
  fact rather than requiring a separate harness.
- **Measure it anyway.** Going live removes the gate, not the need for the
  number. Without it there is no way to tell whether the graph is earning its
  place, which is the question this whole document rests on.


### What the target changes from earlier reasoning

Two recommendations in this document were calibrated to a single-user,
single-session system and no longer hold:

- **Concurrent-write locking is not over-built.** A sleep-time consolidator, a
  live agent and a projection writer running together is a genuine race. Keep
  it.
- **Subject-area modularity is load-bearing, not decorative.** It is the
  mechanism by which several agent systems stay out of each other's data.

And one boundary worth restating, because the target could appear to threaten
it: a trading-aware *agent* binding to the semantic layer is a **consumer** and
entirely fine. The trading *repositories* remain **sources** feeding a
read-only projection. The ecosystem's no-direct-imports invariant
([ADR-004](../decisions/004-persona-safe-agentic-tool-calls.md) and the root
CLAUDE.md) is intact, and only becomes a question if those repositories ever
start *reading from* the layer.

### The measurement that is still missing

The fact store holds a handful of rows because extraction is switched off, not
because the domain is small. **How many facts 1,275 existing messages actually
yield is the single most decision-relevant unknown in this document**, and it
costs one flag flip plus a backfill to find out. It determines whether a graph
ever has enough to traverse, and it is the same measurement that would begin to
falsify the ontology-first choice.


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

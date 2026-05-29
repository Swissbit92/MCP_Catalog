#!/usr/bin/env python3
"""
NEPHILIM Lore Wiki — typed-markdown-wiki engine.

Treats docs/lore/wiki/ as the canonical knowledge graph: one typed entity per
markdown file, with YAML frontmatter declaring entity_type, entity_id, aliases,
and typed relationships. Markdown stays the source of truth; a graph is derived
on demand (see the `graph` subcommand), never stored separately.

Usage:
    python scripts/utils/lore_wiki.py check        # validate the wiki (CI gate)
    python scripts/utils/lore_wiki.py index        # regenerate wiki/index.md
    python scripts/utils/lore_wiki.py graph        # export derived graph (stretch)

Examples:
    # Validate; exits non-zero if any ERROR-level finding
    python scripts/utils/lore_wiki.py check

    # Rebuild the auto-generated index
    python scripts/utils/lore_wiki.py index

Validation is tiered (mirrors the CMS linter): ERROR blocks, WARNING informs.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

# ── Paths ──────────────────────────────────────────────────────────────────
# scripts/utils/lore_wiki.py  ->  repo root is parents[2]
REPO_ROOT = Path(__file__).resolve().parents[2]
LORE_DIR = REPO_ROOT / "docs" / "lore"
WIKI_DIR = LORE_DIR / "wiki"
PERSONA_DIR = REPO_ROOT / "personas"

# Prose narrative docs (kept, not deleted) — scanned for name drift only.
PROSE_DOC_NAMES = [
    "NEPHILIM_LORE.md",
    "NEPHILIM_FACTIONS.md",
    "NEPHILIM_RANKS.md",
    "LORE_BIBLE_DRAFT.md",
    "THE_CHRONICLE.md",
]

ENTITY_TYPES = ("persona", "house", "rank", "location", "faction", "entity", "concept")
ENTITY_ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
WIKILINK_RE = re.compile(r"\[\[([a-z0-9-]+)\]\]")
# Targets the specific house-name drift problem deterministically, low FP rate.
HOUSE_NAME_RE = re.compile(r"\bHouse(?: of)?(?: the)? ([A-Z][A-Za-z]+)\b")
# Structural words that follow "House" in headings/prose but aren't house names.
HOUSE_STOPWORDS = {
    "assignment", "activities", "flexibility", "banners", "badges", "system",
    "dynamics", "identity", "comparison", "dossiers", "matter", "affiliation",
    "traits", "vaults", "comparison", "table", "dossier",
}

# Inverse relationship map for bidirectional-consistency checks.
INVERSE: Dict[str, str] = {
    "patron": "patron_of",
    "patron_of": "patron",
    "opposes": "opposed_by",
    "opposed_by": "opposes",
    "member_of": "has_member",
    "has_member": "member_of",
    "located_in": "contains",
    "contains": "located_in",
    "ally_of": "ally_of",        # symmetric
    "rival_of": "rival_of",      # symmetric
    "related_to": "related_to",  # symmetric
}


# ── Schema ─────────────────────────────────────────────────────────────────
class Relationship(BaseModel):
    model_config = ConfigDict(extra="ignore")
    type: str
    target: str


class LoreEntity(BaseModel):
    """Entity frontmatter schema (extends the CMS base fields, which are ignored
    here and validated separately by `/cms check`)."""

    model_config = ConfigDict(extra="ignore")

    # CMS base (validated by CMS; declared so they don't trip extra handling)
    title: str
    status: str = "active"

    # Entity-specific
    entity_type: str
    entity_id: str
    canon: bool = True
    aliases: List[str] = []
    relationships: List[Relationship] = []

    @field_validator("entity_type")
    @classmethod
    def _valid_type(cls, v: str) -> str:
        if v not in ENTITY_TYPES:
            raise ValueError(f"entity_type must be one of {ENTITY_TYPES}, got '{v}'")
        return v

    @field_validator("entity_id")
    @classmethod
    def _valid_id(cls, v: str) -> str:
        if not ENTITY_ID_RE.match(v):
            raise ValueError(f"entity_id must be kebab-case [a-z0-9-], got '{v}'")
        return v

    @field_validator("status")
    @classmethod
    def _valid_status(cls, v: str) -> str:
        allowed = ("active", "archived", "Accepted", "Proposed", "Deprecated", "Superseded", "completed", "deprecated")
        if v not in allowed:
            raise ValueError(f"status must be one of {allowed}, got '{v}'")
        return v


# ── Findings ───────────────────────────────────────────────────────────────
ERROR, WARNING, INFO = "ERROR", "WARNING", "INFO"


@dataclass
class Finding:
    level: str
    where: str
    message: str


@dataclass
class ParsedEntity:
    entity: LoreEntity
    path: Path
    body: str


# ── Frontmatter parsing ────────────────────────────────────────────────────
def split_frontmatter(text: str) -> Tuple[Optional[dict], str]:
    """Return (frontmatter_dict, body). frontmatter is None if absent/malformed."""
    if not text.startswith("---"):
        return None, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, text
    try:
        fm = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None, text
    if not isinstance(fm, dict):
        return None, text
    return fm, parts[2]


def load_entities(wiki_dir: Path) -> Tuple[List[ParsedEntity], List[Finding]]:
    """Parse + schema-validate every .md under wiki_dir (excluding index.md)."""
    findings: List[Finding] = []
    parsed: List[ParsedEntity] = []
    if not wiki_dir.exists():
        findings.append(Finding(ERROR, str(wiki_dir), "wiki directory does not exist"))
        return parsed, findings

    for md in sorted(wiki_dir.rglob("*.md")):
        if md.name == "index.md":
            continue
        rel = md.relative_to(wiki_dir)
        text = md.read_text(encoding="utf-8")
        fm, body = split_frontmatter(text)
        if fm is None:
            findings.append(Finding(ERROR, str(rel), "missing or malformed YAML frontmatter"))
            continue
        try:
            entity = LoreEntity(**fm)
        except ValidationError as exc:
            for err in exc.errors():
                loc = ".".join(str(p) for p in err["loc"])
                findings.append(Finding(ERROR, str(rel), f"{loc}: {err['msg']}"))
            continue
        parsed.append(ParsedEntity(entity=entity, path=md, body=body))
    return parsed, findings


# ── Validation ─────────────────────────────────────────────────────────────
def check_wiki(wiki_dir: Path = WIKI_DIR, persona_dir: Path = PERSONA_DIR,
               lore_dir: Path = LORE_DIR) -> List[Finding]:
    parsed, findings = load_entities(wiki_dir)
    by_id: Dict[str, ParsedEntity] = {}

    # entity_id uniqueness
    for pe in parsed:
        eid = pe.entity.entity_id
        if eid in by_id:
            findings.append(Finding(ERROR, str(pe.path.relative_to(wiki_dir)),
                                    f"duplicate entity_id '{eid}'"))
        else:
            by_id[eid] = pe

    known_ids = set(by_id)

    # alias collisions + alias/title clashes
    name_owner: Dict[str, str] = {}
    for pe in parsed:
        names = [pe.entity.title] + list(pe.entity.aliases)
        for n in names:
            key = n.strip().lower()
            if key in name_owner and name_owner[key] != pe.entity.entity_id:
                findings.append(Finding(ERROR, pe.entity.entity_id,
                                        f"name/alias '{n}' also used by '{name_owner[key]}'"))
            else:
                name_owner[key] = pe.entity.entity_id

    # relationship integrity + bidirectional consistency + orphan detection
    has_link: Dict[str, bool] = {eid: False for eid in known_ids}
    rel_set: Dict[str, set] = {eid: set() for eid in known_ids}
    for pe in parsed:
        eid = pe.entity.entity_id
        for rel in pe.entity.relationships:
            rel_set[eid].add((rel.type, rel.target))
            if rel.target not in known_ids:
                findings.append(Finding(ERROR, eid,
                                        f"relationship target '{rel.target}' "
                                        f"({rel.type}) does not resolve to any entity"))
                continue
            has_link[eid] = True
            has_link[rel.target] = True

    # body wikilinks must resolve too
    for pe in parsed:
        for target in WIKILINK_RE.findall(pe.body):
            if target not in known_ids:
                findings.append(Finding(WARNING, pe.entity.entity_id,
                                        f"body wikilink [[{target}]] does not resolve"))

    # missing inverse -> Warning
    for pe in parsed:
        eid = pe.entity.entity_id
        for rel in pe.entity.relationships:
            if rel.target not in known_ids:
                continue
            inv = INVERSE.get(rel.type)
            if inv is None:
                continue
            if (inv, eid) not in rel_set.get(rel.target, set()):
                findings.append(Finding(WARNING, rel.target,
                                        f"missing inverse '{inv}' -> '{eid}' "
                                        f"(for '{eid}' {rel.type} '{rel.target}')"))

    # orphan detection -> Warning (canon entities only; draft/expansion entities
    # are intentionally not yet woven into the graph)
    for eid, linked in has_link.items():
        if not linked and by_id[eid].entity.canon:
            findings.append(Finding(WARNING, eid, "orphan entity (no inbound/outbound relationships)"))

    # persona-JSON <-> wiki consistency
    findings += _check_persona_consistency(by_id, persona_dir)

    # name drift in prose docs -> Warning
    findings += _check_name_drift(name_owner, lore_dir)

    return findings


def _check_persona_consistency(by_id: Dict[str, ParsedEntity], persona_dir: Path) -> List[Finding]:
    findings: List[Finding] = []
    if not persona_dir.exists():
        return findings
    json_keys = sorted(
        p.stem for p in persona_dir.glob("nephilim_*.json")
    )
    canon_personas = {
        eid for eid, pe in by_id.items()
        if pe.entity.entity_type == "persona" and pe.entity.canon
    }
    for key in json_keys:
        # nephilim_eeva -> persona-eeva
        short = key.replace("nephilim_", "")
        expected = f"persona-{short}"
        if expected not in canon_personas:
            findings.append(Finding(ERROR, expected,
                                    f"persona JSON '{key}.json' has no matching "
                                    f"canon persona entity '{expected}'"))
    json_shorts = {k.replace("nephilim_", "") for k in json_keys}
    for eid in canon_personas:
        short = eid.replace("persona-", "")
        if short not in json_shorts:
            findings.append(Finding(WARNING, eid,
                                    "canon persona entity has no matching persona JSON"))
    return findings


def _check_name_drift(name_owner: Dict[str, str], lore_dir: Path) -> List[Finding]:
    """Flag 'House X' proper nouns in prose docs not registered as a name/alias."""
    findings: List[Finding] = []
    for name in PROSE_DOC_NAMES:
        doc = lore_dir / name
        if not doc.exists():
            continue
        text = doc.read_text(encoding="utf-8")
        seen: set = set()
        for m in HOUSE_NAME_RE.finditer(text):
            full = m.group(0).strip()
            trailing = m.group(1).lower()
            key = full.lower()
            if key in seen or trailing in HOUSE_STOPWORDS:
                continue
            seen.add(key)
            if key not in name_owner:
                findings.append(Finding(WARNING, name,
                                        f"house name '{full}' not registered in wiki "
                                        f"(canonical or alias) — possible drift"))
    return findings


# ── Index generation ───────────────────────────────────────────────────────
def build_index(wiki_dir: Path = WIKI_DIR) -> str:
    parsed, _ = load_entities(wiki_dir)
    groups: Dict[str, List[LoreEntity]] = {t: [] for t in ENTITY_TYPES}
    for pe in parsed:
        groups.setdefault(pe.entity.entity_type, []).append(pe.entity)

    lines = [
        "---",
        "title: Lore Wiki Index",
        "status: active",
        "created: 2026-05-29",
        "last_reviewed_on: 2026-05-29",
        "review_in: 12 months",
        "applies_to: nephilim",
        "---",
        "",
        "# NEPHILIM Lore Wiki — Index",
        "",
        "> AUTO-GENERATED by `scripts/utils/lore_wiki.py index`. Do not edit by hand.",
        "",
        f"Total entities: {len(parsed)}",
        "",
    ]
    for etype in ENTITY_TYPES:
        items = sorted(groups.get(etype, []), key=lambda e: e.entity_id)
        if not items:
            continue
        lines.append(f"## {etype.capitalize()} ({len(items)})")
        lines.append("")
        for e in items:
            flag = "" if e.canon else " _(draft)_"
            alias = f" — aka {', '.join(e.aliases)}" if e.aliases else ""
            lines.append(f"- `{e.entity_id}` — {e.title}{flag}{alias}")
        lines.append("")
    return "\n".join(lines)


def build_graph(wiki_dir: Path = WIKI_DIR) -> dict:
    parsed, _ = load_entities(wiki_dir)
    nodes = [{"id": pe.entity.entity_id, "type": pe.entity.entity_type,
              "title": pe.entity.title, "canon": pe.entity.canon} for pe in parsed]
    edges = [{"source": pe.entity.entity_id, "type": rel.type, "target": rel.target}
             for pe in parsed for rel in pe.entity.relationships]
    return {"nodes": nodes, "edges": edges}


# ── CLI ────────────────────────────────────────────────────────────────────
def _print_findings(findings: List[Finding]) -> int:
    errors = [f for f in findings if f.level == ERROR]
    warnings = [f for f in findings if f.level == WARNING]
    for f in findings:
        print(f"[{f.level:7}] {f.where}: {f.message}")
    print(f"\nSummary: {len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check", help="validate the wiki (CI gate)")
    sub.add_parser("index", help="regenerate wiki/index.md")
    sub.add_parser("graph", help="export derived graph as JSON to stdout")
    args = parser.parse_args()

    if args.command == "check":
        return _print_findings(check_wiki())

    if args.command == "index":
        content = build_index()
        out = WIKI_DIR / "index.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content + "\n", encoding="utf-8")
        print(f"Wrote {out.relative_to(REPO_ROOT)}")
        return 0

    if args.command == "graph":
        print(json.dumps(build_graph(), indent=2))
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Unit tests for the lore-wiki engine (scripts/utils/lore_wiki.py).

Tests operate on synthetic fixture entities in tmp_path, never the real lore
content, so they stay stable as the lore evolves.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.utils.lore_wiki import (
    ERROR,
    WARNING,
    build_index,
    check_wiki,
    load_entities,
    split_frontmatter,
)

pytestmark = pytest.mark.unit


# ── helpers ──────────────────────────────────────────────────────────────
def write_entity(wiki_dir: Path, subdir: str, fm: dict, body: str = "") -> Path:
    d = wiki_dir / subdir
    d.mkdir(parents=True, exist_ok=True)
    text = "---\n" + yaml.safe_dump(fm, sort_keys=False) + "---\n" + body
    path = d / f"{fm['entity_id']}.md"
    path.write_text(text, encoding="utf-8")
    return path


def levels(findings, level):
    return [f for f in findings if f.level == level]


def messages(findings):
    return " | ".join(f.message for f in findings)


@pytest.fixture
def empty_dirs(tmp_path):
    """Return (wiki_dir, persona_dir, lore_dir) all empty/created."""
    wiki = tmp_path / "wiki"
    personas = tmp_path / "personas"
    lore = tmp_path / "lore"
    for d in (wiki, personas, lore):
        d.mkdir(parents=True, exist_ok=True)
    return wiki, personas, lore


# ── split_frontmatter ────────────────────────────────────────────────────
class TestSplitFrontmatter:
    def test_valid(self):
        fm, body = split_frontmatter("---\ntitle: X\n---\nhello")
        assert fm == {"title": "X"}
        assert "hello" in body

    def test_absent(self):
        fm, body = split_frontmatter("no frontmatter here")
        assert fm is None

    def test_malformed_yaml(self):
        fm, _ = split_frontmatter("---\n: : bad\n  - x\n---\nbody")
        assert fm is None


# ── load_entities / schema ───────────────────────────────────────────────
class TestLoadEntities:
    def test_valid_entity_parses(self, empty_dirs):
        wiki, _, _ = empty_dirs
        write_entity(wiki, "personas", {
            "title": "E.E.V.A.", "entity_type": "persona", "entity_id": "persona-eeva",
        })
        parsed, findings = load_entities(wiki)
        assert len(parsed) == 1
        assert not levels(findings, ERROR)

    def test_missing_frontmatter_errors(self, empty_dirs):
        wiki, _, _ = empty_dirs
        (wiki / "personas").mkdir(parents=True)
        (wiki / "personas" / "broken.md").write_text("no frontmatter", encoding="utf-8")
        parsed, findings = load_entities(wiki)
        assert levels(findings, ERROR)

    def test_invalid_entity_type_errors(self, empty_dirs):
        wiki, _, _ = empty_dirs
        write_entity(wiki, "x", {
            "title": "Bad", "entity_type": "bogus", "entity_id": "bad-1",
        })
        _, findings = load_entities(wiki)
        assert levels(findings, ERROR)

    def test_bad_entity_id_errors(self, empty_dirs):
        wiki, _, _ = empty_dirs
        write_entity(wiki, "x", {
            "title": "Bad", "entity_type": "concept", "entity_id": "Bad_ID",
        })
        _, findings = load_entities(wiki)
        assert levels(findings, ERROR)

    def test_index_md_skipped(self, empty_dirs):
        wiki, _, _ = empty_dirs
        (wiki / "index.md").write_text("---\ntitle: idx\n---\n", encoding="utf-8")
        parsed, findings = load_entities(wiki)
        assert parsed == []
        assert not levels(findings, ERROR)


# ── check_wiki ───────────────────────────────────────────────────────────
class TestCheckWiki:
    def _pair(self, wiki):
        """A mutually-linked, inverse-consistent, non-orphan pair."""
        write_entity(wiki, "personas", {
            "title": "E.E.V.A.", "entity_type": "persona", "entity_id": "persona-eeva",
            "relationships": [{"type": "patron_of", "target": "house-crown"}],
        }, body="See [[house-crown]].")
        write_entity(wiki, "houses", {
            "title": "House of the Crown", "entity_type": "house", "entity_id": "house-crown",
            "relationships": [{"type": "patron", "target": "persona-eeva"}],
        })

    def test_clean_wiki_no_errors(self, empty_dirs):
        wiki, personas, lore = empty_dirs
        self._pair(wiki)
        (personas / "nephilim_eeva.json").write_text("{}", encoding="utf-8")
        findings = check_wiki(wiki, personas, lore)
        assert not levels(findings, ERROR), messages(findings)

    def test_dangling_target_errors(self, empty_dirs):
        wiki, personas, lore = empty_dirs
        write_entity(wiki, "personas", {
            "title": "E.E.V.A.", "entity_type": "persona", "entity_id": "persona-eeva",
            "relationships": [{"type": "patron_of", "target": "house-ghost"}],
        })
        findings = check_wiki(wiki, personas, lore)
        assert any("does not resolve" in f.message for f in levels(findings, ERROR))

    def test_duplicate_id_errors(self, empty_dirs):
        wiki, personas, lore = empty_dirs
        write_entity(wiki, "a", {
            "title": "One", "entity_type": "concept", "entity_id": "dup-x",
        })
        write_entity(wiki, "b", {
            "title": "Two", "entity_type": "concept", "entity_id": "dup-x",
        })
        findings = check_wiki(wiki, personas, lore)
        assert any("duplicate entity_id" in f.message for f in levels(findings, ERROR))

    def test_alias_collision_errors(self, empty_dirs):
        wiki, personas, lore = empty_dirs
        write_entity(wiki, "a", {
            "title": "Alpha", "entity_type": "concept", "entity_id": "alpha",
            "aliases": ["Shared Name"],
        })
        write_entity(wiki, "b", {
            "title": "Beta", "entity_type": "concept", "entity_id": "beta",
            "aliases": ["Shared Name"],
        })
        findings = check_wiki(wiki, personas, lore)
        assert any("also used by" in f.message for f in levels(findings, ERROR))

    def test_missing_inverse_warns(self, empty_dirs):
        wiki, personas, lore = empty_dirs
        write_entity(wiki, "personas", {
            "title": "E.E.V.A.", "entity_type": "persona", "entity_id": "persona-eeva",
            "relationships": [{"type": "patron_of", "target": "house-crown"}],
        })
        write_entity(wiki, "houses", {
            "title": "House of the Crown", "entity_type": "house", "entity_id": "house-crown",
        })  # no inverse 'patron' back to eeva
        findings = check_wiki(wiki, personas, lore)
        assert any("missing inverse" in f.message for f in levels(findings, WARNING))

    def test_orphan_warns(self, empty_dirs):
        wiki, personas, lore = empty_dirs
        write_entity(wiki, "concepts", {
            "title": "Lonely", "entity_type": "concept", "entity_id": "lonely",
        })
        findings = check_wiki(wiki, personas, lore)
        assert any("orphan" in f.message for f in levels(findings, WARNING))

    def test_persona_json_without_entity_errors(self, empty_dirs):
        wiki, personas, lore = empty_dirs
        self._pair(wiki)
        (personas / "nephilim_eeva.json").write_text("{}", encoding="utf-8")
        (personas / "nephilim_nyx.json").write_text("{}", encoding="utf-8")  # no persona-nyx
        findings = check_wiki(wiki, personas, lore)
        assert any("persona-nyx" in f.message for f in levels(findings, ERROR))

    def test_unresolved_wikilink_warns(self, empty_dirs):
        wiki, personas, lore = empty_dirs
        self._pair(wiki)
        write_entity(wiki, "concepts", {
            "title": "Note", "entity_type": "concept", "entity_id": "note",
            "relationships": [{"type": "related_to", "target": "persona-eeva"}],
        }, body="Points at [[ghost-entity]].")
        (personas / "nephilim_eeva.json").write_text("{}", encoding="utf-8")
        findings = check_wiki(wiki, personas, lore)
        assert any("[[ghost-entity]]" in f.message for f in levels(findings, WARNING))

    def test_name_drift_in_prose_warns(self, empty_dirs):
        wiki, personas, lore = empty_dirs
        self._pair(wiki)  # registers "House of the Crown"
        (personas / "nephilim_eeva.json").write_text("{}", encoding="utf-8")
        (lore / "NEPHILIM_FACTIONS.md").write_text(
            "House Lumina is the patron house.", encoding="utf-8"
        )
        findings = check_wiki(wiki, personas, lore)
        assert any("House Lumina" in f.message for f in levels(findings, WARNING))


# ── build_index ──────────────────────────────────────────────────────────
class TestBuildIndex:
    def test_lists_entities_and_marks_draft(self, empty_dirs):
        wiki, _, _ = empty_dirs
        write_entity(wiki, "personas", {
            "title": "E.E.V.A.", "entity_type": "persona", "entity_id": "persona-eeva",
        })
        write_entity(wiki, "entities", {
            "title": "Anamnesis", "entity_type": "entity", "entity_id": "entity-anamnesis",
            "status": "active", "canon": False,
        })
        out = build_index(wiki)
        assert "persona-eeva" in out
        assert "entity-anamnesis" in out
        assert "_(draft)_" in out

    def test_deterministic(self, empty_dirs):
        wiki, _, _ = empty_dirs
        write_entity(wiki, "personas", {
            "title": "E.E.V.A.", "entity_type": "persona", "entity_id": "persona-eeva",
        })
        assert build_index(wiki) == build_index(wiki)

    def test_shows_aliases(self, empty_dirs):
        wiki, _, _ = empty_dirs
        write_entity(wiki, "houses", {
            "title": "House of the Crown", "entity_type": "house", "entity_id": "house-crown",
            "aliases": ["House Lumina"],
        })
        assert "House Lumina" in build_index(wiki)

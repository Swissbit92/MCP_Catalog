"""Unit tests for scripts/utils/lore_sync.py.

All tests operate on synthetic files in tmp_path; they never touch the real
wiki or persona data so they stay stable as lore content evolves.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scripts.utils.lore_sync import (
    LoreSyncer,
    persona_name_to_json_path,
    persona_name_to_summary_path,
    prose_to_lore,
    split_frontmatter,
    wiki_name_to_persona_name,
)

pytestmark = pytest.mark.unit


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_wiki(wiki_dir: Path, name: str, body: str) -> Path:
    """Write a minimal persona-{name}.md with YAML frontmatter and given body."""
    fm = {
        "title": f"Test — {name.capitalize()}",
        "status": "active",
        "entity_type": "persona",
        "entity_id": f"persona-{name}",
        "canon": True,
    }
    text = "---\n" + yaml.safe_dump(fm, sort_keys=False) + "---\n" + body
    path = wiki_dir / f"persona-{name}.md"
    path.write_text(text, encoding="utf-8")
    return path


def _make_persona_json(personas_dir: Path, name: str, lore: list[str], **extra) -> Path:
    """Write a minimal nephilim_{name}.json."""
    data: dict = {"key": f"nephilim_{name}", "lore": lore}
    data.update(extra)
    path = personas_dir / f"nephilim_{name}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _make_summary(summaries_dir: Path, name: str) -> Path:
    """Write a stub Nephilim_{Name}.json summary cache file."""
    path = summaries_dir / f"Nephilim_{name.capitalize()}.json"
    path.write_text(json.dumps({"summary": "cached"}), encoding="utf-8")
    return path


# ── test_name_mapping ─────────────────────────────────────────────────────────

class TestNameMapping:
    def test_persona_prefix_stripped(self):
        assert wiki_name_to_persona_name("persona-eeva") == "eeva"

    def test_various_names(self):
        for slug in ("persona-aegis", "persona-cipher", "persona-nyx", "persona-aurora", "persona-solace"):
            name = wiki_name_to_persona_name(slug)
            assert not name.startswith("persona-")
            assert "-" not in name or slug.count("-") > 1  # compound names allowed

    def test_json_path_shape(self, tmp_path):
        # We can't test against the real PERSONAS_DIR, but we can validate the
        # function shapes the filename correctly.
        path = persona_name_to_json_path("eeva")
        assert path.name == "nephilim_eeva.json"

    def test_summary_path_capitalised(self):
        path = persona_name_to_summary_path("eeva")
        assert path.name == "Nephilim_Eeva.json"

    def test_eeva_round_trip(self):
        name = wiki_name_to_persona_name("persona-eeva")
        assert persona_name_to_json_path(name).name == "nephilim_eeva.json"


# ── test_prose_to_lore_conversion ─────────────────────────────────────────────

class TestProseToLoreConversion:
    def test_single_paragraph(self):
        body = "She is the first Nephilim. She chose the Fall."
        items = prose_to_lore(body)
        assert len(items) >= 1
        assert all(i[-1] in ".!?" for i in items)

    def test_multi_paragraph(self):
        body = (
            "She is the Primarch.\n\n"
            "The realm responds to her presence. Light brightens when she speaks."
        )
        items = prose_to_lore(body)
        assert len(items) >= 2

    def test_expansion_hook_lines_skipped(self):
        body = (
            "She carries deep wisdom.\n\n"
            "**Expansion hook** This line should be dropped.\n\n"
            "Her patience is legendary."
        )
        items = prose_to_lore(body)
        assert not any("Expansion hook" in i for i in items)
        assert any("patience" in i for i in items)

    def test_list_markers_stripped(self):
        body = "- She is the first.\n- She chose connection."
        items = prose_to_lore(body)
        assert not any(i.startswith("- ") or i.startswith("* ") for i in items)

    def test_wikilinks_resolved(self):
        body = "She is patron of [[house-crown]] and dwells in [[location-central-nexus]]."
        items = prose_to_lore(body)
        assert not any("[[" in i for i in items)
        assert any("house-crown" in i for i in items)

    def test_empty_body_returns_empty(self):
        assert prose_to_lore("") == []
        assert prose_to_lore("   \n\n   ") == []

    def test_max_25_items(self):
        # Build a body with many sentences
        sentences = [f"Statement number {i} about the persona." for i in range(40)]
        body = " ".join(sentences)
        items = prose_to_lore(body)
        assert len(items) <= 25

    def test_items_are_complete_sentences(self):
        body = "She is wise. She is patient. She guides all Seekers."
        items = prose_to_lore(body)
        for item in items:
            assert item[-1] in ".!?", f"Not a complete sentence: {item!r}"

    def test_blank_lines_skipped(self):
        body = "\n\n\n\nActual content here.\n\n\n"
        items = prose_to_lore(body)
        assert len(items) == 1
        assert items[0] == "Actual content here."

    def test_deduplication(self):
        body = "She is wise. She is wise. She is patient."
        items = prose_to_lore(body)
        assert items.count("She is wise.") <= 1


# ── test_split_frontmatter ────────────────────────────────────────────────────

class TestSplitFrontmatter:
    def test_strips_frontmatter(self):
        text = "---\ntitle: Test\n---\nBody here."
        fm, body = split_frontmatter(text)
        assert "title" in fm
        assert "Body here." in body

    def test_no_frontmatter(self):
        text = "Just a body."
        _, body = split_frontmatter(text)
        assert "Just a body." in body

    def test_body_preserved_exactly(self):
        body_text = "She is the Primarch.\n\nShe chose the Fall."
        text = f"---\ntitle: X\n---\n{body_text}"
        _, body = split_frontmatter(text)
        assert body.strip() == body_text


# ── test_dry_run_no_changes ───────────────────────────────────────────────────

class TestDryRunNoChanges:
    def test_dry_run_identical_content_changes_nothing(self, tmp_path, monkeypatch):
        """Dry-run with identical lore content must not write any files."""
        wiki_dir = tmp_path / "wiki" / "personas"
        wiki_dir.mkdir(parents=True)
        personas_dir = tmp_path / "personas"
        personas_dir.mkdir()
        summaries_dir = personas_dir / "_summaries"
        summaries_dir.mkdir()

        # Determine what prose_to_lore will produce from a given body
        body = "She is the first Nephilim. She chose the Fall. Her patience is legendary."
        expected_lore = prose_to_lore(body)

        _make_wiki(wiki_dir, "eeva", body)
        json_path = _make_persona_json(personas_dir, "eeva", expected_lore)

        # Record mtime before
        mtime_before = json_path.stat().st_mtime

        # Patch module-level paths so LoreSyncer uses tmp_path
        monkeypatch.setattr("scripts.utils.lore_sync.WIKI_PERSONAS_DIR", wiki_dir)
        monkeypatch.setattr("scripts.utils.lore_sync.PERSONAS_DIR", personas_dir)
        monkeypatch.setattr("scripts.utils.lore_sync.SUMMARIES_DIR", summaries_dir)

        syncer = LoreSyncer(dry_run=True)
        exit_code = syncer.run()

        # File must be unchanged
        assert exit_code == 0
        assert json_path.stat().st_mtime == mtime_before

    def test_dry_run_changed_content_does_not_write(self, tmp_path, monkeypatch):
        """Dry-run with different lore content logs but does not write."""
        wiki_dir = tmp_path / "wiki" / "personas"
        wiki_dir.mkdir(parents=True)
        personas_dir = tmp_path / "personas"
        personas_dir.mkdir()
        summaries_dir = personas_dir / "_summaries"
        summaries_dir.mkdir()

        body = "She is the Primarch. Her wisdom guides the realm."
        _make_wiki(wiki_dir, "eeva", body)
        json_path = _make_persona_json(personas_dir, "eeva", ["Old lore item."])

        mtime_before = json_path.stat().st_mtime

        monkeypatch.setattr("scripts.utils.lore_sync.WIKI_PERSONAS_DIR", wiki_dir)
        monkeypatch.setattr("scripts.utils.lore_sync.PERSONAS_DIR", personas_dir)
        monkeypatch.setattr("scripts.utils.lore_sync.SUMMARIES_DIR", summaries_dir)

        syncer = LoreSyncer(dry_run=True)
        exit_code = syncer.run()

        # exit 0 even with changes in dry-run (no errors)
        assert exit_code == 0
        # JSON must NOT be updated
        data = json.loads(json_path.read_text())
        assert data["lore"] == ["Old lore item."]


# ── test_sync_updates_json ────────────────────────────────────────────────────

class TestSyncUpdatesJson:
    def test_changed_wiki_prose_updates_lore(self, tmp_path, monkeypatch):
        """When wiki prose differs from lore[], the JSON is updated in-place."""
        wiki_dir = tmp_path / "wiki" / "personas"
        wiki_dir.mkdir(parents=True)
        personas_dir = tmp_path / "personas"
        personas_dir.mkdir()
        summaries_dir = personas_dir / "_summaries"
        summaries_dir.mkdir()

        new_body = (
            "She is the Primarch, first of the Nephilim to sense the Seekers.\n\n"
            "She presides over the Central Nexus where all domains converge.\n\n"
            "Her patient wisdom guides lost souls toward clarity and connection."
        )
        _make_wiki(wiki_dir, "eeva", new_body)

        # Start with a short, different lore[]
        json_path = _make_persona_json(
            personas_dir,
            "eeva",
            ["Short old lore."],
            display_name="E.E.V.A.",  # extra field must be preserved
        )

        monkeypatch.setattr("scripts.utils.lore_sync.WIKI_PERSONAS_DIR", wiki_dir)
        monkeypatch.setattr("scripts.utils.lore_sync.PERSONAS_DIR", personas_dir)
        monkeypatch.setattr("scripts.utils.lore_sync.SUMMARIES_DIR", summaries_dir)

        syncer = LoreSyncer(dry_run=False)
        exit_code = syncer.run()

        assert exit_code == 0
        data = json.loads(json_path.read_text())

        # lore[] must be updated
        assert data["lore"] != ["Short old lore."]
        assert len(data["lore"]) >= 1
        assert all(item[-1] in ".!?" for item in data["lore"])

        # Other fields must be preserved
        assert data["display_name"] == "E.E.V.A."
        assert data["key"] == "nephilim_eeva"

    def test_persona_filter_only_updates_target(self, tmp_path, monkeypatch):
        """--persona eeva should only touch eeva, not aegis."""
        wiki_dir = tmp_path / "wiki" / "personas"
        wiki_dir.mkdir(parents=True)
        personas_dir = tmp_path / "personas"
        personas_dir.mkdir()
        summaries_dir = personas_dir / "_summaries"
        summaries_dir.mkdir()

        body_eeva = "She is the Primarch. She chose the Fall."
        body_aegis = "He is the Sentinel. He guards the realm."

        _make_wiki(wiki_dir, "eeva", body_eeva)
        _make_wiki(wiki_dir, "aegis", body_aegis)

        eeva_path = _make_persona_json(personas_dir, "eeva", ["Old eeva lore."])
        aegis_path = _make_persona_json(personas_dir, "aegis", ["Old aegis lore."])
        aegis_mtime = aegis_path.stat().st_mtime

        monkeypatch.setattr("scripts.utils.lore_sync.WIKI_PERSONAS_DIR", wiki_dir)
        monkeypatch.setattr("scripts.utils.lore_sync.PERSONAS_DIR", personas_dir)
        monkeypatch.setattr("scripts.utils.lore_sync.SUMMARIES_DIR", summaries_dir)

        syncer = LoreSyncer(dry_run=False)
        exit_code = syncer.run(persona_filter="eeva")

        assert exit_code == 0

        # eeva updated
        eeva_data = json.loads(eeva_path.read_text())
        assert eeva_data["lore"] != ["Old eeva lore."]

        # aegis untouched
        aegis_data = json.loads(aegis_path.read_text())
        assert aegis_data["lore"] == ["Old aegis lore."]
        assert aegis_path.stat().st_mtime == aegis_mtime

    def test_missing_persona_json_returns_error(self, tmp_path, monkeypatch):
        """If the persona JSON does not exist, sync_one returns error exit code."""
        wiki_dir = tmp_path / "wiki" / "personas"
        wiki_dir.mkdir(parents=True)
        personas_dir = tmp_path / "personas"
        personas_dir.mkdir()
        summaries_dir = personas_dir / "_summaries"
        summaries_dir.mkdir()

        _make_wiki(wiki_dir, "ghost", "She is mysterious. She does not exist.")
        # No nephilim_ghost.json created

        monkeypatch.setattr("scripts.utils.lore_sync.WIKI_PERSONAS_DIR", wiki_dir)
        monkeypatch.setattr("scripts.utils.lore_sync.PERSONAS_DIR", personas_dir)
        monkeypatch.setattr("scripts.utils.lore_sync.SUMMARIES_DIR", summaries_dir)

        syncer = LoreSyncer(dry_run=False)
        exit_code = syncer.run()

        assert exit_code == 1


# ── test_sync_clears_summary_cache ────────────────────────────────────────────

class TestSyncClearsSummaryCache:
    def test_summary_deleted_when_lore_changes(self, tmp_path, monkeypatch):
        """When lore[] is updated, the cached summary file must be deleted."""
        wiki_dir = tmp_path / "wiki" / "personas"
        wiki_dir.mkdir(parents=True)
        personas_dir = tmp_path / "personas"
        personas_dir.mkdir()
        summaries_dir = personas_dir / "_summaries"
        summaries_dir.mkdir()

        body = "She is the Primarch. Her wisdom flows through the realm."
        _make_wiki(wiki_dir, "eeva", body)
        _make_persona_json(personas_dir, "eeva", ["Stale lore item."])
        summary_path = _make_summary(summaries_dir, "eeva")

        assert summary_path.exists(), "Summary must exist before sync"

        monkeypatch.setattr("scripts.utils.lore_sync.WIKI_PERSONAS_DIR", wiki_dir)
        monkeypatch.setattr("scripts.utils.lore_sync.PERSONAS_DIR", personas_dir)
        monkeypatch.setattr("scripts.utils.lore_sync.SUMMARIES_DIR", summaries_dir)

        syncer = LoreSyncer(dry_run=False)
        exit_code = syncer.run()

        assert exit_code == 0
        assert not summary_path.exists(), "Summary cache must be deleted after lore change"

    def test_summary_not_deleted_when_lore_unchanged(self, tmp_path, monkeypatch):
        """When lore[] is already current, the summary cache must be left alone."""
        wiki_dir = tmp_path / "wiki" / "personas"
        wiki_dir.mkdir(parents=True)
        personas_dir = tmp_path / "personas"
        personas_dir.mkdir()
        summaries_dir = personas_dir / "_summaries"
        summaries_dir.mkdir()

        body = "She is the Primarch. Her wisdom flows through the realm."
        existing_lore = prose_to_lore(body)

        _make_wiki(wiki_dir, "eeva", body)
        _make_persona_json(personas_dir, "eeva", existing_lore)
        summary_path = _make_summary(summaries_dir, "eeva")

        monkeypatch.setattr("scripts.utils.lore_sync.WIKI_PERSONAS_DIR", wiki_dir)
        monkeypatch.setattr("scripts.utils.lore_sync.PERSONAS_DIR", personas_dir)
        monkeypatch.setattr("scripts.utils.lore_sync.SUMMARIES_DIR", summaries_dir)

        syncer = LoreSyncer(dry_run=False)
        exit_code = syncer.run()

        assert exit_code == 0
        # Summary should still be there — lore didn't change
        assert summary_path.exists(), "Summary cache must survive when lore is unchanged"

    def test_no_summary_file_does_not_error(self, tmp_path, monkeypatch):
        """Sync completes cleanly even when no summary cache file exists."""
        wiki_dir = tmp_path / "wiki" / "personas"
        wiki_dir.mkdir(parents=True)
        personas_dir = tmp_path / "personas"
        personas_dir.mkdir()
        summaries_dir = personas_dir / "_summaries"
        summaries_dir.mkdir()

        body = "She is the Primarch. Her wisdom guides all."
        _make_wiki(wiki_dir, "eeva", body)
        _make_persona_json(personas_dir, "eeva", ["Old lore."])
        # No summary file created

        monkeypatch.setattr("scripts.utils.lore_sync.WIKI_PERSONAS_DIR", wiki_dir)
        monkeypatch.setattr("scripts.utils.lore_sync.PERSONAS_DIR", personas_dir)
        monkeypatch.setattr("scripts.utils.lore_sync.SUMMARIES_DIR", summaries_dir)

        syncer = LoreSyncer(dry_run=False)
        exit_code = syncer.run()

        assert exit_code == 0

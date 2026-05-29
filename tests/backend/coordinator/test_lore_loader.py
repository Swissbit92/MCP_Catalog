"""Unit tests for src/coordinator/lore_loader.py

Tests cover:
- Frontmatter stripping
- File-level caching (read-once guarantee)
- Missing entity → None
- Known persona → combined 3-entity context
- Unknown persona (Wanderer/Gojo) → empty string
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch, mock_open, call

import pytest

# Ensure project root is on the path so coordinator imports work
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_wiki(tmp_path: Path) -> Path:
    """Create a minimal wiki tree under tmp_path and return the wiki root."""
    wiki = tmp_path / "wiki"
    (wiki / "personas").mkdir(parents=True)
    (wiki / "houses").mkdir(parents=True)
    (wiki / "locations").mkdir(parents=True)
    return wiki


def _write_entity(wiki: Path, subdir: str, entity_id: str, body: str) -> Path:
    """Write a minimal wiki entity file with frontmatter + body."""
    content = (
        "---\n"
        f"entity_id: {entity_id}\n"
        "---\n"
        f"{body}"
    )
    p = wiki / subdir / f"{entity_id}.md"
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_lore_cache():
    """Clear the module-level cache between tests to ensure isolation."""
    import coordinator.lore_loader as ll
    original = ll._cache.copy()
    ll._cache.clear()
    yield
    ll._cache.clear()
    ll._cache.update(original)


# ---------------------------------------------------------------------------
# Tests: load_entity_body
# ---------------------------------------------------------------------------

class TestLoadEntityBody:
    def test_strips_frontmatter(self, tmp_path):
        """Body returned should not contain the --- YAML block."""
        wiki = _make_wiki(tmp_path)
        _write_entity(wiki, "personas", "persona-eeva", "She was the first to Fall.\n")

        import coordinator.lore_loader as ll
        with patch.object(ll, "_WIKI_DIR", wiki):
            result = ll.load_entity_body("persona-eeva")

        assert result is not None
        assert "---" not in result
        assert "She was the first to Fall." in result

    def test_caches_result(self, tmp_path):
        """Second call must not re-read the file (cache hit)."""
        wiki = _make_wiki(tmp_path)
        _write_entity(wiki, "personas", "persona-eeva", "Cached body.\n")

        import coordinator.lore_loader as ll
        with patch.object(ll, "_WIKI_DIR", wiki):
            # Prime the cache
            first = ll.load_entity_body("persona-eeva")
            # Corrupt the file — second call should still return cached value
            (wiki / "personas" / "persona-eeva.md").write_text("CORRUPTED", encoding="utf-8")
            second = ll.load_entity_body("persona-eeva")

        assert first == second
        assert "Cached body." in first

    def test_missing_entity_returns_none(self, tmp_path):
        """Non-existent entity_id must return None (not raise)."""
        wiki = _make_wiki(tmp_path)

        import coordinator.lore_loader as ll
        with patch.object(ll, "_WIKI_DIR", wiki):
            result = ll.load_entity_body("persona-nonexistent")

        assert result is None

    def test_body_stripped_correctly_with_multiline_frontmatter(self, tmp_path):
        """Multiline frontmatter block is fully stripped."""
        wiki = _make_wiki(tmp_path)
        content = (
            "---\n"
            "title: The Primarch\n"
            "status: active\n"
            "entity_id: persona-eeva\n"
            "---\n"
            "The true body starts here.\n"
        )
        p = wiki / "personas" / "persona-eeva.md"
        p.write_text(content, encoding="utf-8")

        import coordinator.lore_loader as ll
        with patch.object(ll, "_WIKI_DIR", wiki):
            result = ll.load_entity_body("persona-eeva")

        assert "title:" not in result
        assert "The true body starts here." in result


# ---------------------------------------------------------------------------
# Tests: get_persona_lore_context
# ---------------------------------------------------------------------------

class TestGetPersonaLoreContext:
    def test_known_persona_combines_three_entities(self, tmp_path):
        """eeva → concatenates persona-eeva + house-crown + location-central-nexus bodies."""
        wiki = _make_wiki(tmp_path)
        _write_entity(wiki, "personas", "persona-eeva", "Persona body.\n")
        _write_entity(wiki, "houses",   "house-crown",  "House body.\n")
        _write_entity(wiki, "locations", "location-central-nexus", "Location body.\n")

        import coordinator.lore_loader as ll
        with patch.object(ll, "_WIKI_DIR", wiki):
            result = ll.get_persona_lore_context("nephilim_eeva")

        assert "Persona body." in result
        assert "House body." in result
        assert "Location body." in result
        assert "persona-eeva" in result
        assert "house-crown" in result
        assert "location-central-nexus" in result

    def test_unknown_persona_returns_empty_string(self, tmp_path):
        """Wanderer persona (e.g. 'gojo') is not in mapping → returns empty string."""
        import coordinator.lore_loader as ll
        result = ll.get_persona_lore_context("gojo")
        assert result == ""

    def test_none_persona_key_returns_empty_string(self):
        """Passing an empty string persona_key returns empty string."""
        import coordinator.lore_loader as ll
        result = ll.get_persona_lore_context("")
        assert result == ""

    def test_missing_entity_files_handled_gracefully(self, tmp_path):
        """If wiki files are missing, returns empty string (no exception)."""
        # Empty wiki — no files
        wiki = _make_wiki(tmp_path)

        import coordinator.lore_loader as ll
        with patch.object(ll, "_WIKI_DIR", wiki):
            result = ll.get_persona_lore_context("nephilim_eeva")

        # Should return empty string (all three entities missing)
        assert result == ""

    def test_word_limit_truncation(self, tmp_path):
        """Very long entity bodies are truncated to ≤ _MAX_WORDS words."""
        wiki = _make_wiki(tmp_path)
        long_body = ("word " * 300).strip() + "\n"  # 300 words per entity → 900 total
        _write_entity(wiki, "personas", "persona-eeva", long_body)
        _write_entity(wiki, "houses",   "house-crown",  long_body)
        _write_entity(wiki, "locations", "location-central-nexus", long_body)

        import coordinator.lore_loader as ll
        with patch.object(ll, "_WIKI_DIR", wiki):
            result = ll.get_persona_lore_context("nephilim_eeva")

        word_count = len(result.split())
        # _MAX_WORDS is 600; allow a small margin for section headers
        assert word_count <= ll._MAX_WORDS + 20  # headers add a few words
        assert result.endswith("...")

    def test_all_six_nephilim_keys_recognized(self, tmp_path):
        """All six nephilim persona keys are in the mapping."""
        import coordinator.lore_loader as ll

        keys = [
            "nephilim_eeva",
            "nephilim_aegis",
            "nephilim_aurora",
            "nephilim_cipher",
            "nephilim_nyx",
            "nephilim_solace",
        ]
        for key in keys:
            assert key in ll._PERSONA_ENTITIES, f"{key} missing from _PERSONA_ENTITIES"

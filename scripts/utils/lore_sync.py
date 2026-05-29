#!/usr/bin/env python3
"""
Lore Sync — propagate wiki prose into persona JSON lore[] arrays.

Reads canonical prose from docs/lore/wiki/personas/persona-{name}.md and
updates the corresponding personas/nephilim_{name}.json lore[] field in-place.
Deletes the matching _summaries/Nephilim_{Name}.json cache file when lore changes
so the CV summariser regenerates on next request.

Usage:
    # Preview changes without writing
    python scripts/utils/lore_sync.py --dry-run

    # Sync all personas
    python scripts/utils/lore_sync.py

    # Sync only one persona
    python scripts/utils/lore_sync.py --persona eeva

Exit codes:
    0 = no changes needed (or all changes applied successfully)
    1 = one or more errors occurred (still processes remaining personas)
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Optional

# ── logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ── paths (relative to repo root) ────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[2]
WIKI_PERSONAS_DIR = REPO_ROOT / "docs" / "lore" / "wiki" / "personas"
PERSONAS_DIR = REPO_ROOT / "personas"
SUMMARIES_DIR = PERSONAS_DIR / "_summaries"

# Maximum lore[] items to keep
MAX_LORE_ITEMS = 25
MIN_LORE_ITEMS = 15


# ── prose → lore[] conversion ────────────────────────────────────────────────

def split_frontmatter(text: str) -> tuple[str, str]:
    """Strip YAML frontmatter from markdown text.

    Returns (frontmatter_block, body).  If no frontmatter, frontmatter_block
    is empty string.
    """
    if not text.startswith("---"):
        return "", text

    end = text.find("\n---", 3)
    if end == -1:
        return "", text

    # Skip the closing ---\n
    body_start = end + 4  # len("\n---") = 4
    if body_start < len(text) and text[body_start] == "\n":
        body_start += 1

    return text[: body_start], text[body_start:]


_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
_EXPANSION_HOOK_RE = re.compile(r"^\*?\*?Expansion hook\*?\*?", re.IGNORECASE)


def _clean_sentence(s: str) -> str:
    """Normalise a candidate lore sentence."""
    s = s.strip()
    # Strip leading list markers
    s = re.sub(r"^[-*]\s+", "", s)
    # Collapse wikilinks to plain text: [[persona-eeva]] → persona-eeva
    s = _WIKILINK_RE.sub(lambda m: m.group(1), s)
    # Collapse extra whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _is_complete_sentence(s: str) -> bool:
    """True if the string ends with sentence-terminal punctuation."""
    return bool(s) and s[-1] in ".!?"


def prose_to_lore(body: str) -> list[str]:
    """Convert raw markdown body text to a list of lore[] strings.

    Rules applied (in order):
    1. Split on double newlines to get paragraphs.
    2. Further split each paragraph on ``'. '`` to surface individual statements.
    3. Skip blank lines and Expansion-hook lines.
    4. Normalise (strip whitespace, list markers, wikilinks).
    5. Keep only complete sentences.
    6. Cap at MAX_LORE_ITEMS, preferring longer / more specific statements.
    """
    paragraphs = re.split(r"\n{2,}", body.strip())

    candidates: list[str] = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if _EXPANSION_HOOK_RE.match(para):
            continue

        # Split on sentence boundary: ". " followed by a capital or digit
        parts = re.split(r"(?<=\.)\s+(?=[A-Z\d])", para)
        for part in parts:
            cleaned = _clean_sentence(part)
            if not cleaned:
                continue
            if _EXPANSION_HOOK_RE.match(cleaned):
                continue
            # Ensure terminal punctuation
            if not _is_complete_sentence(cleaned):
                cleaned = cleaned.rstrip() + "."
            candidates.append(cleaned)

    if not candidates:
        return []

    # Prefer longer, more specific statements (richest content first)
    candidates.sort(key=len, reverse=True)

    # Deduplicate while preserving relative order
    seen: set[str] = set()
    unique: list[str] = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique.append(c)

    return unique[:MAX_LORE_ITEMS]


# ── name mapping ─────────────────────────────────────────────────────────────

def wiki_name_to_persona_name(wiki_stem: str) -> str:
    """Map ``persona-eeva`` → ``eeva`` (strips the ``persona-`` prefix)."""
    return wiki_stem.removeprefix("persona-")


def persona_name_to_json_path(name: str) -> Path:
    """``eeva`` → ``personas/nephilim_eeva.json``."""
    return PERSONAS_DIR / f"nephilim_{name}.json"


def persona_name_to_summary_path(name: str) -> Path:
    """``eeva`` → ``personas/_summaries/Nephilim_eeva.json``.

    The capitalisation follows the convention already on disk:
    ``Nephilim_eeva.json``, ``Nephilim_aegis.json``, …
    """
    # Match casing used on disk: Nephilim_{Name}.json with capital first letter
    capitalised = name.capitalize()
    return SUMMARIES_DIR / f"Nephilim_{capitalised}.json"


# ── core sync logic ───────────────────────────────────────────────────────────

class LoreSyncer:
    """Syncs wiki persona prose into persona JSON lore[] arrays."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run

    def sync_one(self, wiki_file: Path) -> bool:
        """Sync a single wiki persona file.

        Returns True if successful (including no-op), False on error.
        """
        name = wiki_name_to_persona_name(wiki_file.stem)
        json_path = persona_name_to_json_path(name)
        summary_path = persona_name_to_summary_path(name)

        logger.debug("Processing %s → %s", wiki_file.name, json_path.name)

        # ── load wiki ──────────────────────────────────────────────────────
        try:
            raw = wiki_file.read_text(encoding="utf-8")
        except OSError as exc:
            logger.error("Cannot read %s: %s", wiki_file, exc)
            return False

        _, body = split_frontmatter(raw)
        new_lore = prose_to_lore(body)

        if not new_lore:
            logger.warning(
                "%s: prose_to_lore produced 0 items — check wiki body content",
                wiki_file.name,
            )
            # Not a fatal error; persona may not have prose yet
            return True

        # ── load persona JSON ──────────────────────────────────────────────
        if not json_path.exists():
            logger.error("Persona JSON not found: %s", json_path)
            return False

        try:
            persona_data = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("Cannot parse %s: %s", json_path, exc)
            return False

        old_lore: list[str] = persona_data.get("lore", [])

        # ── compare ────────────────────────────────────────────────────────
        if old_lore == new_lore:
            logger.info("%s: lore[] unchanged — nothing to do", name)
            return True

        # ── show diff ─────────────────────────────────────────────────────
        logger.info(
            "%s: lore[] changed (%d items → %d items)",
            name,
            len(old_lore),
            len(new_lore),
        )

        added = set(new_lore) - set(old_lore)
        removed = set(old_lore) - set(new_lore)
        for item in sorted(added):
            logger.info("  + %s", item[:100])
        for item in sorted(removed):
            logger.info("  - %s", item[:100])

        if self.dry_run:
            logger.info("[DRY RUN] Would write %s and invalidate %s", json_path.name, summary_path.name)
            return True

        # ── update persona JSON ────────────────────────────────────────────
        persona_data["lore"] = new_lore
        try:
            json_path.write_text(
                json.dumps(persona_data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            logger.info("Wrote %s", json_path)
        except OSError as exc:
            logger.error("Cannot write %s: %s", json_path, exc)
            return False

        # ── invalidate summary cache ───────────────────────────────────────
        if summary_path.exists():
            try:
                summary_path.unlink()
                logger.info("Deleted summary cache %s", summary_path)
            except OSError as exc:
                logger.warning("Could not delete %s: %s", summary_path, exc)
                # Not fatal — cache will simply serve stale data until overwritten

        return True

    def sync_all(self, persona_filter: Optional[str] = None) -> dict[str, int]:
        """Sync all (or one) wiki persona files.

        Returns stats dict.
        """
        stats = {"processed": 0, "changed": 0, "errors": 0, "skipped": 0}

        wiki_files = sorted(WIKI_PERSONAS_DIR.glob("persona-*.md"))
        if not wiki_files:
            logger.warning("No persona-*.md files found in %s", WIKI_PERSONAS_DIR)
            return stats

        for wiki_file in wiki_files:
            name = wiki_name_to_persona_name(wiki_file.stem)

            if persona_filter and name != persona_filter:
                stats["skipped"] += 1
                continue

            stats["processed"] += 1
            ok = self.sync_one(wiki_file)
            if not ok:
                stats["errors"] += 1

        if persona_filter and stats["processed"] == 0:
            logger.error(
                "Persona '%s' not found. Available: %s",
                persona_filter,
                ", ".join(wiki_name_to_persona_name(f.stem) for f in wiki_files),
            )
            stats["errors"] += 1

        return stats

    def run(self, persona_filter: Optional[str] = None) -> int:
        """Run sync and return exit code."""
        if self.dry_run:
            logger.info("DRY RUN — no files will be written")

        stats = self.sync_all(persona_filter=persona_filter)

        logger.info("")
        logger.info("=" * 60)
        logger.info("LORE SYNC SUMMARY")
        logger.info("=" * 60)
        logger.info("Processed:  %d", stats["processed"])
        logger.info("Skipped:    %d", stats["skipped"])
        logger.info("Errors:     %d", stats["errors"])
        if self.dry_run:
            logger.info("(dry-run — nothing written)")
        logger.info("=" * 60)

        return 1 if stats["errors"] > 0 else 0


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync wiki persona prose into persona JSON lore[] arrays.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run — show what would change
  python scripts/utils/lore_sync.py --dry-run

  # Sync all personas
  python scripts/utils/lore_sync.py

  # Sync only eeva
  python scripts/utils/lore_sync.py --persona eeva

Exit codes:
  0 = success (no changes needed or all applied)
  1 = one or more errors during sync
        """,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing anything.",
    )
    parser.add_argument(
        "--persona",
        metavar="NAME",
        help="Sync only this persona by name (e.g. eeva, aegis).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    syncer = LoreSyncer(dry_run=args.dry_run)
    exit_code = syncer.run(persona_filter=args.persona)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

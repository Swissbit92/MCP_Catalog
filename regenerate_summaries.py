#!/usr/bin/env python3
"""
Regenerate all persona summaries with new truncation logic.

This script:
1. Clears the existing summary cache
2. Regenerates all summaries using the new 80-120 token range
3. Validates that all summaries end with proper punctuation
4. Displays summary statistics
"""

from __future__ import annotations

import sys
import io
from pathlib import Path

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from coordinator.persona_memory import (
    clear_summary_cache,
    ensure_all_summaries_serialized,
    _load_all_cards_cached,
    _load_cached_summary,
    _count_tokens
)


def main():
    print("=" * 70)
    print("PERSONA SUMMARY REGENERATION")
    print("=" * 70)

    # Step 1: Clear existing cache
    print("\n[1/4] Clearing existing summary cache...")
    deleted_count = clear_summary_cache()
    print(f"✓ Deleted {deleted_count} cached summaries")

    # Step 2: Get list of all personas
    print("\n[2/4] Loading persona definitions...")
    cards = _load_all_cards_cached()
    print(f"✓ Found {len(cards)} personas")

    # Step 3: Regenerate all summaries
    print("\n[3/4] Regenerating summaries with new logic...")
    print("  (Using 80-120 token range with sentence-boundary truncation)")
    built, skipped = ensure_all_summaries_serialized(timeout_sec=300.0)
    print(f"✓ Built: {built}, Skipped: {skipped}")

    # Step 4: Validate all summaries
    print("\n[4/4] Validating generated summaries...")
    print()

    all_valid = True
    stats = {
        'total': 0,
        'valid_punctuation': 0,
        'invalid_punctuation': 0,
        'min_tokens': float('inf'),
        'max_tokens': 0,
        'total_tokens': 0
    }

    for card in cards:
        key = (card.get("key") or "Persona").split()[0].capitalize()
        name = card.get("display_name") or key

        # Load summary
        summary_data = _load_cached_summary(key)

        if not summary_data:
            print(f"❌ {name}: No summary found")
            all_valid = False
            continue

        summary = summary_data.get("summary", "")
        tokens = _count_tokens(summary)
        ends_properly = summary[-1] in '.!?' if summary else False

        stats['total'] += 1
        stats['total_tokens'] += tokens
        stats['min_tokens'] = min(stats['min_tokens'], tokens)
        stats['max_tokens'] = max(stats['max_tokens'], tokens)

        if ends_properly:
            stats['valid_punctuation'] += 1
            status = "✓"
        else:
            stats['invalid_punctuation'] += 1
            status = "❌"
            all_valid = False

        # Display summary info
        print(f"{status} {name:20s} | {tokens:3d} tokens | ends: '{summary[-1] if summary else '(empty)'}'")

        # Show first/last 60 chars
        if summary:
            preview = summary[:60] + "..." if len(summary) > 60 else summary
            ending = "..." + summary[-60:] if len(summary) > 60 else summary
            print(f"   Start: {preview}")
            print(f"   End:   {ending}")
            print()

    # Display statistics
    print("\n" + "=" * 70)
    print("SUMMARY STATISTICS")
    print("=" * 70)
    print(f"Total summaries:        {stats['total']}")
    print(f"Valid punctuation:      {stats['valid_punctuation']} ({100 * stats['valid_punctuation'] / max(1, stats['total']):.1f}%)")
    print(f"Invalid punctuation:    {stats['invalid_punctuation']}")
    print(f"Token range:            {stats['min_tokens']}-{stats['max_tokens']} tokens")

    if stats['total'] > 0:
        avg_tokens = stats['total_tokens'] / stats['total']
        print(f"Average tokens:         {avg_tokens:.1f}")

    print()

    if all_valid:
        print("✓ SUCCESS: All summaries end with proper punctuation!")
        print("=" * 70)
        return 0
    else:
        print("❌ FAILURE: Some summaries have issues (see above)")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

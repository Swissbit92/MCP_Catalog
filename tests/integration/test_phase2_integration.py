# tests/integration/test_phase2_integration.py
"""
Phase 2 Integration Tests with Clear KPIs.

Tests the complete Phase 2 persona quality implementation:
- Psychological profiles for all personas
- Example dialogues for all personas
- Emotional state tracking
- System prompt integration

KPIs:
- KPI-1: 100% personas have psychological profiles
- KPI-2: 100% personas have 8+ example dialogues
- KPI-3: Emotional state updates correctly on positive/negative signals
- KPI-4: System prompt includes psychological context
- KPI-5: Emotional context injected into session prompts
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Set test database path
os.environ["COORDINATOR_DB_PATH"] = "test_phase2.db"


def test_kpi1_all_personas_have_psychological_profiles():
    """KPI-1: 100% personas have psychological profiles."""
    from src.coordinator.persona_memory import _load_all_cards_cached

    cards = _load_all_cards_cached()

    personas_with_profile = []
    personas_without_profile = []

    for card in cards:
        key = card.get("key")
        has_profile = "psychological_profile" in card

        if has_profile:
            psych = card.get("psychological_profile", {})
            has_wound = bool(psych.get("core_wound"))
            has_contradictions = len(psych.get("contradiction_pairs", [])) > 0

            if has_wound and has_contradictions:
                personas_with_profile.append(key)
            else:
                personas_without_profile.append(f"{key} (incomplete)")
        else:
            personas_without_profile.append(key)

    coverage = len(personas_with_profile) / len(cards) * 100

    print(f"[KPI-1] Psychological Profile Coverage: {coverage:.1f}%")
    print(f"  With profile: {personas_with_profile}")
    print(f"  Without profile: {personas_without_profile}")

    assert coverage == 100.0, f"KPI-1 FAILED: Only {coverage:.1f}% coverage"
    print("[PASS] KPI-1: 100% personas have psychological profiles")
    return True


def test_kpi2_all_personas_have_example_dialogues():
    """KPI-2: 100% personas have 8+ example dialogues."""
    from src.coordinator.persona_memory import _load_all_cards_cached

    cards = _load_all_cards_cached()

    MIN_DIALOGUES = 8
    personas_with_dialogues = []
    personas_insufficient = []

    for card in cards:
        key = card.get("key")
        dialogues = card.get("example_dialogues", [])
        count = len(dialogues)

        if count >= MIN_DIALOGUES:
            personas_with_dialogues.append(f"{key} ({count})")
        else:
            personas_insufficient.append(f"{key} ({count}/{MIN_DIALOGUES})")

    coverage = len(personas_with_dialogues) / len(cards) * 100

    print(f"[KPI-2] Example Dialogues Coverage: {coverage:.1f}%")
    print(f"  Sufficient (8+): {personas_with_dialogues}")
    print(f"  Insufficient: {personas_insufficient}")

    assert coverage == 100.0, f"KPI-2 FAILED: Only {coverage:.1f}% have 8+ dialogues"
    print("[PASS] KPI-2: 100% personas have 8+ example dialogues")
    return True


def test_kpi3_emotional_state_tracking():
    """KPI-3: Emotional state updates correctly on positive/negative signals."""
    from src.coordinator.repositories.emotional_state_repository import (
        EmotionalStateRepository,
        EmotionalState
    )

    # Use test database
    repo = EmotionalStateRepository("test_kpi3.db")

    # Test 1: Positive signal increases trust
    state = repo.get_or_create("test_positive")
    initial_trust = state.trust_level

    state = repo.update_from_interaction(
        "test_positive",
        "Thank you so much! This is amazing!",
        "I'm glad I could help!"
    )

    assert state.trust_level > initial_trust, "Positive signal should increase trust"
    print(f"  [OK] Positive signal: trust {initial_trust:.3f} -> {state.trust_level:.3f}")

    # Test 2: Negative signal decreases trust
    state = repo.get_or_create("test_negative")
    initial_trust = state.trust_level

    state = repo.update_from_interaction(
        "test_negative",
        "This is wrong and useless!",
        "I apologize for the confusion."
    )

    assert state.trust_level < initial_trust, "Negative signal should decrease trust"
    print(f"  [OK] Negative signal: trust {initial_trust:.3f} -> {state.trust_level:.3f}")

    # Test 3: Rapport increases with each interaction
    state = repo.get_or_create("test_rapport")
    initial_rapport = state.rapport

    for i in range(3):
        state = repo.update_from_interaction(
            "test_rapport",
            f"Question {i}",
            f"Answer {i}"
        )

    assert state.rapport > initial_rapport, "Rapport should increase over time"
    print(f"  [OK] Rapport growth: {initial_rapport:.3f} -> {state.rapport:.3f}")

    # Test 4: Mood detection
    state = repo.update_from_interaction(
        "test_mood",
        "I'm feeling really sad today...",
        "I'm sorry to hear that."
    )

    assert state.current_mood == "sad", f"Should detect sad mood, got: {state.current_mood}"
    print(f"  [OK] Mood detection: {state.current_mood}")

    # Cleanup
    os.remove("test_kpi3.db")

    print("[PASS] KPI-3: Emotional state updates correctly")
    return True


def test_kpi4_psychological_context_in_system_prompt():
    """KPI-4: System prompt includes psychological context."""
    from src.coordinator.persona_memory import (
        build_system_prompt,
        _build_psychological_block,
        resolve_persona_to_card,
        _load_all_cards_cached
    )

    build_system_prompt.cache_clear()

    # Test Eeva (should have psychological profile)
    card = resolve_persona_to_card("Eeva")
    assert card is not None, "Eeva persona not found"

    psych_block = _build_psychological_block(card)
    assert "Psychological Depth" in psych_block, "Missing psychological depth header"
    assert "Core vulnerability" in psych_block, "Missing core vulnerability"
    print(f"  [OK] Eeva has psychological block ({len(psych_block)} chars)")

    # Test that system prompt includes psychological block
    system_prompt = build_system_prompt("Eeva")
    assert "Psychological Depth" in system_prompt, "System prompt missing psychological context"
    print(f"  [OK] System prompt includes psychological context")

    # Test all personas
    cards = _load_all_cards_cached()
    for card in cards:
        key = card.get("key")
        psych_block = _build_psychological_block(card)
        assert len(psych_block) > 0, f"{key} has empty psychological block"

    print("[PASS] KPI-4: System prompt includes psychological context")
    return True


def test_kpi5_emotional_context_injection():
    """KPI-5: Emotional context is injected into session prompts."""
    from src.coordinator.repositories.emotional_state_repository import (
        EmotionalStateRepository,
        EmotionalState
    )

    repo = EmotionalStateRepository("test_kpi5.db")

    # Create state with specific values
    state = EmotionalState(
        session_id="test_session",
        trust_level=0.75,
        rapport=0.65,
        current_mood="happy",
        mood_intensity=0.7,
        last_emotional_event="User expressed gratitude"
    )
    repo.save(state)

    # Get prompt context
    retrieved_state = repo.get("test_session")
    context = retrieved_state.to_prompt_context()

    assert "Current Emotional Context" in context, "Missing context header"
    assert "Relationship:" in context, "Missing relationship description"
    assert "Current mood:" in context, "Missing mood"
    assert "comfortable and friendly" in context, "Should describe trust level 0.75"
    print(f"  [OK] Emotional context generated correctly")
    print(f"  Context preview: {context[:100]}...")

    # Cleanup
    os.remove("test_kpi5.db")

    print("[PASS] KPI-5: Emotional context is injected correctly")
    return True


def test_server_integration():
    """Test that server loads with all Phase 2 components."""
    from src.coordinator.server import app
    # _emotional_state_repo moved to startup module (not re-exported from server)
    from src.coordinator.startup import get_emotional_state_repo

    assert app is not None, "Server app not loaded"

    # Count routes
    route_count = len(app.routes)
    assert route_count >= 20, f"Expected 20+ routes, got {route_count}"
    print(f"  [OK] Server loaded with {route_count} routes")

    # Check for emotional state endpoint
    routes = [r.path for r in app.routes if hasattr(r, 'path')]
    assert any("emotional-state" in r for r in routes), "Missing emotional-state endpoint"
    print(f"  [OK] Emotional state endpoint registered")

    print("[PASS] Server integration working")
    return True


def run_all_tests():
    """Run all KPI tests and report results."""
    print("=" * 70)
    print("PHASE 2 INTEGRATION TESTS - KPI VERIFICATION")
    print("=" * 70)

    tests = [
        ("KPI-1: Psychological Profiles", test_kpi1_all_personas_have_psychological_profiles),
        ("KPI-2: Example Dialogues", test_kpi2_all_personas_have_example_dialogues),
        ("KPI-3: Emotional State Tracking", test_kpi3_emotional_state_tracking),
        ("KPI-4: System Prompt Integration", test_kpi4_psychological_context_in_system_prompt),
        ("KPI-5: Emotional Context Injection", test_kpi5_emotional_context_injection),
        ("Server Integration", test_server_integration),
    ]

    results = []
    for name, test_func in tests:
        print(f"\n--- {name} ---")
        try:
            success = test_func()
            results.append((name, "PASS", None))
        except AssertionError as e:
            results.append((name, "FAIL", str(e)))
            print(f"[FAIL] {e}")
        except Exception as e:
            results.append((name, "ERROR", str(e)))
            print(f"[ERROR] {e}")

    # Summary
    print("\n" + "=" * 70)
    print("KPI SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, status, _ in results if status == "PASS")
    total = len(results)

    for name, status, error in results:
        symbol = "[PASS]" if status == "PASS" else f"[{status}]"
        print(f"  {symbol} {name}")
        if error:
            print(f"         Error: {error}")

    print()
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 70)

    # Cleanup test database
    if os.path.exists("test_phase2.db"):
        os.remove("test_phase2.db")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

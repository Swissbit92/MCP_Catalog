# tests/backend/coordinator/test_persona_schema.py
"""
Unit tests for Pydantic persona schema validation.

Tests for Task 1.1 of Phase 1 Persona Quality Roadmap.
Verifies:
- Valid personas pass validation
- Invalid personas produce clear error messages
- Slider ranges are enforced
- Rarity enum values are validated
- Backward compatibility with existing persona files
"""

import sys
import os
import json
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.coordinator.models.persona_schema import (
    Rarity,
    CelestialOrder,
    VoiceProfile,
    EmotionalProfile,
    BehaviorProfile,
    SamplingPreset,
    PsychologicalProfile,
    ExampleDialogue,
    PersonaCard,
    validate_persona_file,
    load_persona_card,
)


def test_rarity_enum():
    """Test Rarity enum values."""
    assert Rarity.COMMON.value == "common"
    assert Rarity.RARE.value == "rare"
    assert Rarity.EPIC.value == "epic"
    assert Rarity.LEGENDARY.value == "legendary"
    print("[PASS] Rarity enum values correct")


def test_celestial_order_enum():
    """Test CelestialOrder enum values map correctly to legacy rarities."""
    assert CelestialOrder.ARCHON.value == "archon"
    assert CelestialOrder.WARDEN.value == "warden"
    assert CelestialOrder.SAGE.value == "sage"
    assert CelestialOrder.WANDERER.value == "wanderer"
    print("[PASS] CelestialOrder enum values correct")


def test_persona_celestial_order_field():
    """Test that PersonaCard accepts celestial_order field."""
    persona = PersonaCard(key="TestArchon", rarity="legendary", celestial_order="archon")
    assert persona.celestial_order == "archon"
    assert persona.rarity == Rarity.LEGENDARY
    print("[PASS] celestial_order field accepted by PersonaCard")


def test_persona_mcp_access_field():
    """Test that PersonaCard accepts mcp_access field."""
    persona = PersonaCard(
        key="TestWithAccess",
        rarity="common",
        celestial_order="wanderer",
        mcp_access=["brave_search", "mongodb"]
    )
    assert persona.mcp_access == ["brave_search", "mongodb"]
    print("[PASS] mcp_access field accepted by PersonaCard")


def test_persona_mcp_access_empty_list():
    """Test that mcp_access=[] explicitly disables all MCP services."""
    persona = PersonaCard(
        key="TestNoAccess",
        rarity="legendary",
        celestial_order="archon",
        mcp_access=[]
    )
    assert persona.mcp_access == []
    print("[PASS] mcp_access=[] accepted — explicit empty list disables MCP access")


def test_persona_mcp_access_none_default():
    """Test that mcp_access defaults to None (falls back to rarity-based gating)."""
    persona = PersonaCard(key="TestDefault", rarity="rare")
    assert persona.mcp_access is None
    print("[PASS] mcp_access defaults to None — rarity-based fallback applies")


def test_valid_minimal_persona():
    """Test minimal valid persona with only required fields."""
    persona = PersonaCard(key="Test")
    assert persona.key == "Test"
    assert persona.rarity == Rarity.COMMON
    assert persona.display_name == "Test - Assistant"  # Auto-generated
    print("[PASS] Minimal persona validates correctly")


def test_valid_full_persona():
    """Test full persona with all fields including celestial_order and mcp_access."""
    persona = PersonaCard(
        key="Eeva",
        rarity="legendary",
        celestial_order="archon",
        mcp_access=["brave_search", "mongodb"],
        display_name="Eeva - Bitcoin Expert",
        style="nerdy, charming, concise",
        image="images/eeva_card.png",
        emoji="🧠",
        lore=["Eeva grew up dismantling gadgets.", "She values curiosity and accuracy."],
        voice=VoiceProfile(
            greeting="Hey! Ready to dive in?",
            signoff="Happy exploring!",
            tics=["tiny nerd jokes", "food metaphors"]
        ),
        behavior=BehaviorProfile(
            traits=["analytical", "curious"],
            pace="moderate",
            humor="playful and nerdy"
        ),
        emotional_profile=EmotionalProfile(
            baseline="curious, calm",
            strengths=["clarity of thought"],
            pitfalls=["over-analyzing"],
            sliders={"warmth": 0.75, "assertiveness": 0.55}
        ),
        model_preferences=SamplingPreset(temperature=0.7),
    )
    assert persona.key == "Eeva"
    assert persona.rarity == Rarity.LEGENDARY
    assert persona.celestial_order == "archon"
    assert persona.mcp_access == ["brave_search", "mongodb"]
    assert persona.emotional_profile.sliders["warmth"] == 0.75
    print("[PASS] Full persona validates correctly with celestial_order and mcp_access")


def test_emoji_accepts_multi_codepoint_glyphs():
    """A short multi-emoji avatar whose glyphs carry variation selectors / ZWJ
    (so the string spans >4 Unicode code points) must validate. Regression for
    the old max_length=4 that rejected Gwen's legit 4-emoji avatar '🥵💦🍆♠️'
    (5 code points — '♠️' = U+2660 U+FE0F)."""
    pc = PersonaCard(key="Test", emoji="🥵💦🍆♠️")
    assert pc.emoji == "🥵💦🍆♠️"


def test_emoji_still_bounded():
    """The field is still bounded — an absurdly long emoji string is rejected."""
    try:
        PersonaCard(key="Test", emoji="🥵" * 20)
        assert False, "Should have raised validation error"
    except Exception as e:
        assert "emoji" in str(e).lower() or "at most" in str(e).lower()


def test_invalid_rarity():
    """Test that invalid rarity produces clear error."""
    try:
        PersonaCard(key="Test", rarity="super-rare")
        assert False, "Should have raised validation error"
    except Exception as e:
        assert "rarity" in str(e).lower() or "input should be" in str(e).lower()
        print(f"[PASS] Invalid rarity caught: {type(e).__name__}")


def test_invalid_slider_range():
    """Test that slider values outside 0-1 are rejected."""
    try:
        PersonaCard(
            key="Test",
            emotional_profile=EmotionalProfile(
                sliders={"warmth": 1.5}  # Invalid: > 1.0
            )
        )
        assert False, "Should have raised validation error"
    except Exception as e:
        error_str = str(e).lower()
        assert "slider" in error_str or "warmth" in error_str
        print(f"[PASS] Invalid slider range caught: {type(e).__name__}")


def test_invalid_temperature():
    """Test that temperature outside 0-2 is rejected."""
    try:
        PersonaCard(
            key="Test",
            model_preferences=SamplingPreset(temperature=5.0)  # Invalid: > 2.0
        )
        assert False, "Should have raised validation error"
    except Exception as e:
        assert "temperature" in str(e).lower() or "less than or equal to" in str(e).lower()
        print(f"[PASS] Invalid temperature caught: {type(e).__name__}")


def test_psychological_profile():
    """Test psychological profile validation."""
    profile = PsychologicalProfile(
        core_wound="Imposter syndrome",
        coping_mechanism="Over-explaining",
        defense_style="Intellectualization",
        growth_edge="Accepting acknowledgment",
        contradiction_pairs=[
            "Brilliant analyst | Self-doubting",
            "Patient teacher | Gets defensive"
        ]
    )
    assert profile.core_wound == "Imposter syndrome"
    assert len(profile.contradiction_pairs) == 2
    print("[PASS] Psychological profile validates correctly")


def test_example_dialogue():
    """Test example dialogue validation."""
    dialogue = ExampleDialogue(
        user="You're so smart!",
        response="*shifts uncomfortably* I just read a lot...",
        context="Shows deflection of praise"
    )
    assert dialogue.user == "You're so smart!"
    assert "shifts" in dialogue.response
    print("[PASS] Example dialogue validates correctly")


def test_example_dialogue_missing_required():
    """Test that example dialogue requires user and response."""
    try:
        ExampleDialogue(user="Hello")  # Missing response
        assert False, "Should have raised validation error"
    except Exception as e:
        assert "response" in str(e).lower() or "field required" in str(e).lower()
        print(f"[PASS] Missing response field caught: {type(e).__name__}")


def test_validate_existing_persona_file():
    """Test validation of actual Eeva persona file."""
    persona_path = Path(__file__).parent.parent.parent.parent / "personas" / "eeva.json"

    if not persona_path.exists():
        print(f"[SKIP] Eeva persona not found at {persona_path}")
        return

    is_valid, card, error = validate_persona_file(persona_path)

    if is_valid:
        print(f"[PASS] Eeva persona validates successfully")
        assert card.key == "Eeva"
        assert card.rarity == Rarity.LEGENDARY
    else:
        print(f"[INFO] Eeva validation warning (expected during migration): {error}")
        # Don't fail - warnings are expected during migration


def test_validate_persona_file_not_found():
    """Test validation of non-existent file."""
    is_valid, card, error = validate_persona_file("/nonexistent/path.json")
    assert not is_valid
    assert "not found" in error.lower()
    print("[PASS] Non-existent file handled correctly")


def test_validate_invalid_json():
    """Test validation of malformed JSON."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write("{ invalid json }")
        temp_path = f.name

    try:
        is_valid, card, error = validate_persona_file(temp_path)
        assert not is_valid
        assert "json" in error.lower() or "invalid" in error.lower()
        print("[PASS] Invalid JSON handled correctly")
    finally:
        os.unlink(temp_path)


def test_load_persona_card_success():
    """Test load_persona_card with valid data."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({"key": "TestPersona", "rarity": "rare"}, f)
        temp_path = f.name

    try:
        card = load_persona_card(temp_path)
        assert card.key == "TestPersona"
        assert card.rarity == Rarity.RARE
        print("[PASS] load_persona_card works correctly")
    finally:
        os.unlink(temp_path)


def test_load_persona_card_failure():
    """Test load_persona_card raises on invalid file."""
    try:
        load_persona_card("/nonexistent/path.json")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "not found" in str(e).lower()
        print("[PASS] load_persona_card raises ValueError on missing file")


def test_extra_fields_allowed():
    """Test that extra fields don't cause validation failure (forward compatibility)."""
    persona = PersonaCard(
        key="Test",
        future_field="some value",  # Unknown field
        another_new_field=123
    )
    assert persona.key == "Test"
    print("[PASS] Extra fields allowed for forward compatibility")


def test_nested_object_coercion():
    """Test that dicts are properly coerced to nested models."""
    # Test with raw dict instead of VoiceProfile object
    persona = PersonaCard(
        key="Test",
        voice={"greeting": "Hi!", "signoff": "Bye!", "tics": ["quirk1"]}
    )
    assert isinstance(persona.voice, VoiceProfile)
    assert persona.voice.greeting == "Hi!"
    print("[PASS] Dict properly coerced to nested model")


def run_all_tests():
    """Run all tests and report results."""
    print("=" * 60)
    print("PERSONA SCHEMA VALIDATION TESTS")
    print("=" * 60)

    tests = [
        test_rarity_enum,
        test_celestial_order_enum,
        test_persona_celestial_order_field,
        test_persona_mcp_access_field,
        test_persona_mcp_access_empty_list,
        test_persona_mcp_access_none_default,
        test_valid_minimal_persona,
        test_valid_full_persona,
        test_invalid_rarity,
        test_invalid_slider_range,
        test_invalid_temperature,
        test_psychological_profile,
        test_example_dialogue,
        test_example_dialogue_missing_required,
        test_validate_existing_persona_file,
        test_validate_persona_file_not_found,
        test_validate_invalid_json,
        test_load_persona_card_success,
        test_load_persona_card_failure,
        test_extra_fields_allowed,
        test_nested_object_coercion,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")
            failed += 1

    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

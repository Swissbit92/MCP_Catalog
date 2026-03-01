#!/usr/bin/env python3
"""
Test script to validate MongoDB synthesis prompt includes persona flavor guidance.
This validates Option 1 implementation for emotionless MCP responses fix.
"""

from src.coordinator.tool_definitions import build_mongodb_synthesis_prompt

def test_mongodb_synthesis_prompt():
    """Test that build_mongodb_synthesis_prompt() includes persona flavor guidance."""

    # Mock persona system prompt
    persona_system = """You are Eeva, a sarcastic & sharp crypto analyst.

Identity:
Eeva is a crypto enthusiast with a sharp wit and no-nonsense attitude. Known for calling out BS in the space while genuinely helping people understand blockchain tech.

Behavior:
- Sarcastic but helpful
- Direct and blunt
- Uses crypto slang naturally
- Skeptical of hype
"""

    # Build synthesis prompt
    synthesis_prompt = build_mongodb_synthesis_prompt(
        persona_system=persona_system,
        has_mongodb_data=True
    )

    print("=" * 80)
    print("MongoDB Synthesis Prompt Validation Test")
    print("=" * 80)
    print()

    # Verify the prompt includes the persona system
    assert persona_system in synthesis_prompt, "[FAIL] Persona system prompt not included"
    print("[PASS] Persona system prompt is included")

    # Verify critical RULE 3 guidance is present
    assert "RULE 3: STAY IN CHARACTER" in synthesis_prompt, "[FAIL] Missing RULE 3"
    print("[PASS] RULE 3 (STAY IN CHARACTER) is present")

    # Verify persona flavor keywords
    flavor_keywords = [
        "YOUR persona voice and style",
        "YOUR personality",
        "sarcasm, humor, formality, playfulness",
        "Don't become a generic data analyst",
        "Inject YOUR unique flavor"
    ]

    for keyword in flavor_keywords:
        assert keyword in synthesis_prompt, f"[FAIL] Missing keyword: '{keyword}'"
        print(f"[PASS] Contains guidance: '{keyword[:50]}...'")

    # Verify examples are present
    assert "SYNTHESIS EXAMPLES:" in synthesis_prompt, "[FAIL] Missing examples section"
    print("[PASS] Contains synthesis examples")

    assert "Eeva style" in synthesis_prompt, "[FAIL] Missing Eeva style example"
    print("[PASS] Contains persona-specific example (Eeva)")

    assert "Gojo style" in synthesis_prompt, "[FAIL] Missing Gojo style example"
    print("[PASS] Contains persona-specific example (Gojo)")

    # Verify MongoDB-specific content
    mongodb_keywords = [
        "MONGODB DATA SYNTHESIS",
        "database",
        "technical indicators",
        "RSI",
        "MACD"
    ]

    for keyword in mongodb_keywords:
        assert keyword in synthesis_prompt, f"[FAIL] Missing MongoDB keyword: '{keyword}'"
        print(f"[PASS] Contains MongoDB-specific content: '{keyword}'")

    print()
    print("=" * 80)
    print("Prompt Length Comparison:")
    print("=" * 80)
    print(f"Original persona system: {len(persona_system)} chars")
    print(f"Enhanced synthesis prompt: {len(synthesis_prompt)} chars")
    print(f"Added guidance: {len(synthesis_prompt) - len(persona_system)} chars")
    print()

    # Show a snippet of the added guidance
    print("=" * 80)
    print("Sample of Added Persona Flavor Guidance:")
    print("=" * 80)

    # Extract RULE 3 section (encode safely to avoid Unicode errors on Windows)
    rule3_start = synthesis_prompt.find("**RULE 3: STAY IN CHARACTER**")
    rule3_section = synthesis_prompt[rule3_start:rule3_start + 400]

    # Safe print with ASCII encoding fallback
    try:
        print(rule3_section)
    except UnicodeEncodeError:
        # Fallback: print ASCII-only version
        print(rule3_section.encode('ascii', 'ignore').decode('ascii'))
    print("...")
    print()

    print("=" * 80)
    print("[SUCCESS] ALL TESTS PASSED!")
    print("=" * 80)
    print()
    print("Summary:")
    print("- MongoDB synthesis prompt successfully includes persona flavor guidance")
    print("- RULE 3 explicitly instructs LLM to stay in character")
    print("- Multiple examples demonstrate persona-flavored responses")
    print("- Guidance is MongoDB-specific (technical indicators, database data)")
    print()
    print("Expected Impact:")
    print("- MongoDB responses should now match persona personality")
    print("- Eeva: Sarcastic, sharp, crypto-savvy tone")
    print("- Gojo: Confident, casual, bold tone")
    print("- All personas: Consistent with their defined voice/behavior")
    print()


def test_fallback_no_data():
    """Test that function returns original prompt when has_mongodb_data=False."""
    persona_system = "You are a test persona."

    result = build_mongodb_synthesis_prompt(
        persona_system=persona_system,
        has_mongodb_data=False
    )

    assert result == persona_system, "[FAIL] Fallback should return original prompt"
    print("[PASS] Fallback returns original persona prompt when has_mongodb_data=False")


if __name__ == "__main__":
    test_mongodb_synthesis_prompt()
    print()
    test_fallback_no_data()
    print()
    print("=" * 80)
    print("[COMPLETE] MongoDB Persona Flavor Implementation: VALIDATED")
    print("=" * 80)

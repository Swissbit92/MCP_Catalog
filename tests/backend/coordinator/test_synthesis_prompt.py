# test_synthesis_prompt.py
# Unit tests for synthesis prompt builder

import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from coordinator.tool_definitions import build_synthesis_prompt


def test_synthesis_prompt_includes_search_instructions():
    """Verify synthesis prompt has search result usage instructions."""
    persona_system = "You are Eeva, a sarcastic AI assistant."
    synthesis_prompt = build_synthesis_prompt(persona_system, has_search_results=True)

    # Should include original persona
    assert "You are Eeva" in synthesis_prompt

    # Should include search result usage rules
    assert "ONLY use information from the web search results" in synthesis_prompt
    assert "Do NOT use your training data" in synthesis_prompt
    assert "RULE 1: USE ONLY SEARCH RESULTS" in synthesis_prompt

    print("[PASS] test_synthesis_prompt_includes_search_instructions")


def test_synthesis_prompt_includes_synthesis_instructions():
    """Verify synthesis prompt has synthesis guidance."""
    synthesis_prompt = build_synthesis_prompt("", has_search_results=True)

    # Should include synthesis rules
    assert "RULE 2: SYNTHESIZE NATURALLY" in synthesis_prompt
    assert "Don't just repeat or list the search results" in synthesis_prompt
    assert "Combine information from multiple sources" in synthesis_prompt

    print("[PASS] test_synthesis_prompt_includes_synthesis_instructions")


def test_synthesis_prompt_includes_persona_voice_instructions():
    """Verify synthesis prompt maintains persona voice."""
    synthesis_prompt = build_synthesis_prompt("", has_search_results=True)

    # Should include persona voice maintenance
    assert "RULE 3: STAY IN CHARACTER" in synthesis_prompt
    assert "Answer in your persona voice and style" in synthesis_prompt
    assert "Use your personality" in synthesis_prompt

    print("[PASS] test_synthesis_prompt_includes_persona_voice_instructions")


def test_synthesis_prompt_includes_accuracy_requirements():
    """Verify synthesis prompt has accuracy rules."""
    synthesis_prompt = build_synthesis_prompt("", has_search_results=True)

    # Should include accuracy requirements
    assert "RULE 4: BE ACCURATE" in synthesis_prompt
    assert "Use exact numbers, dates, and facts" in synthesis_prompt
    assert "Don't round numbers unless the source does" in synthesis_prompt

    print("[PASS] test_synthesis_prompt_includes_accuracy_requirements")


def test_synthesis_prompt_includes_citation_format():
    """Verify synthesis prompt has citation format examples."""
    synthesis_prompt = build_synthesis_prompt("", has_search_results=True)

    # Should include citation format requirements
    assert "RULE 5: MANDATORY SOURCE CITATIONS" in synthesis_prompt
    assert "Sources:" in synthesis_prompt
    assert "[" in synthesis_prompt  # Bullet point format
    assert "CITATION REQUIREMENTS:" in synthesis_prompt

    print("[PASS] test_synthesis_prompt_includes_citation_format")


def test_synthesis_prompt_includes_examples():
    """Verify synthesis prompt has positive/negative examples."""
    synthesis_prompt = build_synthesis_prompt("", has_search_results=True)

    # Should include synthesis examples
    assert "SYNTHESIS EXAMPLES:" in synthesis_prompt
    assert "WRONG" in synthesis_prompt
    assert "CORRECT" in synthesis_prompt

    # Should have Ethereum price example (specific to hallucination issue)
    assert "Ethereum" in synthesis_prompt
    assert "$3,245.67" in synthesis_prompt  # Correct price example
    assert "$1,850" in synthesis_prompt  # Wrong price example (training data)

    # Should have raw dump example
    assert "Bitcoin Price Soars" in synthesis_prompt or "raw dump" in synthesis_prompt.lower()

    # Should have inline citation example
    assert "inline" in synthesis_prompt.lower() or "[Source](url1)" in synthesis_prompt

    print("[PASS] test_synthesis_prompt_includes_examples")


def test_synthesis_without_search_results():
    """Verify synthesis prompt degrades gracefully without search."""
    persona_system = "You are Eeva, a sarcastic AI assistant."
    synthesis_prompt = build_synthesis_prompt(persona_system, has_search_results=False)

    # Should just return original persona prompt
    assert synthesis_prompt == persona_system
    assert "SYNTHESIS" not in synthesis_prompt

    print("[PASS] test_synthesis_without_search_results")


def test_synthesis_prompt_length():
    """Verify synthesis prompt is reasonable length (not too long)."""
    persona_system = "You are Eeva, a sarcastic AI assistant." * 10  # Simulate longer persona
    synthesis_prompt = build_synthesis_prompt(persona_system, has_search_results=True)

    # Should be longer than original but not excessively
    assert len(synthesis_prompt) > len(persona_system)
    assert len(synthesis_prompt) < len(persona_system) + 5000  # Synthesis instructions ~3KB

    print("[PASS] test_synthesis_prompt_length")


def test_synthesis_prompt_preserves_persona():
    """Verify original persona prompt is preserved at the start."""
    persona_system = "You are Eeva, a legendary AI with sarcastic wit and deep expertise."
    synthesis_prompt = build_synthesis_prompt(persona_system, has_search_results=True)

    # Original persona should be at the start
    assert synthesis_prompt.startswith(persona_system)

    # Synthesis instructions should be appended
    assert "---" in synthesis_prompt  # Separator
    assert synthesis_prompt.index("---") > len(persona_system)

    print("[PASS] test_synthesis_prompt_preserves_persona")


def test_synthesis_prompt_specific_hallucination_warnings():
    """Verify synthesis prompt warns against specific hallucination scenarios."""
    synthesis_prompt = build_synthesis_prompt("", has_search_results=True)

    # Should warn against using training data
    assert "training data instead of search results" in synthesis_prompt.lower()

    # Should have example of wrong price vs. correct price
    assert "using old training data" in synthesis_prompt.lower() or "uses old training data" in synthesis_prompt.lower()

    # Should emphasize NOT using estimates
    assert "Do NOT make up or estimate" in synthesis_prompt

    print("[PASS] test_synthesis_prompt_specific_hallucination_warnings")


if __name__ == "__main__":
    print("Running Synthesis Prompt Unit Tests")
    print("=" * 80)

    # Run all tests
    test_synthesis_prompt_includes_search_instructions()
    test_synthesis_prompt_includes_synthesis_instructions()
    test_synthesis_prompt_includes_persona_voice_instructions()
    test_synthesis_prompt_includes_accuracy_requirements()
    test_synthesis_prompt_includes_citation_format()
    test_synthesis_prompt_includes_examples()
    test_synthesis_without_search_results()
    test_synthesis_prompt_length()
    test_synthesis_prompt_preserves_persona()
    test_synthesis_prompt_specific_hallucination_warnings()

    print("=" * 80)
    print("[SUCCESS] All 10 synthesis prompt tests PASSED!")

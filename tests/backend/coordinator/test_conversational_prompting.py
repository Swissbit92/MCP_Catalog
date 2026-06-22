"""
Unit tests for Phase 1: Conversational prompting
Tests prompt construction, curiosity blocks, and message parsing
"""

import pytest
from src.coordinator.prompt_builder import (
    build_system_prompt,
    _build_curiosity_block,
    CONVERSATIONAL_BEHAVIOR_RULES,
    CONVERSATIONAL_EXAMPLES
)
from src.coordinator.persona_loader import get_persona_card


class TestConversationalPromptConstruction:
    """Test that system prompts include conversational elements."""

    def test_conversational_rules_in_prompt(self):
        """Verify CONVERSATIONAL_BEHAVIOR_RULES included in system prompt.

        The prompt was migrated to XML-tagged sections, so the old uppercase
        headers ("CONVERSATIONAL ENGAGEMENT", etc.) no longer exist — assert the
        current section tag plus the actual rule/format text that is injected.
        """
        prompt = build_system_prompt("Eeva")

        assert "<companion_behavior>" in prompt
        assert "COMPANION, not a Q&A bot" in prompt
        assert "Show genuine curiosity" in prompt
        assert "<response_format>" in prompt
        assert "MULTI-MESSAGE FORMAT" in prompt
        assert "<msg>" in prompt

    def test_few_shot_examples_in_prompt(self):
        """Verify few-shot examples included in system prompt.

        Examples now live inside the <response_format> block (no "EXAMPLE
        CONVERSATIONS" header after the XML migration).
        """
        prompt = build_system_prompt("Eeva")

        assert "<response_format>" in prompt
        assert "Example 1" in prompt
        assert "Had kind of a rough day" in prompt  # Example 1
        assert "Just bought some more Bitcoin" in prompt  # Example 2

    def test_curiosity_block_for_persona_with_psychology(self):
        """Verify curiosity guidance generated from psychological profile."""
        card = get_persona_card("Eeva")
        curiosity = _build_curiosity_block(card)

        # Eeva has imposter syndrome + intellectualization
        assert len(curiosity) > 50  # Should have meaningful guidance
        assert "curiosity style" in curiosity.lower()

    def test_curiosity_block_fallback_for_minimal_persona(self):
        """Verify fallback curiosity guidance for personas without psychology."""
        minimal_card = {"key": "test", "rarity": "common"}
        curiosity = _build_curiosity_block(minimal_card)

        assert "genuine curiosity" in curiosity.lower()
        assert len(curiosity) > 20  # Should have fallback text

    def test_prompt_token_budget(self):
        """Ensure new prompt additions don't exceed reasonable token budget."""
        from src.coordinator.llm_client import estimate_tokens

        prompt = build_system_prompt("Eeva")
        tokens = estimate_tokens(prompt)

        # With new additions, should stay under 3000 tokens
        # (Eeva has rich profile + 10 example dialogues, so higher is expected)
        # This still leaves 1000+ tokens for conversation history in 4K context
        assert tokens < 3000, f"Prompt too long: {tokens} tokens"
        print(f"✓ System prompt: {tokens} tokens")


class TestMessageParsing:
    """Test parsing of <msg> tag multi-message responses."""

    def test_parse_single_message(self):
        """Single message without tags should return as-is."""
        response = "Bitcoin is at $87,855 right now."
        messages = self._parse_messages(response)

        assert len(messages) == 1
        assert messages[0] == response

    def test_parse_multi_message(self):
        """Multiple <msg> tags should split into separate messages."""
        response = """<msg>Bitcoin is at $87,855 right now.</msg>
<msg>RSI at 42 means neutral momentum.</msg>
<msg>Are you thinking about buying more?</msg>"""

        messages = self._parse_messages(response)

        assert len(messages) == 3
        assert "Bitcoin is at $87,855" in messages[0]
        assert "RSI at 42" in messages[1]
        assert "Are you thinking about buying" in messages[2]

    def test_parse_mixed_format(self):
        """Handle responses with some tagged, some untagged content."""
        response = """Here's the current price.

<msg>Bitcoin: $87,855</msg>
<msg>What are you thinking?</msg>"""

        messages = self._parse_messages(response)

        # Should extract tagged messages, preserve untagged intro
        assert len(messages) >= 2

    def test_max_message_limit(self):
        """Should cap at 4 messages to prevent spam."""
        response = "\n".join([f"<msg>Message {i}</msg>" for i in range(10)])
        messages = self._parse_messages(response)

        assert len(messages) <= 4, "Should cap at 4 messages max"

    # Helper method (to be implemented in actual code)
    def _parse_messages(self, response: str) -> list[str]:
        """Parse <msg> tags into separate messages."""
        import re

        # Extract all <msg>...</msg> blocks
        msg_pattern = r'<msg>(.*?)</msg>'
        matches = re.findall(msg_pattern, response, re.DOTALL)

        if matches:
            # Strip whitespace, limit to 4 messages
            return [m.strip() for m in matches[:4]]
        else:
            # No tags found, return as single message
            return [response]


class TestQuestionDetection:
    """Test detection and counting of questions in responses."""

    def test_count_questions_simple(self):
        """Count questions in simple responses."""
        response = "Bitcoin is at $87,855. Are you thinking about buying more?"
        count = response.count("?")
        assert count == 1

    def test_count_questions_multi_message(self):
        """Count questions across multi-message response."""
        response = """<msg>Bitcoin is at $87,855</msg>
<msg>Are you thinking about buying more?</msg>
<msg>Or just checking the price?</msg>"""

        count = response.count("?")
        assert count == 2

    def test_detect_over_questioning(self):
        """Flag responses with excessive questions."""
        response = "What? Why? How? When? Where?"
        count = response.count("?")

        assert count >= 4, "Should detect over-questioning"


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

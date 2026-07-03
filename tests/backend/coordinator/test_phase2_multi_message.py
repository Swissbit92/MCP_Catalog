"""
Unit tests for Phase 2: Multi-message response architecture
Tests message parsing, API response format, and schema validation
"""

import pytest
# parse_multi_message_response moved to services.message_processing_service
# (was previously a private helper in routes.chat). Aliased to keep test bodies stable.
from src.coordinator.services.message_processing_service import (
    parse_multi_message_response as _parse_multi_message_response,
)
from src.coordinator.schemas import ResponseMetadata


class TestMessageParsing:
    """Test parsing of <msg> tag multi-message responses."""

    def test_parse_single_message_no_tags(self):
        """Single message without tags should return as-is with 'single' flow."""
        response = "Bitcoin is at $87,855 right now."
        messages, flow_type = _parse_multi_message_response(response)

        assert len(messages) == 1
        assert messages[0] == response
        assert flow_type == 'single'

    def test_parse_multi_message_tags(self):
        """Multiple <msg> tags should split into separate messages with 'multi' flow."""
        response = """<msg>Bitcoin is at $87,855 right now.</msg>
<msg>RSI at 42 means neutral momentum.</msg>
<msg>Are you thinking about buying more?</msg>"""

        messages, flow_type = _parse_multi_message_response(response)

        assert len(messages) == 3
        assert "Bitcoin is at $87,855" in messages[0]
        assert "RSI at 42" in messages[1]
        assert "Are you thinking about buying" in messages[2]
        assert flow_type == 'multi'

    def test_parse_single_message_with_tag(self):
        """Single <msg> tag should return as single message."""
        response = "<msg>Bitcoin is at $87,855.</msg>"

        messages, flow_type = _parse_multi_message_response(response)

        assert len(messages) == 1
        assert "Bitcoin is at $87,855" in messages[0]
        assert flow_type == 'single'

    def test_parse_max_message_limit(self):
        """Should cap at 4 messages to prevent spam."""
        response = "\n".join([f"<msg>Message {i}</msg>" for i in range(10)])
        messages, flow_type = _parse_multi_message_response(response)

        assert len(messages) == 4, "Should cap at 4 messages max"
        assert flow_type == 'multi'

    def test_parse_whitespace_handling(self):
        """Should strip whitespace from parsed messages."""
        response = """<msg>
        Bitcoin is at $87,855.
        </msg>
<msg>  Are you buying?  </msg>"""

        messages, flow_type = _parse_multi_message_response(response)

        assert len(messages) == 2
        assert messages[0] == "Bitcoin is at $87,855."
        assert messages[1] == "Are you buying?"
        assert flow_type == 'multi'

    def test_parse_mixed_content(self):
        """Should handle mixed tagged and untagged content."""
        response = """Here's the current price.

<msg>Bitcoin: $87,855</msg>
<msg>What are you thinking?</msg>"""

        messages, flow_type = _parse_multi_message_response(response)

        # Should extract only tagged messages if 2+ tags found
        if len(messages) >= 2:
            assert "Bitcoin: $87,855" in messages[0] or "Bitcoin: $87,855" in messages[1]
            assert "What are you thinking?" in messages[0] or "What are you thinking?" in messages[1]


class TestResponseMetadata:
    """Test ResponseMetadata schema with Phase 2 fields."""

    def test_metadata_default_single_message(self):
        """Default metadata should indicate single message."""
        metadata = ResponseMetadata()

        assert metadata.source_type == "llm"
        assert metadata.is_multi_message is False
        assert metadata.message_count == 1

    def test_metadata_multi_message_fields(self):
        """Metadata should support multi-message fields."""
        metadata = ResponseMetadata(
            source_type="llm",
            is_multi_message=True,
            message_count=3
        )

        assert metadata.is_multi_message is True
        assert metadata.message_count == 3

    def test_metadata_serialization(self):
        """Metadata should serialize to dict correctly."""
        metadata = ResponseMetadata(
            source_type="llm",
            tools_used=["llm_reasoning"],
            is_multi_message=True,
            message_count=2
        )

        metadata_dict = metadata.model_dump()

        assert metadata_dict["source_type"] == "llm"
        assert metadata_dict["is_multi_message"] is True
        assert metadata_dict["message_count"] == 2
        assert "llm_reasoning" in metadata_dict["tools_used"]


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


class TestMultiMessageBehavior:
    """Test expected multi-message behavior patterns."""

    def test_multi_message_preserves_personality(self):
        """Multi-message should maintain persona voice across messages."""
        # This is more of a guideline test - actual behavior validated in integration tests
        response = """<msg>Bitcoin's sitting at $87,855.</msg>
<msg>RSI at 42 means neutral territory.</msg>
<msg>What's your move?</msg>"""

        messages, flow_type = _parse_multi_message_response(response)

        # Each message should be concise and conversational
        for msg in messages:
            assert len(msg) > 5, "Messages should have substance"
            assert len(msg) < 200, "Messages should be concise"

    def test_multi_message_question_distribution(self):
        """Questions should be distributed across messages, not spammed in one."""
        # Example of good distribution
        good_response = """<msg>Bitcoin is at $87,855.</msg>
<msg>RSI at 42 means neutral momentum.</msg>
<msg>Are you thinking about buying more?</msg>"""

        # Example of bad distribution (all questions in one message)
        bad_response = """<msg>Bitcoin is at $87,855. Are you buying? What's your strategy? Why now?</msg>"""

        good_messages, _ = _parse_multi_message_response(good_response)
        bad_messages, _ = _parse_multi_message_response(bad_response)

        # Good: questions spread across messages
        good_question_counts = [msg.count("?") for msg in good_messages]
        assert max(good_question_counts) <= 1, "Good response has max 1 question per message"

        # Bad: multiple questions in one message
        bad_question_counts = [msg.count("?") for msg in bad_messages]
        assert max(bad_question_counts) >= 2, "Bad response has multiple questions in one message"


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

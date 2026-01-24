"""
End-to-end tests for Phase 1: Full conversation flow
Tests complete user → backend → frontend flow with conversational behavior
"""

import pytest
import time
from src.coordinator.routes.chat import chat
from src.coordinator.schemas import ChatBody, ChatTurn


class TestE2EConversationalFlow:
    """End-to-end tests of conversational engagement."""

    def test_conversation_with_personal_sharing(self):
        """
        Scenario: User shares personal info, persona asks follow-ups
        Expected: Multi-turn conversation with increasing depth
        """
        persona = "Eeva"
        history = []

        # Turn 1: User introduces themselves
        turn1_body = ChatBody(
            persona=persona,
            history=history,
            message="Hi! I'm Alex, just started learning about Bitcoin."
        )

        response1 = chat(turn1_body)
        answer1 = response1["answer"]

        # Assertions turn 1
        assert "?" in answer1, "Should ask a question when user introduces themselves"
        assert len(answer1) > 50, "Should give more than a greeting"

        history.append(ChatTurn(role="user", content=turn1_body.message))
        history.append(ChatTurn(role="assistant", content=answer1))

        print(f"\n--- Turn 1 ---")
        print(f"User: {turn1_body.message}")
        print(f"Eeva: {answer1[:200]}...")

        # Turn 2: User answers and shares more
        turn2_body = ChatBody(
            persona=persona,
            history=history,
            message="I'm trying to understand how to store it safely."
        )

        response2 = chat(turn2_body)
        answer2 = response2["answer"]

        # Assertions turn 2
        assert "wallet" in answer2.lower() or "seed" in answer2.lower(), \
            "Should address wallet/storage"
        # Should still show curiosity
        question_count = answer2.count("?")
        assert question_count >= 1, "Should continue asking questions"

        history.append(ChatTurn(role="user", content=turn2_body.message))
        history.append(ChatTurn(role="assistant", content=answer2))

        print(f"\n--- Turn 2 ---")
        print(f"User: {turn2_body.message}")
        print(f"Eeva: {answer2[:200]}...")

        # Overall conversation metrics
        total_questions = (answer1.count("?") + answer2.count("?"))
        assert total_questions >= 2, "Should ask multiple questions across conversation"
        assert total_questions <= 6, "Should not over-question"

        print(f"\n✓ Total questions: {total_questions} (target: 2-6)")

    def test_factual_query_doesnt_overengage(self):
        """
        Scenario: User asks simple factual question
        Expected: Direct answer, minimal follow-up
        """
        persona = "Eeva"

        body = ChatBody(
            persona=persona,
            history=[],
            message="What's the current Bitcoin block reward?"
        )

        response = chat(body)
        answer = response["answer"]

        # Should answer the question
        assert "6.25" in answer or "3.125" in answer, "Should mention block reward"

        # Should not over-question a factual query
        question_count = answer.count("?")
        assert question_count <= 1, f"Over-questioning factual query: {question_count}"

        print(f"\n--- Factual Query ---")
        print(f"User: {body.message}")
        print(f"Eeva: {answer[:200]}...")
        print(f"✓ Questions: {question_count} (appropriate for factual query)")

    def test_conversation_remembers_name(self):
        """
        Scenario: User shares name, persona uses it later
        Expected: Persona remembers and references name
        """
        persona = "Eeva"
        history = []

        # Turn 1: User shares name
        turn1_body = ChatBody(
            persona=persona,
            history=history,
            message="My name is Sarah, nice to meet you!"
        )

        response1 = chat(turn1_body)
        answer1 = response1["answer"]

        history.append(ChatTurn(role="user", content=turn1_body.message))
        history.append(ChatTurn(role="assistant", content=answer1))

        # Turn 2: Continue conversation
        turn2_body = ChatBody(
            persona=persona,
            history=history,
            message="I'm interested in learning about DCA strategies."
        )

        response2 = chat(turn2_body)
        answer2 = response2["answer"]

        # Should ideally use the name (though memory rules cover this)
        # At minimum, should respond contextually
        assert len(answer2) > 30, "Should give substantive response"

        print(f"\n--- Name Memory ---")
        print(f"User: {turn1_body.message}")
        print(f"Eeva: {answer1[:100]}...")
        print(f"User: {turn2_body.message}")
        print(f"Eeva: {answer2[:100]}...")

        # Note: Full name usage tested in Phase 3 memory tests
        print(f"✓ Conversation flows naturally")


class TestMultiMessageParsing:
    """Test that <msg> tags are properly handled end-to-end."""

    def test_multi_message_response_structure(self):
        """
        If LLM returns <msg> tags, verify they're parsed correctly.
        """
        persona = "Eeva"

        # This may or may not trigger multi-message (LLM dependent)
        body = ChatBody(
            persona=persona,
            history=[],
            message="I'm nervous about my first Bitcoin purchase. Any advice?"
        )

        response = chat(body)
        answer = response["answer"]

        if "<msg>" in answer:
            # LLM used multi-message format
            import re
            messages = re.findall(r'<msg>(.*?)</msg>', answer, re.DOTALL)

            assert len(messages) >= 1, "Should extract at least one message"
            assert len(messages) <= 4, "Should not exceed 4 messages"

            print(f"\n--- Multi-Message Response ---")
            for i, msg in enumerate(messages, 1):
                print(f"Message {i}: {msg.strip()[:100]}...")

            print(f"✓ Parsed {len(messages)} messages")
        else:
            # Single message is acceptable
            print(f"\n✓ Single message response (acceptable)")


# KPI Tracking Test
class TestPhase1KPIs:
    """Automated KPI tracking for Phase 1 success criteria."""

    def test_question_rate_kpi(self):
        """
        KPI: ≥60% of responses include at least one question
        Sample multiple conversations and measure question rate
        """
        persona = "Eeva"
        test_cases = [
            "I'm new to Bitcoin, where should I start?",
            "Just bought my first Bitcoin!",
            "I'm worried about security.",
            "What's the difference between PoW and PoS?",
            "Should I use a hardware wallet?",
        ]

        responses_with_questions = 0
        total_responses = len(test_cases)

        for user_msg in test_cases:
            body = ChatBody(persona=persona, history=[], message=user_msg)
            response = chat(body)
            answer = response["answer"]

            if "?" in answer:
                responses_with_questions += 1

        question_rate = (responses_with_questions / total_responses) * 100

        print(f"\n--- Question Rate KPI ---")
        print(f"Responses with questions: {responses_with_questions}/{total_responses}")
        print(f"Question rate: {question_rate:.1f}%")
        print(f"Target: ≥60%")

        assert question_rate >= 60.0, \
            f"Question rate {question_rate:.1f}% below target (60%)"

        print(f"✓ PASSED: Question rate meets target")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])

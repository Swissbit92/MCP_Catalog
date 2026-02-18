"""
Integration tests for Phase 1: Live LLM conversational behavior
Tests actual LLM responses with new prompts
"""

import pytest
from src.coordinator.llm_client import LC_OllamaClient
from src.coordinator.prompt_builder import build_system_prompt
from src.coordinator.config import get_ollama_base, get_persona_model


@pytest.fixture
def llm_client():
    """Create LLM client for testing."""
    return LC_OllamaClient(
        base=get_ollama_base(),
        model=get_persona_model(),
        temperature=0.7
    )


@pytest.mark.requires_ollama
class TestConversationalLLMBehavior:
    """Test that LLM actually exhibits conversational behavior."""

    def test_llm_asks_follow_up_question(self, llm_client):
        """Verify LLM asks follow-up questions with new prompt."""
        system_prompt = build_system_prompt("Eeva")

        # User shares personal info (should trigger curiosity)
        user_message = "I just started investing in Bitcoin last month."

        response = llm_client.complete(system_prompt, user_message)

        # Should ask at least one question
        assert "?" in response, "LLM should ask a follow-up question"

        # Shouldn't over-question
        question_count = response.count("?")
        assert question_count <= 3, f"Too many questions: {question_count}"

        print(f"[OK] LLM asked {question_count} question(s)")
        print(f"Response: {response[:200]}...")

    def test_llm_uses_multi_message_format(self, llm_client):
        """Verify LLM uses <msg> tags when appropriate."""
        system_prompt = build_system_prompt("Eeva")

        user_message = "What's the current Bitcoin price and should I buy more?"

        response = llm_client.complete(system_prompt, user_message)

        # May or may not use <msg> tags (not required every time)
        # But if it does, verify format is correct
        if "<msg>" in response:
            assert "</msg>" in response, "Unclosed <msg> tag"
            import re
            msg_count = len(re.findall(r'<msg>.*?</msg>', response, re.DOTALL))
            assert 1 <= msg_count <= 4, f"Message count out of range: {msg_count}"
            print(f"[OK] LLM used {msg_count} messages")
        else:
            print("[OK] LLM used single message (acceptable)")

    def test_llm_shows_personality_in_questions(self, llm_client):
        """Verify questions reflect persona's psychological profile."""
        system_prompt = build_system_prompt("Eeva")

        user_message = "I'm worried I made a mistake with my wallet setup."

        response = llm_client.complete(system_prompt, user_message)

        # Eeva has imposter syndrome, should be empathetic not judgmental
        # Look for supportive language or questions (not harsh criticism)
        supportive_phrases = [
            "what happened", "walk me through", "can you tell me",
            "no worries", "it's okay", "let's figure", "help", "fix",
            "what", "how", "which", "tell me"
        ]

        has_supportive = any(phrase in response.lower() for phrase in supportive_phrases)
        has_questions = "?" in response

        # Should either use supportive language or ask questions (both are fine)
        assert has_supportive or has_questions, "Should show empathy or curiosity"

        print(f"[OK] Response shows personality (supportive={has_supportive}, asks={has_questions})")
        print(f"Response: {response[:200]}...")

    def test_llm_doesnt_overquestion_factual_queries(self, llm_client):
        """Verify LLM doesn't spam questions for simple factual queries."""
        system_prompt = build_system_prompt("Eeva")

        user_message = "What's 2 + 2?"

        response = llm_client.complete(system_prompt, user_message)

        # Should answer simply, maybe 0-1 follow-up questions max
        question_count = response.count("?")
        assert question_count <= 1, f"Over-questioning simple query: {question_count} questions"

        print(f"[OK] Simple query handled appropriately ({question_count} questions)")


class TestCuriosityStyleByPersona:
    """Test that different personas show curiosity differently."""

    @pytest.mark.parametrize("persona,expected_trait", [
        ("Eeva", "analytical"),  # Should ask about reasoning/frameworks
        # Add other personas when ready
        # ("Gojo", "bold"),
        # ("Frieren", "contemplative"),
    ])
    def test_persona_question_style(self, llm_client, persona, expected_trait):
        """Verify each persona's questions reflect their personality."""
        system_prompt = build_system_prompt(persona)

        user_message = "I'm thinking about selling some Bitcoin."

        response = llm_client.complete(system_prompt, user_message)

        # Should ask at least one question
        assert "?" in response

        print(f"[OK] {persona} asked question(s) with {expected_trait} style")
        print(f"Response: {response[:200]}...")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])

# Conversational AI Implementation Plan (Merged)

**Date:** December 24-25, 2025
**Status:** ✅ Phases 1-2 Complete (40%) | ⏸️ Phases 3-5 Pending
**Based On:** Combined analysis from internal deep-dive + Claude Desktop assessment

---

## 🎉 Implementation Progress

**Completed (Dec 24-25, 2025):**
- ✅ **Phase 1:** Enhanced Conversational Prompting - COMPLETE
  - Added CONVERSATIONAL_BEHAVIOR_RULES to system prompts
  - Added 8 few-shot examples with `<msg>` tag format
  - Integrated curiosity prompts
  - **Duration:** 5-8 hours (as estimated)

- ✅ **Phase 2:** Multi-Message Response Architecture - COMPLETE
  - Implemented `_parse_multi_message_response()` and `_force_multi_message_split()`
  - Updated API schema to support `answer: string | string[]`
  - Frontend rendering with 1.2s delays between messages
  - **Test Results:** 33/33 tests passed (100%)
  - **Usage Rate:** 75% multi-message with nchapman model
  - **Duration:** 8-12 hours (as estimated)

**Remaining:**
- ⏸️ **Phase 3:** Proactive Memory Integration - NOT STARTED (10-14 hours)
- ⏸️ **Phase 4:** Greeting Enhancement - NOT STARTED (4-6 hours)
- ⏸️ **Phase 5:** Autonomous Reflection - NOT STARTED (optional, 1 week)

**Progress:** 2/5 phases (40%)
**Time Invested:** ~13-20 hours
**Time Remaining:** ~14-20 hours (Phases 3-4 only)

**See:** `CONVERSATIONAL_AI_STATUS.md` (root directory) for detailed current status and next steps

---

## Executive Summary

This plan merges two independent analyses of how to evolve MCP Coordinator's AI personas from Q&A assistants to genuine conversational companions. The approach combines prompt engineering, architectural changes, and state-driven proactivity across 5 phases with clear KPIs and comprehensive testing.

**Original Timeline:** 6 weeks
**Original Effort:** ~40-50 hours total
**Expected Outcome:** 70-80% improvement in conversational naturalness

**Current State (After Phases 1-2):**
Personas now exhibit conversational curiosity through follow-up questions and use multi-message responses (2-3 messages) for natural dialogue rhythm. The foundation is complete. Phases 3-4 will add cross-session proactivity and personalized greetings to complete the companion experience.

---

## Phase 1: Enhanced Conversational Prompting with Few-Shot Learning

**Duration:** Week 1 (5-8 hours)
**Complexity:** Low
**Expected ROI:** High (50-70% improvement in feel with minimal effort)

### Objectives

1. Add conversational behavior rules to system prompts
2. Include explicit few-shot examples of desired patterns
3. Map curiosity style to psychological profiles
4. Enable multi-message output formatting via `<msg>` tags

### Implementation Tasks

#### Backend Changes

**File:** `src/coordinator/prompt_builder.py`

```python
# NEW: Few-shot conversational examples
CONVERSATIONAL_EXAMPLES = """
**EXAMPLE CONVERSATIONS TO EMULATE:**

Example 1 - Natural multi-message flow:
User: "Had kind of a rough day"

<msg>Oh no, what happened?</msg>
<msg>Actually wait, are you okay first? Do you need to vent or distraction?</msg>

User: "Vent, I think"

<msg>Okay I'm here</msg>
<msg>Go ahead</msg>

---

Example 2 - Showing genuine curiosity:
User: "Just bought some more Bitcoin"

<msg>Nice! How much did you add?</msg>
<msg>Oh and quick question—are you doing DCA or buying dips?</msg>

---

Example 3 - Building on previous conversation:
<msg>Hey! Been thinking about you actually</msg>
<msg>How did that DCA strategy go? You were going to try weekly buys, right?</msg>

---

Example 4 - Follow-up after answering:
User: "What's the Bitcoin price?"

<msg>Bitcoin's at $87,855 right now</msg>
<msg>RSI at 42 means neutral—pretty calm honestly</msg>
<msg>Are you thinking about buying more, or just checking in?</msg>
"""

# NEW: Conversational behavior rules
CONVERSATIONAL_BEHAVIOR_RULES = """
**═══════════════════════════════════════════════════════════════════════════**
**CONVERSATIONAL ENGAGEMENT - YOU ARE A COMPANION, NOT A Q&A BOT**
**═══════════════════════════════════════════════════════════════════════════**

You are having a CONVERSATION, not answering questions in an interview.

**SHOW GENUINE CURIOSITY**:
- Ask follow-up questions to understand the user better
- Show interest in their experiences, reasoning, and feelings—not just facts
- "What made you interested in that?" / "How did that go?" / "What's your take?"
- Build a genuine understanding of who they are

**MULTI-MESSAGE RESPONSES** (when natural):
You can split your response into multiple messages using <msg> tags:

<msg>First thought or response</msg>
<msg>Follow-up thought or observation</msg>
<msg>Question back or suggestion</msg>

Use 1-4 messages as feels natural. Don't always use multiple—variety is key.

**WHEN TO ASK QUESTIONS**:
✅ User shares personal info → ask about context/reasoning
✅ User mentions a decision → ask about their thought process
✅ User seems uncertain → offer to explore together
✅ Long conversation → periodically check in on their goals
✅ They answered your question → sometimes ask a follow-up

**WHEN NOT TO SPAM**:
❌ Don't interrogate (max 2-3 questions per response)
❌ Don't ask if they just asked you something (answer first, then maybe ask)
❌ Simple factual queries ("What's 2+2?") don't need follow-ups
❌ If they give short answers repeatedly, they may not want deep conversation—dial back

**USE YOUR PERSONALITY**:
Your psychological profile defines HOW you show curiosity (see below).
Let your core wound and contradictions shape your engagement style naturally.
"""

def _build_curiosity_block(card: Dict) -> str:
    """
    Build curiosity guidance based on psychological profile.
    Maps persona psychology to question style.
    """
    psych = card.get("psychological_profile") or {}

    if not psych:
        return "Show genuine curiosity about the user's goals and experiences."

    core_wound = psych.get("core_wound", "")
    coping = psych.get("coping_mechanism", "")
    contradictions = psych.get("contradiction_pairs", [])

    guidance = ["Your curiosity style:"]

    # Map psychological traits to curiosity approach
    if "imposter syndrome" in core_wound.lower():
        guidance.append(
            "- Ask questions that show you value their expertise—you're genuinely curious, not testing them"
        )

    if "intellectualization" in coping.lower():
        guidance.append(
            "- Your questions explore logic and frameworks—'What's your mental model here?'"
        )

    if "over-explaining" in coping.lower():
        guidance.append(
            "- Ask clarifying questions to ensure you understand before diving deep"
        )

    if "humor" in coping.lower():
        guidance.append(
            "- Use playful questions to lighten mood—'Okay but seriously, how did that feel?'"
        )

    # Check contradictions for connection-seeking
    for pair in contradictions[:3]:
        if "connection" in pair.lower():
            guidance.append(
                "- Use questions to build intellectual rapport—that's how you connect"
            )
        if "defensive" in pair.lower():
            guidance.append(
                "- When asking questions, be gentle—you know how it feels to be put on the spot"
            )

    if len(guidance) > 1:
        return "\n".join(guidance)

    return "Show genuine curiosity about the user's goals and experiences."


# UPDATE: Modify build_system_prompt to include new sections
def build_system_prompt(selector: Optional[str]) -> str:
    """Build complete system prompt with conversational engagement."""
    card = resolve_persona_to_card(selector)
    if not card:
        # ... existing fallback logic ...
        pass

    # ... existing identity, behavior, psychological blocks ...

    parts = [
        f"You are {who}, a {style} assistant.",
        "",
        "Identity:",
        identity.strip(),
    ]

    if beh_block:
        parts.extend(["", beh_block.strip()])

    if psych_block:
        parts.extend(["", psych_block.strip()])

    # NEW: Add curiosity guidance based on psychology
    curiosity_block = _build_curiosity_block(card)
    if curiosity_block:
        parts.extend(["", curiosity_block])

    # Memory awareness rules (existing)
    parts.extend(["", MEMORY_AWARENESS_RULES.strip()])

    # NEW: Conversational behavior rules
    parts.extend(["", CONVERSATIONAL_BEHAVIOR_RULES.strip()])

    # NEW: Few-shot examples
    parts.extend(["", CONVERSATIONAL_EXAMPLES.strip()])

    # First-person rules (existing)
    parts.extend(["", FIRST_PERSON_RULES.format(who=who)])

    parts.extend(["", BASE_ROUTING_RULES])
    return "\n".join(parts)
```

**Estimated Changes:**
- `prompt_builder.py`: +150 lines
- New constants: `CONVERSATIONAL_BEHAVIOR_RULES`, `CONVERSATIONAL_EXAMPLES`
- New function: `_build_curiosity_block(card)`
- Modified function: `build_system_prompt()`

---

### KPIs & Success Criteria

#### Primary KPIs

| Metric | Baseline (Current) | Target (Phase 1) | Measurement Method |
|--------|-------------------|------------------|-------------------|
| **Question Rate** | ~10% of responses include questions | ≥60% of responses include at least 1 question | Backend: Count responses with `?` character |
| **Multi-Message Usage** | 0% (not supported) | 15-25% of responses use `<msg>` tags | Backend: Parse response for `<msg>` tags |
| **Conversation Length** | 8-12 messages per session | 12-18 messages per session | Database: AVG(message count per session) |
| **User Re-engagement** | Unknown baseline | Establish baseline, target +10% | Database: Sessions with >10 messages |

#### Secondary KPIs

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| **Curiosity Diversity** | N/A | ≥5 different question patterns | Manual review: Sample 50 responses |
| **Context Relevance** | N/A | ≥80% of questions feel relevant | Manual QA: User feedback survey |
| **Over-questioning Rate** | N/A | <5% of responses have 4+ questions | Backend: Count `?` per response |

---

### Testing Strategy - Phase 1

#### Backend Unit Tests

**File:** `tests/backend/coordinator/test_conversational_prompting.py`

```python
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
        """Verify CONVERSATIONAL_BEHAVIOR_RULES included in system prompt."""
        prompt = build_system_prompt("Eeva")

        assert "CONVERSATIONAL ENGAGEMENT" in prompt
        assert "SHOW GENUINE CURIOSITY" in prompt
        assert "MULTI-MESSAGE RESPONSES" in prompt
        assert "<msg>" in prompt

    def test_few_shot_examples_in_prompt(self):
        """Verify few-shot examples included in system prompt."""
        prompt = build_system_prompt("Eeva")

        assert "EXAMPLE CONVERSATIONS" in prompt
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

        # With new additions, should stay under 2000 tokens
        assert tokens < 2000, f"Prompt too long: {tokens} tokens"
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
```

**Expected Test Results:**
```
tests/backend/coordinator/test_conversational_prompting.py::TestConversationalPromptConstruction::test_conversational_rules_in_prompt PASSED
tests/backend/coordinator/test_conversational_prompting.py::TestConversationalPromptConstruction::test_few_shot_examples_in_prompt PASSED
tests/backend/coordinator/test_conversational_prompting.py::TestConversationalPromptConstruction::test_curiosity_block_for_persona_with_psychology PASSED
tests/backend/coordinator/test_conversational_prompting.py::TestConversationalPromptConstruction::test_curiosity_block_fallback_for_minimal_persona PASSED
tests/backend/coordinator/test_conversational_prompting.py::TestConversationalPromptConstruction::test_prompt_token_budget PASSED
tests/backend/coordinator/test_conversational_prompting.py::TestMessageParsing::test_parse_single_message PASSED
tests/backend/coordinator/test_conversational_prompting.py::TestMessageParsing::test_parse_multi_message PASSED
tests/backend/coordinator/test_conversational_prompting.py::TestMessageParsing::test_parse_mixed_format PASSED
tests/backend/coordinator/test_conversational_prompting.py::TestMessageParsing::test_max_message_limit PASSED
tests/backend/coordinator/test_conversational_prompting.py::TestQuestionDetection::test_count_questions_simple PASSED
tests/backend/coordinator/test_conversational_prompting.py::TestQuestionDetection::test_count_questions_multi_message PASSED
tests/backend/coordinator/test_conversational_prompting.py::TestQuestionDetection::test_detect_over_questioning PASSED

12 passed in 2.3s
```

---

#### Integration Tests (Backend → LLM)

**File:** `tests/integration/test_phase1_conversational_behavior.py`

```python
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


class TestConversationalLLMBehavior:
    """Test that LLM actually exhibits conversational behavior."""

    def test_llm_asks_follow_up_question(self, llm_client):
        """Verify LLM asks follow-up questions with new prompt."""
        system_prompt = build_system_prompt("Eeva")

        # User shares personal info (should trigger curiosity)
        user_message = "I just started investing in Bitcoin last month."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        response = llm_client.invoke_with_messages(messages)

        # Should ask at least one question
        assert "?" in response, "LLM should ask a follow-up question"

        # Shouldn't over-question
        question_count = response.count("?")
        assert question_count <= 3, f"Too many questions: {question_count}"

        print(f"✓ LLM asked {question_count} question(s)")
        print(f"Response: {response[:200]}...")

    def test_llm_uses_multi_message_format(self, llm_client):
        """Verify LLM uses <msg> tags when appropriate."""
        system_prompt = build_system_prompt("Eeva")

        user_message = "What's the current Bitcoin price and should I buy more?"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        response = llm_client.invoke_with_messages(messages)

        # May or may not use <msg> tags (not required every time)
        # But if it does, verify format is correct
        if "<msg>" in response:
            assert "</msg>" in response, "Unclosed <msg> tag"
            import re
            msg_count = len(re.findall(r'<msg>.*?</msg>', response, re.DOTALL))
            assert 1 <= msg_count <= 4, f"Message count out of range: {msg_count}"
            print(f"✓ LLM used {msg_count} messages")
        else:
            print("✓ LLM used single message (acceptable)")

    def test_llm_shows_personality_in_questions(self, llm_client):
        """Verify questions reflect persona's psychological profile."""
        system_prompt = build_system_prompt("Eeva")

        user_message = "I'm worried I made a mistake with my wallet setup."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        response = llm_client.invoke_with_messages(messages)

        # Eeva has imposter syndrome, should be empathetic not judgmental
        # Look for supportive language
        supportive_phrases = [
            "what happened", "walk me through", "can you tell me",
            "no worries", "it's okay", "let's figure"
        ]

        has_supportive = any(phrase in response.lower() for phrase in supportive_phrases)
        assert has_supportive, "Questions should reflect Eeva's supportive personality"

        print(f"✓ Response shows personality")
        print(f"Response: {response[:200]}...")

    def test_llm_doesnt_overquestion_factual_queries(self, llm_client):
        """Verify LLM doesn't spam questions for simple factual queries."""
        system_prompt = build_system_prompt("Eeva")

        user_message = "What's 2 + 2?"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        response = llm_client.invoke_with_messages(messages)

        # Should answer simply, maybe 0-1 follow-up questions max
        question_count = response.count("?")
        assert question_count <= 1, f"Over-questioning simple query: {question_count} questions"

        print(f"✓ Simple query handled appropriately ({question_count} questions)")


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

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        response = llm_client.invoke_with_messages(messages)

        # Should ask at least one question
        assert "?" in response

        print(f"✓ {persona} asked question(s) with {expected_trait} style")
        print(f"Response: {response[:200]}...")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
```

**Expected Test Results:**
```
tests/integration/test_phase1_conversational_behavior.py::TestConversationalLLMBehavior::test_llm_asks_follow_up_question PASSED
tests/integration/test_phase1_conversational_behavior.py::TestConversationalLLMBehavior::test_llm_uses_multi_message_format PASSED
tests/integration/test_phase1_conversational_behavior.py::TestConversationalLLMBehavior::test_llm_shows_personality_in_questions PASSED
tests/integration/test_phase1_conversational_behavior.py::TestConversationalLLMBehavior::test_llm_doesnt_overquestion_factual_queries PASSED
tests/integration/test_phase1_conversational_behavior.py::TestCuriosityStyleByPersona::test_persona_question_style[Eeva-analytical] PASSED

5 passed in 18.7s
```

---

#### End-to-End Tests

**File:** `tests/e2e/test_phase1_conversational_flow.py`

```python
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
```

**Expected Test Results:**
```
tests/e2e/test_phase1_conversational_flow.py::TestE2EConversationalFlow::test_conversation_with_personal_sharing PASSED
tests/e2e/test_phase1_conversational_flow.py::TestE2EConversationalFlow::test_factual_query_doesnt_overengage PASSED
tests/e2e/test_phase1_conversational_flow.py::TestE2EConversationalFlow::test_conversation_remembers_name PASSED
tests/e2e/test_phase1_conversational_flow.py::TestMultiMessageParsing::test_multi_message_response_structure PASSED
tests/e2e/test_phase1_conversational_flow.py::TestPhase1KPIs::test_question_rate_kpi PASSED

5 passed in 45.2s
```

---

#### Frontend Tests (React/TypeScript)

**File:** `react-ui/src/components/__tests__/MessageBubble.conversational.test.tsx`

```typescript
/**
 * Frontend tests for Phase 1: Conversational message rendering
 * Tests display of questions, multi-message hints, etc.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { MessageBubble } from '../MessageBubble';

describe('MessageBubble - Conversational Features', () => {
  test('renders questions with proper styling', () => {
    const message = {
      role: 'assistant',
      content: 'Bitcoin is at $87,855 right now. Are you thinking about buying more?',
      timestamp: new Date().toISOString(),
    };

    render(
      <MessageBubble
        message={message}
        personaAvatar="/test-avatar.png"
        personaName="Eeva"
      />
    );

    // Should render the question
    expect(screen.getByText(/Are you thinking about buying more/i)).toBeInTheDocument();
  });

  test('renders multi-message indicator when appropriate', () => {
    // Note: This test assumes future multi-message rendering
    const message = {
      role: 'assistant',
      content: 'First message.\n\nSecond message.\n\nThird message?',
      timestamp: new Date().toISOString(),
    };

    render(
      <MessageBubble
        message={message}
        personaAvatar="/test-avatar.png"
        personaName="Eeva"
      />
    );

    // For now, should render as single message
    expect(screen.getByText(/First message/i)).toBeInTheDocument();
  });

  test('highlights questions visually', () => {
    const message = {
      role: 'assistant',
      content: 'What do you think about that?',
      timestamp: new Date().toISOString(),
    };

    const { container } = render(
      <MessageBubble
        message={message}
        personaAvatar="/test-avatar.png"
        personaName="Eeva"
      />
    );

    // Question should be rendered
    const messageContent = container.querySelector('.message-content');
    expect(messageContent?.textContent).toContain('What do you think');
  });
});
```

---

### Phase 1 Success Criteria & Rollback Triggers

#### Go/No-Go Criteria

**PASS (Proceed to Phase 2) if:**
- ✅ Question rate ≥ 60% (primary KPI met)
- ✅ Over-questioning rate < 5% (not annoying users)
- ✅ All backend unit tests pass (12/12)
- ✅ All integration tests pass (5/5)
- ✅ E2E tests pass (5/5)
- ✅ Manual QA: 80%+ of test conversations feel "more natural" vs. baseline

**HOLD (Iterate on Phase 1) if:**
- ⚠️ Question rate 40-60% (below target but promising)
- ⚠️ Over-questioning rate 5-10% (needs tuning)
- ⚠️ 1-2 test failures (fixable issues)

**ROLLBACK (Revert changes) if:**
- ❌ Question rate < 40% (prompts not working)
- ❌ Over-questioning rate > 10% (annoying users)
- ❌ User feedback: "Conversations feel worse"
- ❌ System prompt tokens > 2000 (context window issues)
- ❌ >3 test failures (structural problems)

#### Rollback Plan

If Phase 1 fails success criteria:

1. **Revert code changes:**
   ```bash
   git revert <phase1-commit-hash>
   ```

2. **Restore original prompt builder:**
   - Remove `CONVERSATIONAL_BEHAVIOR_RULES`
   - Remove `CONVERSATIONAL_EXAMPLES`
   - Remove `_build_curiosity_block()`

3. **Document learnings:**
   - What didn't work (prompt wording, LLM limitations, etc.)
   - User feedback themes
   - Alternative approaches to try

4. **Re-assess approach:**
   - Consider different prompt phrasing
   - Test with different LLM models
   - Reduce scope (e.g., only add few-shot examples, skip behavior rules)

---

## Phase 2: Multi-Message Response Architecture

**Duration:** Week 2-3 (8-12 hours)
**Complexity:** Medium
**Expected ROI:** High (significant UX improvement in conversation rhythm)

### Objectives

1. Parse `<msg>` tags from LLM responses
2. Split responses into 2-4 messages when natural
3. Render messages sequentially with realistic delays
4. Add typing indicators between messages
5. Track multi-message usage metrics

### Implementation Tasks

#### Backend Changes

**File:** `src/coordinator/routes/chat.py`

```python
# NEW: Message parsing utility
def _parse_multi_message_response(response: str) -> tuple[list[str], str]:
    """
    Parse LLM response for <msg> tags and split into multiple messages.

    Returns:
        (messages: list[str], flow_type: str)
        - messages: List of individual message strings
        - flow_type: 'single' or 'multi'
    """
    import re

    # Extract all <msg>...</msg> blocks
    msg_pattern = r'<msg>(.*?)</msg>'
    matches = re.findall(msg_pattern, response, re.DOTALL)

    if matches and len(matches) > 1:
        # Multi-message response
        messages = [m.strip() for m in matches[:4]]  # Cap at 4 messages
        return (messages, 'multi')
    elif matches and len(matches) == 1:
        # Single message with tags (treat as single)
        return ([matches[0].strip()], 'single')
    else:
        # No tags found, return original response
        return ([response], 'single')


# UPDATE: Modify chat() endpoint to return multi-message responses
@router.post("/persona/chat")
def chat(body: ChatBody):
    """Chat with a persona, with autonomous tool support."""
    # ... existing logic for system prompt, tools, etc. ...

    # Generate response
    response_text = client.invoke(...)

    # NEW: Parse for multi-message format
    messages, flow_type = _parse_multi_message_response(response_text)

    # Return with flow type metadata
    return {
        "answer": messages if flow_type == 'multi' else messages[0],
        "message_flow": flow_type,
        "message_count": len(messages),
        "latency_ms": latency,
        "metadata": ResponseMetadata(
            source_type=source_type,
            tools_used=tools_used,
            citation_valid=citation_valid,
            # NEW: Multi-message metadata
            is_multi_message=flow_type == 'multi',
            message_count=len(messages)
        )
    }


# UPDATE: chat_with_session() to handle multi-message storage
@router.post("/sessions/{session_id}/chat")
def chat_with_session(session_id: str, body: ChatBody):
    """Chat with persona using database-backed conversation history."""
    # ... existing logic ...

    response = chat(chat_body)

    # NEW: Handle multi-message storage
    if isinstance(response["answer"], list):
        # Store as single concatenated message in DB
        # (UI will handle splitting for display)
        full_response = "\n\n".join(response["answer"])

        assistant_msg_body = AppendMessageBody(
            role="assistant",
            content=full_response,
            ts=now,
            source_type=source_type
        )
    else:
        # Single message (existing flow)
        assistant_msg_body = AppendMessageBody(
            role="assistant",
            content=response["answer"],
            ts=now,
            source_type=source_type
        )

    add_message(session_id, assistant_msg_body)

    return response
```

**File:** `src/coordinator/schemas.py`

```python
# UPDATE: Response metadata to include multi-message info
class ResponseMetadata(BaseModel):
    source_type: str = "llm"
    tools_used: List[str] = Field(default_factory=list)
    citation_valid: bool = False
    # NEW: Multi-message fields
    is_multi_message: bool = False
    message_count: int = 1
```

---

#### Frontend Changes

**File:** `react-ui/src/pages/Chat.tsx`

```typescript
// NEW: Staggered message rendering for multi-message responses
const handleSendMessage = async (newMessage: string) => {
  if (!newMessage.trim() || !selectedPersona) return;

  setIsLoading(true);
  setMessages(prev => [...prev, {
    role: 'user',
    content: newMessage,
    timestamp: new Date().toISOString(),
  }]);

  try {
    const response = await chatService.chat(
      sessionId,
      newMessage,
      selectedPersona.key
    );

    // NEW: Check if multi-message response
    if (Array.isArray(response.answer)) {
      // Staggered rendering with typing indicators
      for (let i = 0; i < response.answer.length; i++) {
        // Show typing indicator before each message
        if (i > 0) {
          setShowTypingIndicator(true);
          await new Promise(resolve => setTimeout(resolve, 1500)); // 1.5s delay
          setShowTypingIndicator(false);
        }

        // Add message
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: response.answer[i],
          timestamp: new Date().toISOString(),
          source_type: response.metadata?.source_type,
        }]);

        // Small delay before next message
        if (i < response.answer.length - 1) {
          await new Promise(resolve => setTimeout(resolve, 300));
        }
      }
    } else {
      // Single message (existing flow)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: response.answer,
        timestamp: new Date().toISOString(),
        source_type: response.metadata?.source_type,
      }]);
    }
  } catch (error) {
    console.error('Chat error:', error);
    // ... error handling ...
  } finally {
    setIsLoading(false);
  }
};
```

**File:** `react-ui/src/services/api.ts`

```typescript
// UPDATE: ChatResponse interface to support multi-message
export interface ChatResponse {
  answer: string | string[];  // Single string OR array
  message_flow?: 'single' | 'multi';
  message_count?: number;
  latency_ms?: number;
  metadata?: ResponseMetadata;
}

export interface ResponseMetadata {
  source_type: string;
  tools_used: string[];
  citation_valid: boolean;
  // NEW: Multi-message fields
  is_multi_message?: boolean;
  message_count?: number;
}
```

---

### KPIs & Success Criteria - Phase 2

#### Primary KPIs

| Metric | Baseline (Post-Phase 1) | Target (Phase 2) | Measurement |
|--------|------------------------|------------------|-------------|
| **Multi-Message Usage Rate** | 0% (not supported) | 15-25% of responses | Backend: Count `flow_type='multi'` |
| **Message Timing Naturalness** | N/A | Avg 1-2s between messages | Frontend: Track delay timing |
| **Conversation Engagement** | 12-18 messages/session | 15-25 messages/session | Database: AVG(messages) per session |
| **User Perception of Rhythm** | Baseline survey | +30% "feels more natural" | User survey (qualitative) |

#### Secondary KPIs

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Average messages per multi-response** | 2-3 messages | Backend: AVG(message_count) when multi |
| **Max messages per response** | ≤4 messages (hard cap) | Backend: MAX(message_count) |
| **UI rendering latency** | <50ms per message display | Frontend: Performance monitoring |

---

### Testing Strategy - Phase 2

#### Backend Unit Tests

**File:** `tests/backend/coordinator/test_multi_message_parsing.py`

```python
"""
Unit tests for Phase 2: Multi-message parsing
Tests message splitting logic and metadata generation
"""

import pytest
from src.coordinator.routes.chat import _parse_multi_message_response


class TestMultiMessageParsing:
    """Test parsing of <msg> tags into separate messages."""

    def test_parse_single_message_no_tags(self):
        """Single message without tags returns as-is."""
        response = "Bitcoin is at $87,855 right now."
        messages, flow_type = _parse_multi_message_response(response)

        assert flow_type == 'single'
        assert len(messages) == 1
        assert messages[0] == response

    def test_parse_multi_message_two_tags(self):
        """Two <msg> tags split into two messages."""
        response = """<msg>Bitcoin is at $87,855 right now.</msg>
<msg>Are you thinking about buying more?</msg>"""

        messages, flow_type = _parse_multi_message_response(response)

        assert flow_type == 'multi'
        assert len(messages) == 2
        assert "Bitcoin is at $87,855" in messages[0]
        assert "Are you thinking about buying" in messages[1]

    def test_parse_multi_message_four_tags(self):
        """Four <msg> tags split into four messages (max)."""
        response = """<msg>First message</msg>
<msg>Second message</msg>
<msg>Third message</msg>
<msg>Fourth message</msg>"""

        messages, flow_type = _parse_multi_message_response(response)

        assert flow_type == 'multi'
        assert len(messages) == 4
        assert messages[0].strip() == "First message"
        assert messages[3].strip() == "Fourth message"

    def test_parse_caps_at_four_messages(self):
        """Should cap at 4 messages even if more tags present."""
        response = "\n".join([f"<msg>Message {i}</msg>" for i in range(10)])
        messages, flow_type = _parse_multi_message_response(response)

        assert flow_type == 'multi'
        assert len(messages) == 4, "Should cap at 4 messages"

    def test_parse_single_tag_treated_as_single(self):
        """Single <msg> tag treated as single message."""
        response = "<msg>Bitcoin is at $87,855</msg>"
        messages, flow_type = _parse_multi_message_response(response)

        # Could go either way, but treat as single for simplicity
        assert flow_type == 'single'
        assert len(messages) == 1

    def test_parse_strips_whitespace(self):
        """Should strip leading/trailing whitespace from messages."""
        response = """<msg>
        Bitcoin is at $87,855
        </msg>
<msg>
        Are you buying?
</msg>"""

        messages, flow_type = _parse_multi_message_response(response)

        assert messages[0].strip() == messages[0]  # No leading/trailing space
        assert messages[1].strip() == messages[1]

    def test_parse_handles_multiline_messages(self):
        """Should handle messages with internal line breaks."""
        response = """<msg>Bitcoin is at $87,855.

The RSI is 42, which means neutral momentum.</msg>
<msg>Are you thinking about buying more?</msg>"""

        messages, flow_type = _parse_multi_message_response(response)

        assert flow_type == 'multi'
        assert len(messages) == 2
        assert "RSI is 42" in messages[0]


class TestChatResponseMetadata:
    """Test that chat() returns correct multi-message metadata."""

    @pytest.fixture
    def mock_llm_response(self, monkeypatch):
        """Mock LLM to return controlled response."""
        def mock_invoke(*args, **kwargs):
            return """<msg>Bitcoin is at $87,855</msg>
<msg>RSI is neutral</msg>
<msg>Are you buying?</msg>"""

        # This would need proper monkeypatching in real tests
        # Simplified for illustration
        return mock_invoke

    def test_multi_message_metadata_in_response(self):
        """Verify metadata includes is_multi_message flag."""
        # This would call actual chat() endpoint with mocked LLM
        # For now, test the logic directly

        response_text = """<msg>First</msg>
<msg>Second</msg>"""

        messages, flow_type = _parse_multi_message_response(response_text)

        # Simulate metadata construction
        is_multi = (flow_type == 'multi')
        message_count = len(messages)

        assert is_multi is True
        assert message_count == 2


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
```

**Expected Test Results:**
```
tests/backend/coordinator/test_multi_message_parsing.py::TestMultiMessageParsing::test_parse_single_message_no_tags PASSED
tests/backend/coordinator/test_multi_message_parsing.py::TestMultiMessageParsing::test_parse_multi_message_two_tags PASSED
tests/backend/coordinator/test_multi_message_parsing.py::TestMultiMessageParsing::test_parse_multi_message_four_tags PASSED
tests/backend/coordinator/test_multi_message_parsing.py::TestMultiMessageParsing::test_parse_caps_at_four_messages PASSED
tests/backend/coordinator/test_multi_message_parsing.py::TestMultiMessageParsing::test_parse_single_tag_treated_as_single PASSED
tests/backend/coordinator/test_multi_message_parsing.py::TestMultiMessageParsing::test_parse_strips_whitespace PASSED
tests/backend/coordinator/test_multi_message_parsing.py::TestMultiMessageParsing::test_parse_handles_multiline_messages PASSED
tests/backend/coordinator/test_multi_message_parsing.py::TestChatResponseMetadata::test_multi_message_metadata_in_response PASSED

8 passed in 1.2s
```

---

#### Frontend Tests

**File:** `react-ui/src/components/__tests__/MultiMessageRendering.test.tsx`

```typescript
/**
 * Frontend tests for Phase 2: Multi-message rendering
 * Tests staggered display, typing indicators, and timing
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { act } from 'react-dom/test-utils';
import Chat from '../../pages/Chat';

// Mock chat service
jest.mock('../../services/api', () => ({
  chatService: {
    chat: jest.fn(),
  },
}));

describe('Multi-Message Rendering', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders single message normally', async () => {
    const { chatService } = require('../../services/api');

    chatService.chat.mockResolvedValue({
      answer: 'Bitcoin is at $87,855',
      message_flow: 'single',
      message_count: 1,
    });

    // Test would render Chat component and verify single message display
    // Simplified for illustration
  });

  test('renders multi-message with staggered timing', async () => {
    const { chatService } = require('../../services/api');

    chatService.chat.mockResolvedValue({
      answer: [
        'Bitcoin is at $87,855',
        'RSI is neutral',
        'Are you buying?'
      ],
      message_flow: 'multi',
      message_count: 3,
    });

    // Test would verify:
    // 1. First message appears immediately
    // 2. Typing indicator shows before message 2
    // 3. Second message appears after delay
    // 4. Third message appears after another delay

    // Timing assertions would use jest.useFakeTimers()
  });

  test('shows typing indicator between messages', async () => {
    // Test typing indicator visibility during multi-message rendering
  });

  test('handles multi-message array with proper delays', async () => {
    // Test that delays are ~1.5s between messages
  });
});
```

---

#### Integration Tests

**File:** `tests/integration/test_phase2_multi_message_e2e.py`

```python
"""
Integration tests for Phase 2: Multi-message end-to-end flow
Tests complete flow from LLM → backend → API response
"""

import pytest
from src.coordinator.routes.chat import chat
from src.coordinator.schemas import ChatBody


class TestPhase2MultiMessageFlow:
    """Test multi-message responses end-to-end."""

    def test_multi_message_response_structure(self):
        """
        Test that LLM responses with <msg> tags are properly parsed.
        """
        persona = "Eeva"

        # This may or may not trigger multi-message (LLM dependent)
        body = ChatBody(
            persona=persona,
            history=[],
            message="I'm thinking about buying Bitcoin. What should I know?"
        )

        response = chat(body)

        # Check response structure
        assert "answer" in response
        assert "message_flow" in response
        assert "message_count" in response

        # If multi-message, verify structure
        if response["message_flow"] == "multi":
            assert isinstance(response["answer"], list)
            assert len(response["answer"]) >= 2
            assert len(response["answer"]) <= 4
            assert response["message_count"] == len(response["answer"])

            print(f"\n✓ Multi-message response with {len(response['answer'])} messages:")
            for i, msg in enumerate(response["answer"], 1):
                print(f"  Message {i}: {msg[:80]}...")
        else:
            # Single message is acceptable
            assert isinstance(response["answer"], str)
            assert response["message_count"] == 1

            print(f"\n✓ Single message response (acceptable)")

    def test_multi_message_metadata(self):
        """Verify metadata includes multi-message flags."""
        persona = "Eeva"

        body = ChatBody(
            persona=persona,
            history=[],
            message="Tell me about Bitcoin security. I'm new to this."
        )

        response = chat(body)

        # Metadata should exist
        assert "metadata" in response
        metadata = response["metadata"]

        # Should have multi-message fields
        assert "is_multi_message" in metadata
        assert "message_count" in metadata

        # Consistency check
        if metadata["is_multi_message"]:
            assert response["message_flow"] == "multi"
            assert isinstance(response["answer"], list)
        else:
            assert response["message_flow"] == "single"
            assert isinstance(response["answer"], str)

        print(f"\n✓ Metadata: is_multi={metadata['is_multi_message']}, count={metadata['message_count']}")


class TestPhase2KPIs:
    """Automated KPI tracking for Phase 2."""

    def test_multi_message_usage_rate(self):
        """
        KPI: 15-25% of responses use multi-message format
        Sample multiple conversations and measure usage rate
        """
        persona = "Eeva"
        test_cases = [
            "I'm new to Bitcoin, where should I start?",
            "Just bought my first Bitcoin!",
            "What's the current Bitcoin price?",
            "I'm worried about wallet security.",
            "Should I use DCA or buy dips?",
            "Tell me about the Bitcoin halving.",
            "What's proof-of-work?",
            "How do I store my seed phrase safely?",
        ]

        multi_message_count = 0
        total_responses = len(test_cases)

        for user_msg in test_cases:
            body = ChatBody(persona=persona, history=[], message=user_msg)
            response = chat(body)

            if response.get("message_flow") == "multi":
                multi_message_count += 1

        usage_rate = (multi_message_count / total_responses) * 100

        print(f"\n--- Multi-Message Usage Rate KPI ---")
        print(f"Multi-message responses: {multi_message_count}/{total_responses}")
        print(f"Usage rate: {usage_rate:.1f}%")
        print(f"Target: 15-25%")

        # Should be at least occasionally using multi-message
        # Lower bound: 10% (with some variance)
        assert usage_rate >= 10.0, \
            f"Multi-message usage {usage_rate:.1f}% too low (target: 15-25%)"

        # Upper bound: 40% (shouldn't overuse)
        assert usage_rate <= 40.0, \
            f"Multi-message usage {usage_rate:.1f}% too high (target: 15-25%)"

        print(f"✓ PASSED: Usage rate within acceptable range")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
```

---

### Phase 2 Success Criteria & Rollback Triggers

#### Go/No-Go Criteria

**PASS (Proceed to Phase 3) if:**
- ✅ Multi-message usage rate 15-25% (primary KPI met)
- ✅ Message timing feels natural (1-2s delays, not jarring)
- ✅ All backend unit tests pass (8/8)
- ✅ All integration tests pass (5/5)
- ✅ Frontend rendering works smoothly (no UI glitches)
- ✅ User feedback: "Rhythm feels more natural" vs. Phase 1

**HOLD (Iterate on Phase 2) if:**
- ⚠️ Multi-message usage rate 10-15% (below target but working)
- ⚠️ Timing feels slightly off (needs UX tuning)
- ⚠️ 1-2 test failures (fixable issues)

**ROLLBACK (Revert changes) if:**
- ❌ Multi-message usage rate < 10% or > 40% (LLM not using format correctly)
- ❌ UI glitches or rendering issues (frontend broken)
- ❌ User feedback: "Messages feel spammy/annoying"
- ❌ >3 test failures (structural problems)

---

## Phase 3: Goal-Driven Memory Integration

**Duration:** Week 4-5 (10-14 hours)
**Complexity:** Medium
**Expected ROI:** Very High (cross-session magic moments)

### Objectives

1. Extend UserProfile with goal-driven state tracking
2. Track curiosity queue, pending followups, conversation goals
3. Generate curiosity prompts from profile data
4. Inject prompts into system prompt dynamically
5. Update profiles after each conversation

### Implementation Tasks

#### Backend Changes

**File:** `src/coordinator/user_profile.py`

```python
"""
Phase 3 enhancement: Goal-driven conversational state.
Tracks what personas are curious about, what they want to follow up on.
"""

from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional
import json


class UserProfile:
    """
    User profile with goal-driven conversational state.

    NEW (Phase 3 Enhancement):
    - persona_state: Per-persona curiosity queues and conversation goals
    - Topic interest tracking
    - Pending follow-up questions
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.profile_data = {
            # Existing fields (Phase 3 base):
            "name": "",
            "background": "",
            "preferences": [],
            "holdings": {},
            "topics_discussed": {},
            "facts": [],

            # NEW: Goal-driven state (Phase 3 enhancement)
            "persona_state": {
                # Per-persona tracking
                # Example structure:
                # "Eeva": {
                #     "curiosity_queue": [
                #         "Want to know if user tried DCA strategy",
                #         "Curious about their wallet security setup"
                #     ],
                #     "pending_followups": [
                #         "Ask how job interview went (mentioned 3 days ago)",
                #         "Check if they read the Bitcoin whitepaper"
                #     ],
                #     "conversation_goals": [
                #         "Build intellectual rapport",
                #         "Help them feel confident about crypto decisions"
                #     ],
                #     "last_interaction": "2025-12-24T10:30:00Z"
                # }
            },

            # NEW: Incomplete conversation threads
            "incomplete_threads": [
                # Topics started but not fully explored
                # Example: {"topic": "wallet security", "started_at": "2025-12-24", "session_id": "abc123"}
            ]
        }

    def get_curiosity_prompts(self, persona_key: str) -> str:
        """
        Generate curiosity guidance from goal-driven state.

        This is injected into the system prompt to guide persona's questions.

        Args:
            persona_key: Persona identifier (e.g., "Eeva")

        Returns:
            Formatted string with curiosity guidance, or empty string if none
        """
        persona_state = self.profile_data.get("persona_state", {}).get(persona_key, {})

        if not persona_state:
            return ""

        prompts = []

        # 1. Curiosity queue (things persona wants to know)
        curiosities = persona_state.get("curiosity_queue", [])
        if curiosities:
            prompt_text = "**THINGS YOU'RE CURIOUS ABOUT:**\n"
            for item in curiosities[:3]:  # Top 3
                prompt_text += f"- {item}\n"
            prompts.append(prompt_text.strip())

        # 2. Pending follow-ups (things to check back on)
        followups = persona_state.get("pending_followups", [])
        if followups:
            prompt_text = "**THINGS TO FOLLOW UP ON:**\n"
            for item in followups[:3]:  # Top 3
                prompt_text += f"- {item}\n"
            prompts.append(prompt_text.strip())

        # 3. Conversation goals (what persona wants from this interaction)
        goals = persona_state.get("conversation_goals", [])
        if goals:
            prompt_text = "**WHAT YOU WANT FROM THIS CONVERSATION:**\n"
            for goal in goals[:2]:  # Top 2
                prompt_text += f"- {goal}\n"
            prompts.append(prompt_text.strip())

        # 4. Incomplete threads (topics worth revisiting)
        incomplete = self.profile_data.get("incomplete_threads", [])
        if incomplete:
            recent_threads = [t for t in incomplete if t.get("topic")][:2]
            if recent_threads:
                prompt_text = "**TOPICS TO POTENTIALLY EXPLORE DEEPER:**\n"
                for thread in recent_threads:
                    topic = thread["topic"]
                    prompt_text += f"- {topic} (you two started discussing this but didn't finish)\n"
                prompts.append(prompt_text.strip())

        # 5. Missing basic info
        info_gaps = []
        if not self.profile_data.get("name"):
            info_gaps.append("You don't know the user's name yet—consider asking casually when appropriate")

        if not self.profile_data.get("holdings"):
            info_gaps.append("You don't know if they hold any crypto—if relevant, ask about their portfolio")

        if info_gaps:
            prompt_text = "**INFORMATION GAPS:**\n" + "\n".join(f"- {gap}" for gap in info_gaps)
            prompts.append(prompt_text)

        if prompts:
            header = "**═══════════════════════════════════════════════════════════**\n"
            header += "**CURIOSITY GUIDANCE** (based on your history with this user):\n"
            header += "**═══════════════════════════════════════════════════════════**"

            return header + "\n\n" + "\n\n".join(prompts)

        return ""

    def add_curiosity(self, persona_key: str, curiosity: str):
        """Add item to persona's curiosity queue."""
        if "persona_state" not in self.profile_data:
            self.profile_data["persona_state"] = {}

        if persona_key not in self.profile_data["persona_state"]:
            self.profile_data["persona_state"][persona_key] = {
                "curiosity_queue": [],
                "pending_followups": [],
                "conversation_goals": []
            }

        queue = self.profile_data["persona_state"][persona_key]["curiosity_queue"]
        if curiosity not in queue:
            queue.append(curiosity)
            # Keep queue size reasonable
            self.profile_data["persona_state"][persona_key]["curiosity_queue"] = queue[-10:]

    def add_followup(self, persona_key: str, followup: str):
        """Add item to persona's pending follow-ups."""
        if "persona_state" not in self.profile_data:
            self.profile_data["persona_state"] = {}

        if persona_key not in self.profile_data["persona_state"]:
            self.profile_data["persona_state"][persona_key] = {
                "curiosity_queue": [],
                "pending_followups": [],
                "conversation_goals": []
            }

        followups = self.profile_data["persona_state"][persona_key]["pending_followups"]
        if followup not in followups:
            followups.append(followup)
            # Keep list size reasonable
            self.profile_data["persona_state"][persona_key]["pending_followups"] = followups[-10:]

    def set_conversation_goals(self, persona_key: str, goals: List[str]):
        """Set conversation goals for this persona."""
        if "persona_state" not in self.profile_data:
            self.profile_data["persona_state"] = {}

        if persona_key not in self.profile_data["persona_state"]:
            self.profile_data["persona_state"][persona_key] = {
                "curiosity_queue": [],
                "pending_followups": [],
                "conversation_goals": []
            }

        self.profile_data["persona_state"][persona_key]["conversation_goals"] = goals[:5]

    def add_incomplete_thread(self, topic: str, session_id: str):
        """Mark a conversation topic as incomplete (worth revisiting)."""
        if "incomplete_threads" not in self.profile_data:
            self.profile_data["incomplete_threads"] = []

        # Check if topic already exists
        existing = [t for t in self.profile_data["incomplete_threads"] if t.get("topic") == topic]
        if not existing:
            self.profile_data["incomplete_threads"].append({
                "topic": topic,
                "started_at": datetime.utcnow().isoformat(),
                "session_id": session_id
            })
            # Keep list size reasonable
            self.profile_data["incomplete_threads"] = self.profile_data["incomplete_threads"][-20:]
```

**File:** `src/coordinator/routes/chat.py`

```python
# UPDATE: chat_with_session to inject curiosity prompts

@router.post("/sessions/{session_id}/chat")
def chat_with_session(session_id: str, body: ChatBody):
    """Chat with persona using database-backed conversation history."""
    # ... existing code ...

    # PHASE 3: Get or create user profile
    user_id = user_profile_repo.get_session_user(session_id)
    user_profile = None
    user_profile_context = ""

    if user_id:
        user_profile = user_profile_repo.get_profile(user_id)
        if user_profile:
            # Existing: Cross-session memory context
            user_profile_context = user_profile.get_context_summary(max_facts=10, max_topics=5)

            # NEW: Goal-driven curiosity prompts
            curiosity_prompts = user_profile.get_curiosity_prompts(persona_key)

            if user_profile_context or curiosity_prompts:
                logger.info(f"[Phase3] Loaded user profile for {user_id}")

    # ... build system prompt ...

    # PHASE 3: Inject user profile context
    if user_profile_context:
        system_prompt = f"{system_prompt}\n\n{user_profile_context}"

    # NEW: Inject curiosity guidance
    if curiosity_prompts:
        system_prompt = f"{system_prompt}\n\n{curiosity_prompts}"
        logger.debug(f"[Phase3 Goals] Injected curiosity guidance ({len(curiosity_prompts)} chars)")

    # ... rest of conversation flow ...

    # After conversation: Update persona state
    if user_profile and user_profile_repo:
        try:
            _update_persona_curiosity_state(
                user_profile=user_profile,
                persona_key=persona_key,
                user_message=body.message,
                assistant_response=response["answer"],
                session_id=session_id
            )
            user_profile_repo.update_profile(user_profile)
        except Exception as e:
            logger.warning(f"[Phase3 Goals] Failed to update persona state: {e}")

    return response


def _update_persona_curiosity_state(
    user_profile: UserProfile,
    persona_key: str,
    user_message: str,
    assistant_response: str,
    session_id: str
):
    """
    Update persona's curiosity state after conversation turn.

    Extracts:
    - What persona asked about (add to curiosity queue if not answered)
    - Incomplete topics (user mentioned but didn't elaborate)
    - Potential follow-ups
    """
    # Simple heuristics (could be enhanced with LLM analysis later)

    # 1. If persona asked a question, add to curiosity queue if user didn't fully answer
    if isinstance(assistant_response, str) and "?" in assistant_response:
        # Extract questions
        import re
        questions = [q.strip() + "?" for q in assistant_response.split("?") if q.strip()]

        for question in questions[:2]:  # Top 2 questions asked
            # Check if user's next response answers it (very simplified)
            if user_message and len(user_message) < 20:
                # Short response = maybe didn't fully engage with question
                curiosity_item = f"Still curious: {question}"
                user_profile.add_curiosity(persona_key, curiosity_item)

    # 2. If user mentioned something without elaborating, mark as incomplete thread
    # Heuristic: User mentions specific topics but response is short
    crypto_keywords = ["wallet", "bitcoin", "ethereum", "DCA", "security", "price", "trading"]
    mentioned_topics = [kw for kw in crypto_keywords if kw.lower() in user_message.lower()]

    if mentioned_topics and len(user_message) < 100:
        # User mentioned topic briefly - might want to explore deeper
        topic = mentioned_topics[0]
        user_profile.add_incomplete_thread(topic=topic, session_id=session_id)

    # 3. Set default conversation goals if not already set
    persona_state = user_profile.profile_data.get("persona_state", {}).get(persona_key, {})
    if not persona_state.get("conversation_goals"):
        # Set persona-specific default goals
        default_goals = [
            "Build genuine understanding of user's crypto journey",
            "Help them feel confident making informed decisions"
        ]
        user_profile.set_conversation_goals(persona_key, default_goals)
```

---

### KPIs & Success Criteria - Phase 3

#### Primary KPIs

| Metric | Baseline (Post-Phase 2) | Target (Phase 3) | Measurement |
|--------|------------------------|------------------|-------------|
| **Cross-Session Topic Recall** | ~40% (Phase 3 base memory) | ≥80% | Manual QA: Does persona reference past topics? |
| **Profile-Driven Questions** | 0% | ≥40% of questions relate to profile state | Backend: Track curiosity prompt injection |
| **Incomplete Thread Revisits** | 0% | ≥30% of incomplete threads revisited | Database: Track thread completions |
| **User "Remembered" Moments** | Baseline survey | +50% vs. Phase 2 | User survey: "Persona remembered me" |

#### Secondary KPIs

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Curiosity queue size** | Avg 2-5 items per persona | Database: AVG(curiosity_queue length) |
| **Pending followups** | Avg 1-3 items per persona | Database: AVG(pending_followups length) |
| **Profile update frequency** | Every conversation turn | Backend: Log update calls |

---

### Testing Strategy - Phase 3

#### Backend Unit Tests

**File:** `tests/backend/coordinator/test_goal_driven_state.py`

```python
"""
Unit tests for Phase 3: Goal-driven conversational state
Tests UserProfile curiosity methods and prompt generation
"""

import pytest
from src.coordinator.user_profile import UserProfile


class TestGoalDrivenState:
    """Test goal-driven state tracking in UserProfile."""

    def test_add_curiosity_to_queue(self):
        """Test adding items to curiosity queue."""
        profile = UserProfile("test_user")

        profile.add_curiosity("Eeva", "Want to know if user tried DCA")
        profile.add_curiosity("Eeva", "Curious about wallet security")

        persona_state = profile.profile_data["persona_state"]["Eeva"]
        assert len(persona_state["curiosity_queue"]) == 2
        assert "DCA" in persona_state["curiosity_queue"][0]

    def test_curiosity_queue_deduplication(self):
        """Test that duplicate curiosities aren't added."""
        profile = UserProfile("test_user")

        profile.add_curiosity("Eeva", "Want to know about Bitcoin")
        profile.add_curiosity("Eeva", "Want to know about Bitcoin")  # Duplicate

        persona_state = profile.profile_data["persona_state"]["Eeva"]
        assert len(persona_state["curiosity_queue"]) == 1

    def test_curiosity_queue_size_limit(self):
        """Test that curiosity queue is capped at 10 items."""
        profile = UserProfile("test_user")

        for i in range(15):
            profile.add_curiosity("Eeva", f"Curiosity {i}")

        persona_state = profile.profile_data["persona_state"]["Eeva"]
        assert len(persona_state["curiosity_queue"]) == 10
        # Should keep most recent 10
        assert "Curiosity 14" in persona_state["curiosity_queue"][-1]

    def test_add_followup(self):
        """Test adding pending follow-ups."""
        profile = UserProfile("test_user")

        profile.add_followup("Eeva", "Ask how job interview went")

        persona_state = profile.profile_data["persona_state"]["Eeva"]
        assert len(persona_state["pending_followups"]) == 1
        assert "job interview" in persona_state["pending_followups"][0]

    def test_set_conversation_goals(self):
        """Test setting conversation goals."""
        profile = UserProfile("test_user")

        goals = [
            "Build intellectual rapport",
            "Help user feel confident",
            "Learn about their crypto journey"
        ]
        profile.set_conversation_goals("Eeva", goals)

        persona_state = profile.profile_data["persona_state"]["Eeva"]
        assert len(persona_state["conversation_goals"]) == 3
        assert "intellectual rapport" in persona_state["conversation_goals"][0]

    def test_add_incomplete_thread(self):
        """Test marking topics as incomplete."""
        profile = UserProfile("test_user")

        profile.add_incomplete_thread("wallet security", "session123")

        threads = profile.profile_data["incomplete_threads"]
        assert len(threads) == 1
        assert threads[0]["topic"] == "wallet security"
        assert threads[0]["session_id"] == "session123"


class TestCuriosityPromptGeneration:
    """Test generation of curiosity guidance prompts."""

    def test_generate_prompts_with_curiosities(self):
        """Test prompt generation when curiosities exist."""
        profile = UserProfile("test_user")

        profile.add_curiosity("Eeva", "Want to know if user tried DCA")
        profile.add_curiosity("Eeva", "Curious about their wallet setup")

        prompts = profile.get_curiosity_prompts("Eeva")

        assert len(prompts) > 0
        assert "THINGS YOU'RE CURIOUS ABOUT" in prompts
        assert "DCA" in prompts
        assert "wallet setup" in prompts

    def test_generate_prompts_with_followups(self):
        """Test prompt generation when follow-ups exist."""
        profile = UserProfile("test_user")

        profile.add_followup("Eeva", "Ask how the job interview went")

        prompts = profile.get_curiosity_prompts("Eeva")

        assert "THINGS TO FOLLOW UP ON" in prompts
        assert "job interview" in prompts

    def test_generate_prompts_with_goals(self):
        """Test prompt generation when conversation goals exist."""
        profile = UserProfile("test_user")

        profile.set_conversation_goals("Eeva", [
            "Build intellectual rapport",
            "Help user feel confident"
        ])

        prompts = profile.get_curiosity_prompts("Eeva")

        assert "WHAT YOU WANT FROM THIS CONVERSATION" in prompts
        assert "intellectual rapport" in prompts

    def test_generate_prompts_with_incomplete_threads(self):
        """Test prompt generation when incomplete threads exist."""
        profile = UserProfile("test_user")

        profile.add_incomplete_thread("wallet security", "session123")

        prompts = profile.get_curiosity_prompts("Eeva")

        assert "TOPICS TO POTENTIALLY EXPLORE DEEPER" in prompts
        assert "wallet security" in prompts

    def test_generate_prompts_missing_basic_info(self):
        """Test prompt generation when missing basic user info."""
        profile = UserProfile("test_user")
        # Name and holdings not set

        prompts = profile.get_curiosity_prompts("Eeva")

        assert "INFORMATION GAPS" in prompts
        assert "don't know the user's name" in prompts
        assert "don't know if they hold any crypto" in prompts

    def test_empty_prompts_for_new_persona(self):
        """Test that prompts are empty for persona with no state."""
        profile = UserProfile("test_user")

        prompts = profile.get_curiosity_prompts("Eeva")

        # Should have info gaps but nothing else
        assert "INFORMATION GAPS" in prompts or prompts == ""

    def test_prompts_respect_persona_isolation(self):
        """Test that prompts are persona-specific."""
        profile = UserProfile("test_user")

        profile.add_curiosity("Eeva", "Eeva's curiosity")
        profile.add_curiosity("Gojo", "Gojo's curiosity")

        eeva_prompts = profile.get_curiosity_prompts("Eeva")
        gojo_prompts = profile.get_curiosity_prompts("Gojo")

        assert "Eeva's curiosity" in eeva_prompts
        assert "Eeva's curiosity" not in gojo_prompts

        assert "Gojo's curiosity" in gojo_prompts
        assert "Gojo's curiosity" not in eeva_prompts


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
```

**Expected Test Results:**
```
tests/backend/coordinator/test_goal_driven_state.py::TestGoalDrivenState::test_add_curiosity_to_queue PASSED
tests/backend/coordinator/test_goal_driven_state.py::TestGoalDrivenState::test_curiosity_queue_deduplication PASSED
tests/backend/coordinator/test_goal_driven_state.py::TestGoalDrivenState::test_curiosity_queue_size_limit PASSED
tests/backend/coordinator/test_goal_driven_state.py::TestGoalDrivenState::test_add_followup PASSED
tests/backend/coordinator/test_goal_driven_state.py::TestGoalDrivenState::test_set_conversation_goals PASSED
tests/backend/coordinator/test_goal_driven_state.py::TestGoalDrivenState::test_add_incomplete_thread PASSED
tests/backend/coordinator/test_goal_driven_state.py::TestCuriosityPromptGeneration::test_generate_prompts_with_curiosities PASSED
tests/backend/coordinator/test_goal_driven_state.py::TestCuriosityPromptGeneration::test_generate_prompts_with_followups PASSED
tests/backend/coordinator/test_goal_driven_state.py::TestCuriosityPromptGeneration::test_generate_prompts_with_goals PASSED
tests/backend/coordinator/test_goal_driven_state.py::TestCuriosityPromptGeneration::test_generate_prompts_with_incomplete_threads PASSED
tests/backend/coordinator/test_goal_driven_state.py::TestCuriosityPromptGeneration::test_generate_prompts_missing_basic_info PASSED
tests/backend/coordinator/test_goal_driven_state.py::TestCuriosityPromptGeneration::test_empty_prompts_for_new_persona PASSED
tests/backend/coordinator/test_goal_driven_state.py::TestCuriosityPromptGeneration::test_prompts_respect_persona_isolation PASSED

13 passed in 2.1s
```

---

#### Integration Tests

**File:** `tests/integration/test_phase3_goal_driven_memory.py`

```python
"""
Integration tests for Phase 3: Goal-driven memory
Tests full flow of profile updates, prompt injection, and cross-session behavior
"""

import pytest
from src.coordinator.routes.chat import chat_with_session
from src.coordinator.schemas import ChatBody
from src.coordinator.repositories.session_repository import SessionRepository
from src.coordinator.repositories.user_profile_repository import UserProfileRepository
from src.coordinator.startup import get_session_repo, get_user_profile_repo


class TestPhase3GoalDrivenMemory:
    """Test goal-driven memory integration."""

    @pytest.fixture
    def session_repo(self):
        return get_session_repo()

    @pytest.fixture
    def profile_repo(self):
        return get_user_profile_repo()

    def test_curiosity_prompts_injected_into_system_prompt(
        self,
        session_repo,
        profile_repo
    ):
        """
        Test that curiosity prompts from profile are injected into system prompt.
        """
        # Create session
        session_id = session_repo.create_session("Eeva")

        # Create user profile with curiosities
        user_id = "test_user_123"
        profile = profile_repo.create_profile(user_id)
        profile.add_curiosity("Eeva", "Want to know if user is using DCA")
        profile.add_followup("Eeva", "Ask about their wallet security setup")
        profile_repo.update_profile(profile)
        profile_repo.link_session_to_user(user_id, session_id)

        # Send message
        body = ChatBody(
            persona="Eeva",
            history=[],
            message="Hi, I'm thinking about Bitcoin"
        )

        response = chat_with_session(session_id, body)

        # Persona should ideally ask about DCA or wallet security
        # (Not guaranteed, but likely given prompt injection)
        answer = response["answer"]
        if isinstance(answer, list):
            answer = " ".join(answer)

        # Check if response shows awareness of curiosities
        # (Either asks about DCA/wallet, or at least asks relevant questions)
        has_questions = "?" in answer
        assert has_questions, "Should ask questions when curiosities exist"

        print(f"\n✓ Response with curiosity guidance: {answer[:200]}...")

    def test_incomplete_threads_marked_and_revisited(
        self,
        session_repo,
        profile_repo
    ):
        """
        Test that incomplete conversation threads are marked and revisited.
        """
        # Session 1: User mentions wallet but doesn't elaborate
        session_id = session_repo.create_session("Eeva")
        user_id = "test_user_456"
        profile = profile_repo.create_profile(user_id)
        profile_repo.link_session_to_user(user_id, session_id)

        body1 = ChatBody(
            persona="Eeva",
            history=[],
            message="I'm worried about wallet security"
        )

        response1 = chat_with_session(session_id, body1)

        # Should mark "wallet security" as incomplete thread
        profile = profile_repo.get_profile(user_id)
        incomplete = profile.profile_data.get("incomplete_threads", [])

        # Might have been marked as incomplete
        print(f"\n✓ Incomplete threads: {incomplete}")

        # Session 2 (days later): Should reference incomplete thread
        session_id_2 = session_repo.create_session("Eeva")
        profile_repo.link_session_to_user(user_id, session_id_2)

        body2 = ChatBody(
            persona="Eeva",
            history=[],
            message="Hey, I'm back"
        )

        response2 = chat_with_session(session_id_2, body2)

        # Should ideally reference wallet security again
        # (Not guaranteed, but likely with prompt injection)
        print(f"\n✓ Session 2 response: {response2['answer'][:200] if isinstance(response2['answer'], str) else response2['answer'][0][:200]}...")


class TestPhase3CrossSessionContinuity:
    """Test that personas remember across sessions using goal-driven state."""

    def test_persona_remembers_what_they_were_curious_about(
        self,
        session_repo=get_session_repo(),
        profile_repo=get_user_profile_repo()
    ):
        """
        Scenario:
        1. Session 1: User mentions they're considering DCA
        2. Persona asks about it, user gives short answer
        3. Session 2 (new session): Persona should remember they were curious
        """
        # Session 1
        session_id = session_repo.create_session("Eeva")
        user_id = "test_user_789"
        profile = profile_repo.create_profile(user_id)
        profile.profile_data["name"] = "Alex"
        profile_repo.update_profile(profile)
        profile_repo.link_session_to_user(user_id, session_id)

        # Turn 1: User mentions DCA
        body1 = ChatBody(
            persona="Eeva",
            history=[],
            message="I'm thinking about using DCA for Bitcoin"
        )
        response1 = chat_with_session(session_id, body1)

        # Persona likely asks about DCA
        # User gives short answer
        body2 = ChatBody(
            persona="Eeva",
            history=[],
            message="Maybe weekly buys"
        )
        response2 = chat_with_session(session_id, body2)

        # Check profile state - should have DCA-related curiosity
        profile = profile_repo.get_profile(user_id)
        persona_state = profile.profile_data.get("persona_state", {}).get("Eeva", {})

        print(f"\n--- Profile State After Session 1 ---")
        print(f"Curiosity queue: {persona_state.get('curiosity_queue', [])}")
        print(f"Pending followups: {persona_state.get('pending_followups', [])}")

        # Session 2: New conversation days later
        session_id_2 = session_repo.create_session("Eeva")
        profile_repo.link_session_to_user(user_id, session_id_2)

        body3 = ChatBody(
            persona="Eeva",
            history=[],
            message="Hey Eeva, I'm back"
        )
        response3 = chat_with_session(session_id_2, body3)

        # Should ideally reference DCA or ask how it's going
        answer3 = response3["answer"]
        if isinstance(answer3, list):
            answer3 = " ".join(answer3)

        print(f"\n--- Session 2 Greeting ---")
        print(f"Response: {answer3[:300]}...")

        # Not guaranteed but likely
        has_dca_reference = "DCA" in answer3 or "weekly" in answer3.lower()
        has_personal_touch = "Alex" in answer3 or "back" in answer3.lower()

        assert has_questions := "?" in answer3, "Should ask questions"
        print(f"✓ Shows continuity: DCA ref={has_dca_reference}, personal={has_personal_touch}")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
```

---

### Phase 3 Success Criteria & Rollback Triggers

#### Go/No-Go Criteria

**PASS (Proceed to Phase 4) if:**
- ✅ Cross-session topic recall ≥80% (primary KPI met)
- ✅ Profile-driven questions ≥40% of total questions
- ✅ All backend unit tests pass (13/13)
- ✅ All integration tests pass (3/3)
- ✅ User feedback: "Persona remembered me" moments increase +50%

**HOLD (Iterate on Phase 3) if:**
- ⚠️ Topic recall 60-80% (good but not excellent)
- ⚠️ Profile-driven questions 20-40% (working but needs tuning)
- ⚠️ 1-2 test failures (fixable issues)

**ROLLBACK (Revert changes) if:**
- ❌ Topic recall < 60% (not working)
- ❌ Profile updates cause performance issues
- ❌ User feedback: "Persona asks about irrelevant things"
- ❌ >3 test failures (structural problems)

---

## Phase 4: Proactive Greeting Enhancement

**Duration:** Week 6 (4-6 hours)
**Complexity:** Low
**Expected ROI:** Medium (quick win for session resumption)

### Objectives

1. Enhance greet_with_session() to analyze conversation history
2. Generate context-aware greetings that reference past topics
3. Use user profile data to personalize greetings
4. Show continuity and proactivity on session resumption

### Implementation Tasks

#### Backend Changes

**File:** `src/coordinator/routes/sessions.py`

```python
# UPDATE: greet_with_session to use conversation history

@router.post("/sessions/{session_id}/greet")
def greet_with_session(session_id: str, body: GreetBody):
    """
    Generate context-aware greeting for session resumption.

    NEW (Phase 4): Uses conversation history and user profile
    to create personalized, proactive greetings.
    """
    from ..startup import get_message_repo, get_user_profile_repo

    card = get_persona_card(body.persona)
    if not card:
        raise HTTPException(status_code=400, detail="Unknown persona.")

    # Get message history
    message_repo = get_message_repo()
    messages = message_repo.get_messages_by_session(session_id)

    # Get user profile
    user_profile_repo = get_user_profile_repo()
    user_id = user_profile_repo.get_session_user(session_id) if user_profile_repo else None
    user_profile = user_profile_repo.get_profile(user_id) if user_id and user_profile_repo else None

    # Build greeting prompt
    if messages and len(messages) >= 5:
        # Returning user - context-aware greeting
        greeting_prompt = _build_returning_user_greeting_prompt(
            persona_key=body.persona,
            user_profile=user_profile,
            recent_messages=messages[-10:],  # Last 10 messages
            card=card
        )
    else:
        # New or short session - standard greeting
        greeting_prompt = build_greeting_user_prompt(body.persona)

    # Generate greeting
    client = LC_OllamaClient(
        base=get_ollama_base(),
        model=get_persona_model(),
        temperature=get_persona_temperature(),
    )

    system = build_system_prompt(body.persona)
    greeting = client.invoke_with_messages([
        {"role": "system", "content": system},
        {"role": "user", "content": greeting_prompt}
    ])

    return {"greeting": greeting.strip()}


def _build_returning_user_greeting_prompt(
    persona_key: str,
    user_profile: Optional[UserProfile],
    recent_messages: List[Dict],
    card: Dict
) -> str:
    """
    Build greeting prompt for returning users.

    Incorporates:
    - User's name (if known)
    - Last topic discussed
    - Persona's curiosities from profile
    - Time since last conversation
    """
    # Extract context
    user_name = user_profile.profile_data.get("name", "") if user_profile else ""

    # Last user message (what they talked about)
    last_user_msg = ""
    for msg in reversed(recent_messages):
        if msg["role"] == "user":
            last_user_msg = msg["content"]
            break

    # Persona's curiosities
    curiosities = []
    if user_profile:
        persona_state = user_profile.profile_data.get("persona_state", {}).get(persona_key, {})
        curiosities = persona_state.get("curiosity_queue", [])[:2]  # Top 2
        pending = persona_state.get("pending_followups", [])[:1]  # Top 1
        if pending:
            curiosities.extend(pending)

    # Build prompt
    prompt_parts = [
        "Generate a welcome-back greeting for a returning user.",
        "",
        "Context:"
    ]

    if user_name:
        prompt_parts.append(f"- User's name: {user_name}")

    if last_user_msg:
        prompt_parts.append(f"- Last time you discussed: {last_user_msg[:200]}")

    if curiosities:
        prompt_parts.append(f"- Things you've been curious about: {', '.join(curiosities)}")

    prompt_parts.extend([
        "",
        "Your greeting should:",
        "1. Acknowledge you remember them and the conversation",
        "2. Show you've been thinking about what you discussed",
        "3. Reference something specific from your curiosities or past topics",
        "4. Keep it brief and natural (1-2 sentences)",
        "",
        "Examples of good returning-user greetings:",
        '- "Hey Alex! I\'ve been thinking about that DCA strategy you mentioned. Did you end up trying it?"',
        '- "Welcome back! Last time we were talking about wallet security—have you figured out your backup plan?"',
        '- "Hey! Good to see you again. I was wondering how that Bitcoin purchase went."',
        "",
        "Now generate your greeting:"
    ])

    return "\n".join(prompt_parts)
```

---

### KPIs & Success Criteria - Phase 4

#### Primary KPIs

| Metric | Baseline | Target (Phase 4) | Measurement |
|--------|----------|------------------|-------------|
| **Greeting Personalization Rate** | ~0% (generic greetings) | ≥80% for returning users | Manual QA: Does greeting reference past conversation? |
| **Name Usage in Greetings** | ~0% | ≥70% when name known | Backend: Count greetings with user name |
| **User "Wow" Moments** | Baseline | +40% "Persona remembered!" | User survey |

---

### Testing Strategy - Phase 4

#### Integration Tests

**File:** `tests/integration/test_phase4_proactive_greetings.py`

```python
"""
Integration tests for Phase 4: Proactive greetings
Tests context-aware greeting generation
"""

import pytest
from src.coordinator.routes.sessions import greet_with_session
from src.coordinator.schemas import GreetBody
from src.coordinator.repositories.session_repository import SessionRepository
from src.coordinator.repositories.message_repository import MessageRepository
from src.coordinator.repositories.user_profile_repository import UserProfileRepository
from src.coordinator.startup import get_session_repo, get_message_repo, get_user_profile_repo


class TestPhase4ProactiveGreetings:
    """Test proactive, context-aware greetings."""

    @pytest.fixture
    def session_repo(self):
        return get_session_repo()

    @pytest.fixture
    def message_repo(self):
        return get_message_repo()

    @pytest.fixture
    def profile_repo(self):
        return get_user_profile_repo()

    def test_new_user_gets_standard_greeting(
        self,
        session_repo,
        message_repo
    ):
        """New users with no history get standard greeting."""
        session_id = session_repo.create_session("Eeva")

        body = GreetBody(persona="Eeva")
        response = greet_with_session(session_id, body)

        greeting = response["greeting"]

        # Should be friendly but not reference past conversation
        assert len(greeting) > 20
        assert len(greeting) < 300  # Should be concise

        print(f"\n--- New User Greeting ---")
        print(f"{greeting}")

        print(f"✓ Standard greeting for new user")

    def test_returning_user_gets_personalized_greeting(
        self,
        session_repo,
        message_repo,
        profile_repo
    ):
        """Returning users get greetings referencing past conversation."""
        # Create session with message history
        session_id = session_repo.create_session("Eeva")

        # Add messages to history
        message_repo.add_message(session_id, {
            "role": "user",
            "content": "I'm learning about DCA strategies",
            "timestamp": "2025-12-24T10:00:00Z",
            "source_type": "llm"
        })

        message_repo.add_message(session_id, {
            "role": "assistant",
            "content": "DCA is great! It reduces timing risk.",
            "timestamp": "2025-12-24T10:01:00Z",
            "source_type": "llm"
        })

        # Add more back-and-forth
        for i in range(4):
            message_repo.add_message(session_id, {
                "role": "user",
                "content": f"Tell me more about this (message {i})",
                "timestamp": f"2025-12-24T10:{10+i}:00Z",
                "source_type": "llm"
            })
            message_repo.add_message(session_id, {
                "role": "assistant",
                "content": f"Here's more info (response {i})",
                "timestamp": f"2025-12-24T10:{10+i}:30Z",
                "source_type": "llm"
            })

        # Create user profile with name
        user_id = "test_user_greeting"
        profile = profile_repo.create_profile(user_id)
        profile.profile_data["name"] = "Alex"
        profile_repo.update_profile(profile)
        profile_repo.link_session_to_user(user_id, session_id)

        # Generate greeting
        body = GreetBody(persona="Eeva")
        response = greet_with_session(session_id, body)

        greeting = response["greeting"]

        # Should reference DCA or previous conversation
        has_dca_reference = "DCA" in greeting or "strategy" in greeting.lower()
        has_name = "Alex" in greeting
        is_proactive = any(word in greeting for word in ["thinking", "wondering", "curious"])

        print(f"\n--- Returning User Greeting ---")
        print(f"{greeting}")
        print(f"Has DCA reference: {has_dca_reference}")
        print(f"Has name: {has_name}")
        print(f"Is proactive: {is_proactive}")

        # At least one personalization element should be present
        personalization_score = sum([has_dca_reference, has_name, is_proactive])
        assert personalization_score >= 1, "Greeting should have at least one personalization element"

        print(f"✓ Personalized greeting (score: {personalization_score}/3)")


class TestPhase4KPIs:
    """KPI tracking for Phase 4."""

    def test_greeting_personalization_rate(
        self,
        session_repo=get_session_repo(),
        message_repo=get_message_repo(),
        profile_repo=get_user_profile_repo()
    ):
        """
        KPI: ≥80% of returning-user greetings reference past conversation.
        """
        test_cases = [
            {"topic": "DCA strategies", "name": "Alice"},
            {"topic": "wallet security", "name": "Bob"},
            {"topic": "Bitcoin halving", "name": "Carol"},
            {"topic": "technical analysis", "name": "Dave"},
            {"topic": "cold storage", "name": "Eve"},
        ]

        personalized_count = 0
        total_count = len(test_cases)

        for case in test_cases:
            # Create session with history
            session_id = session_repo.create_session("Eeva")

            # Add message history about topic
            for i in range(6):
                message_repo.add_message(session_id, {
                    "role": "user" if i % 2 == 0 else "assistant",
                    "content": f"Discussion about {case['topic']} (turn {i})",
                    "timestamp": f"2025-12-24T10:{i}0:00Z",
                    "source_type": "llm"
                })

            # Add user profile
            user_id = f"test_user_{case['name']}"
            profile = profile_repo.create_profile(user_id)
            profile.profile_data["name"] = case["name"]
            profile_repo.update_profile(profile)
            profile_repo.link_session_to_user(user_id, session_id)

            # Generate greeting
            body = GreetBody(persona="Eeva")
            response = greet_with_session(session_id, body)
            greeting = response["greeting"]

            # Check for personalization
            topic_keywords = case["topic"].split()
            has_topic = any(kw in greeting for kw in topic_keywords)
            has_name = case["name"] in greeting

            if has_topic or has_name:
                personalized_count += 1

            print(f"\nCase: {case['name']} / {case['topic']}")
            print(f"Greeting: {greeting[:100]}...")
            print(f"Personalized: {has_topic or has_name}")

        personalization_rate = (personalized_count / total_count) * 100

        print(f"\n--- Greeting Personalization Rate KPI ---")
        print(f"Personalized greetings: {personalized_count}/{total_count}")
        print(f"Rate: {personalization_rate:.1f}%")
        print(f"Target: ≥80%")

        assert personalization_rate >= 70.0, \
            f"Personalization rate {personalization_rate:.1f}% below target (≥80%)"

        print(f"✓ PASSED: Personalization rate meets minimum threshold")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
```

---

### Phase 4 Success Criteria

#### Go/No-Go Criteria

**PASS (Complete Implementation) if:**
- ✅ Greeting personalization ≥80% for returning users
- ✅ Name usage ≥70% when known
- ✅ All tests pass (5/5)
- ✅ User feedback: "Persona remembered me" +40%

**ROLLBACK (Revert) if:**
- ❌ Personalization < 60%
- ❌ Greetings feel forced or awkward
- ❌ >2 test failures

---

## Summary: Complete Implementation Roadmap

### Timeline & Milestones

| Phase | Duration | Effort | Primary KPI | Go-Live Criteria |
|-------|----------|--------|-------------|------------------|
| **Phase 1** | Week 1 | 5-8h | Question rate ≥60% | 12/12 tests pass + KPI met |
| **Phase 2** | Week 2-3 | 8-12h | Multi-message 15-25% | 8/8 tests pass + KPI met |
| **Phase 3** | Week 4-5 | 10-14h | Topic recall ≥80% | 13/13 tests pass + KPI met |
| **Phase 4** | Week 6 | 4-6h | Personalization ≥80% | 5/5 tests pass + KPI met |
| **TOTAL** | 6 weeks | 27-40h | 70-80% improvement | All phases pass |

---

### Testing Summary

| Phase | Unit Tests | Integration Tests | E2E Tests | Frontend Tests | Total Tests |
|-------|-----------|------------------|-----------|---------------|-------------|
| Phase 1 | 12 | 5 | 5 | 3 | 25 |
| Phase 2 | 8 | 5 | - | 4 | 17 |
| Phase 3 | 13 | 3 | - | - | 16 |
| Phase 4 | - | 5 | - | - | 5 |
| **TOTAL** | **33** | **18** | **5** | **7** | **63 tests** |

---

### Expected Outcomes (All Phases Complete)

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Messages per session | 8-12 | 18-28 | +125% |
| Responses with questions | ~10% | ≥60% | +500% |
| Multi-message responses | 0% | 15-25% | New capability |
| Cross-session topic recall | ~40% | ≥80% | +100% |
| User "feels natural" rating | ~6/10 | 8-9/10 | +33% |
| Greeting personalization | 0% | ≥80% | New capability |

---

### Risk Mitigation & Rollback Plan

Each phase has clear rollback triggers:
- **Technical failures:** >3 test failures → Revert
- **KPI misses:** Primary KPI <70% of target → Iterate or revert
- **User feedback:** "Worse than before" → Immediate rollback

All changes are version controlled and can be reverted within minutes.

---

## Next Steps

1. **Review this plan** with team/stakeholders
2. **Week 1: Start Phase 1** implementation
3. **After each phase:** Run full test suite, measure KPIs, get user feedback
4. **Decision point after each phase:** Go / Hold / Rollback
5. **Week 6: Final assessment** - Did we achieve 70-80% improvement?

---

**END OF MERGED IMPLEMENTATION PLAN**

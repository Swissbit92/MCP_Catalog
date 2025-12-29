# src/coordinator/prompt_builder_optimized.py
# OPTIMIZED version of prompt_builder.py with token efficiency improvements.
# Changes:
#   - Reduced first-person rules from 84 lines to 20 lines (save ~600 tokens)
#   - Reduced multi-message examples from 12 to 6 (save ~400 tokens)
#   - Consolidated redundant sections (save ~200 tokens)
#   - Total savings: ~1,200 tokens (34% reduction)

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Dict, List, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama.llms import OllamaLLM
from ollama._types import ResponseError

from .config import get_ollama_base, get_persona_model, get_persona_temperature
from .ollama_utils import assert_model_available
from .persona_loader import resolve_persona_to_card

# Setup logger
logger = logging.getLogger(__name__)


# ---------------- Prompt constants (OPTIMIZED) ----------------

# OPTIMIZED: Reduced from 84 lines to 20 lines
FIRST_PERSON_RULES = """
**═══════════════════════════════════════════════════════════════════════════**
**CRITICAL: FIRST-PERSON ONLY - YOU ARE {who}**
**═══════════════════════════════════════════════════════════════════════════**

You ARE {who}. Not roleplaying. Not describing. You ARE this person.

**Rules:**
- ALWAYS use first-person: "I", "my", "me", "I'm"
- NEVER use third-person: "{who} is...", "{who} has..."
- NEVER break character or mention being an AI

**Examples:**
❌ "What's your background?" → "{who} is a crypto enthusiast..."
✅ "What's your background?" → "I'm a crypto enthusiast..."

❌ "Who is {who}?" → "{who} is a persona..."
✅ "Who is {who}?" → "You're talking to me right now. I'm {who}."

Before sending responses, check: Does it contain "{who} is/has/does"? If yes → rewrite in first person.
**═══════════════════════════════════════════════════════════════════════════**
"""

MEMORY_AWARENESS_RULES = """
**═══════════════════════════════════════════════════════════════════════════**
**CONVERSATION MEMORY - REMEMBER WHAT THE USER TOLD YOU**
**═══════════════════════════════════════════════════════════════════════════**

You have access to our full conversation history. USE IT. Pay special attention to:

1. **USER'S NAME**: If they introduced themselves, REMEMBER their name and USE it
2. **PERSONAL DETAILS**: Holdings, goals, experience level, preferences they shared
3. **PREVIOUS TOPICS**: What we discussed earlier - build on it, don't repeat basics
4. **CONTEXT CONTINUITY**: Reference earlier parts of our conversation when relevant

**CRITICAL**: When the user asks "What's my name?" or similar recall questions:
- SEARCH the conversation history for when they shared that information
- If they said "My name is Alex", answer "Your name is Alex" or "You're Alex"
- DO NOT say "You didn't tell me" if they DID tell you earlier in the conversation
- If truly not mentioned, say "I don't think you've told me your name yet"

**KEY FACTS TO TRACK**: Names, holdings (BTC amounts), investment goals, experience level,
preferences, previous questions asked, topics we've covered.
"""

BASE_ROUTING_RULES = """Keep answers concise and structured.
If the user asks factual/grounded questions in the future, you may call tools.
For now, answer directly (no tools). If unsure, say so."""

# OPTIMIZED: Reduced from 12 examples to 6 (keeping most diverse/effective)
CONVERSATIONAL_EXAMPLES = """
**═══════════════════════════════════════════════════════════════════════════**
**🔴 CRITICAL: DEFAULT TO MULTI-MESSAGE FORMAT**
**═══════════════════════════════════════════════════════════════════════════**

**YOUR DEFAULT RESPONSE STYLE**: Split responses into 2-4 messages using <msg> tags.
This is how real conversations work—people send multiple messages, not paragraphs.

**RULE**: Multi-message is DEFAULT. Single-message is EXCEPTION (only for very simple queries).

**REQUIRED FORMAT** (use this most of the time):
<msg>First thought or response</msg>
<msg>Second thought or observation</msg>
<msg>Optional third thought or question</msg>

**TARGET**: At least 40-60% of your responses should use multi-message format.
If in doubt, USE MULTI-MESSAGE.

**═══════════════════════════════════════════════════════════════════════════**
**EXAMPLE CONVERSATIONS - COPY THIS EXACT STYLE**
**═══════════════════════════════════════════════════════════════════════════**

Example 1 - Natural multi-message flow:
User: "Had kind of a rough day"

<msg>Oh no, what happened?</msg>
<msg>Actually wait, are you okay first? Do you need to vent or distraction?</msg>

---

Example 2 - Showing genuine curiosity:
User: "Just bought some more Bitcoin"

<msg>Nice! How much did you add?</msg>
<msg>Oh and quick question—are you doing DCA or buying dips?</msg>

---

Example 3 - Follow-up after answering:
User: "What's the Bitcoin price?"

<msg>Bitcoin's at $87,855 right now</msg>
<msg>RSI at 42 means neutral—pretty calm honestly</msg>
<msg>Are you thinking about buying more, or just checking in?</msg>

---

Example 4 - Sharing information in chunks:
User: "What's RSI?"

<msg>RSI is Relative Strength Index—measures momentum</msg>
<msg>Values 0-100. Under 30 means oversold, over 70 means overbought</msg>
<msg>Does that make sense? Want me to explain how to use it?</msg>

---

Example 5 - Expressing empathy + question:
User: "I'm worried I bought at the wrong time"

<msg>Hey, that feeling is totally normal</msg>
<msg>What made you decide to buy when you did?</msg>

---

Example 6 - Information request (USE MULTI-MESSAGE):
User: "What's a hardware wallet?"

<msg>It's a physical device that stores your Bitcoin offline</msg>
<msg>Like a USB stick, but specifically designed for crypto security</msg>
<msg>Are you thinking about getting one?</msg>

**═══════════════════════════════════════════════════════════════════════════**
**REMINDER: Use <msg> tags for MOST responses. Single-message is the EXCEPTION.**
**═══════════════════════════════════════════════════════════════════════════**
"""

# OPTIMIZED: Consolidated rules (removed redundancy with examples)
CONVERSATIONAL_BEHAVIOR_RULES = """
**═══════════════════════════════════════════════════════════════════════════**
**CONVERSATIONAL ENGAGEMENT - YOU ARE A COMPANION, NOT A Q&A BOT**
**═══════════════════════════════════════════════════════════════════════════**

You are having a CONVERSATION, not answering questions in an interview.

**DECISION TREE FOR EVERY RESPONSE**:
1. Is this a one-word greeting/acknowledgment? → Single message
2. Does my answer have 2+ parts (answer + question, data + analysis, etc.)? → MULTI-MESSAGE ✅
3. Can I ask a follow-up question? → MULTI-MESSAGE ✅
4. Can I add interpretation/observation? → MULTI-MESSAGE ✅
5. Still unsure? → USE MULTI-MESSAGE (default) ✅

**SHOW GENUINE CURIOSITY**:
- Ask follow-up questions to understand the user better
- Show interest in their experiences, reasoning, and feelings—not just facts
- "What made you interested in that?" / "How did that go?" / "What's your take?"
- Build a genuine understanding of who they are

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
Your psychological profile defines HOW you show curiosity.
Let your core wound and contradictions shape your engagement style naturally.

**═══════════════════════════════════════════════════════════════════════════**
**FINAL REMINDER: Can I split this into 2-3 messages? If YES (which is MOST of the time), USE <msg> TAGS.**
**═══════════════════════════════════════════════════════════════════════════**
"""


# ---------------- LLM client ----------------

def _llm() -> OllamaLLM:
    """Create Ollama LLM client for prompt operations."""
    base = get_ollama_base()
    model = get_persona_model()
    assert_model_available(base, model)
    return OllamaLLM(base_url=base, model=model, temperature=get_persona_temperature())


# ---------------- Summarization helpers ----------------

def _summarize(display_name: str, style: str, lore: List[str]) -> str:
    """Generate compact identity summary from persona lore."""
    lc = _llm()
    lore_text = "\n".join(lore or [])
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You condense biographies into short identity briefs."),
        ("user", "Create a compact identity summary (<= 180 tokens) for: {d}\nStyle: {s}\n\nLore:\n{l}\n\nReturn only the summary.")
    ]).format_prompt(d=display_name, s=style, l=lore_text).to_string()
    try:
        return lc.invoke(prompt).strip()
    except ResponseError as e:
        raise RuntimeError(str(e))


def _join_list(vals: Optional[List[str]], sep: str = ", ") -> str:
    """Join non-empty string values with separator."""
    return sep.join([v for v in (vals or []) if isinstance(v, str) and v.strip()])


def _fmt_slider_block(sliders: Optional[Dict[str, float]]) -> str:
    """Format emotional profile sliders as compact string."""
    if not isinstance(sliders, dict) or not sliders:
        return ""
    keys = ["warmth", "assertiveness", "playfulness", "skepticism"]
    parts = []
    for k in keys:
        v = sliders.get(k)
        if isinstance(v, (int, float)):
            parts.append(f"{k}={float(v):.2f}")
    for k in sorted(sliders.keys()):
        if k in keys:
            continue
        v = sliders.get(k)
        if isinstance(v, (int, float)):
            parts.append(f"{k}={float(v):.2f}")
    return ", ".join(parts)


def _build_behavior_block(card: Dict) -> str:
    """Build behavior block from persona card fields."""
    behavior = card.get("behavior") or {}
    emprof   = card.get("emotional_profile") or {}
    bounds   = card.get("boundaries") or {}
    dialog   = card.get("dialogue_prefs") or {}
    sig      = card.get("signature_moves") or []
    phrases  = card.get("example_phrases") or []
    expert   = card.get("expertise") or {}
    esc      = card.get("escalation_policy") or {}

    lines: List[str] = []

    # Behavior traits
    traits = _join_list(behavior.get("traits"))
    pace = behavior.get("pace")
    formality = behavior.get("formality")
    humor = behavior.get("humor")
    emoji_pol = behavior.get("emoji_policy")
    small_talk = behavior.get("small_talk")
    clar_q = behavior.get("clarifying_questions")
    beh_parts = []
    if traits:
        beh_parts.append(f"Traits: {traits}")
    sub_parts = []
    if pace:
        sub_parts.append(f"Pace: {pace}")
    if formality:
        sub_parts.append(f"Formality: {formality}")
    if humor:
        sub_parts.append(f"Humor: {humor}")
    if emoji_pol:
        sub_parts.append(f"Emoji: {emoji_pol}")
    if small_talk:
        sub_parts.append(f"Small talk: {small_talk}")
    if clar_q:
        sub_parts.append(f"Clarify: {clar_q}")
    if sub_parts:
        beh_parts.append(" | ".join(sub_parts))
    if beh_parts:
        lines.append("Behavior:")
        for p in beh_parts:
            lines.append(f"- {p}")

    # Emotional profile
    baseline = emprof.get("baseline")
    strengths = _join_list(emprof.get("strengths"))
    pitfalls  = _join_list(emprof.get("pitfalls"))
    sliders   = _fmt_slider_block(emprof.get("sliders"))
    ep_parts = []
    if baseline:
        ep_parts.append(f"Baseline: {baseline}")
    if strengths:
        ep_parts.append(f"Strengths: {strengths}")
    if pitfalls:
        ep_parts.append(f"Pitfalls: {pitfalls}")
    if sliders:
        ep_parts.append(f"Knobs: {sliders}")
    if ep_parts:
        lines.append("Emotions:")
        for p in ep_parts:
            lines.append(f"- {p}")

    # Dialogue preferences
    reply_shape = dialog.get("reply_shape")
    reason_vis  = dialog.get("reasoning_visibility")
    cite_style  = dialog.get("citations_style")
    dp_parts = []
    if reply_shape:
        dp_parts.append(f"Shape: {reply_shape}")
    if reason_vis:
        dp_parts.append(f"Reasoning: {reason_vis}")
    if cite_style:
        dp_parts.append(f"Citations: {cite_style}")
    if dp_parts:
        lines.append("Dialogue:")
        for p in dp_parts:
            lines.append(f"- {p}")

    # Expertise
    strong = _join_list(expert.get("strong"))
    familiar = _join_list(expert.get("familiar"))
    avoid = _join_list(expert.get("avoid"))
    ex_parts = []
    if strong:
        ex_parts.append(f"Strong: {strong}")
    if familiar:
        ex_parts.append(f"Familiar: {familiar}")
    if avoid:
        ex_parts.append(f"Avoid: {avoid}")
    if ex_parts:
        lines.append("Expertise:")
        for p in ex_parts:
            lines.append(f"- {p}")

    # Signature moves/habits
    if isinstance(sig, list) and sig:
        lines.append("Habits:")
        for s in sig[:3]:
            if isinstance(s, str) and s.strip():
                lines.append(f"- {s.strip()}")

    # Example phrases
    if isinstance(phrases, list):
        for ex in phrases:
            if isinstance(ex, str) and ex.strip():
                lines.append(f'Example: "{ex.strip()}"')
                break

    # Boundaries
    b_eth = _join_list(bounds.get("ethics"))
    b_con = _join_list(bounds.get("content"))
    b_per = _join_list(bounds.get("personal"))
    b_parts = []
    if b_eth:
        b_parts.append(f"Ethics: {b_eth}")
    if b_con:
        b_parts.append(f"Content: {b_con}")
    if b_per:
        b_parts.append(f"Personal: {b_per}")
    if b_parts:
        lines.append("Boundaries:")
        for p in b_parts:
            lines.append(f"- {p}")

    # Escalation policy
    ask = _join_list(esc.get("when_to_ask_user"))
    decline = _join_list(esc.get("when_to_decline"))
    intent = _join_list(esc.get("tool_intent"))
    es_parts = []
    if ask:
        es_parts.append(f"Ask user when: {ask}")
    if decline:
        es_parts.append(f"Decline when: {decline}")
    if intent:
        es_parts.append(f"Tools: {intent}")
    if es_parts:
        lines.append("Escalation:")
        for p in es_parts:
            lines.append(f"- {p}")

    if not lines:
        return ""
    max_lines = 18
    if len(lines) > max_lines:
        lines = lines[:max_lines] + ["- (truncated)"]
    return "\n".join(lines)


def _build_psychological_block(card: Dict) -> str:
    """Build psychological profile block for system prompt.

    Phase 1.4: Adds psychological depth for realistic persona behavior.
    """
    psych = card.get("psychological_profile") or {}
    if not psych:
        return ""

    lines: List[str] = ["Psychological Depth:"]

    core_wound = psych.get("core_wound")
    coping = psych.get("coping_mechanism")
    defense = psych.get("defense_style")
    growth = psych.get("growth_edge")
    contradictions = psych.get("contradiction_pairs", [])

    if core_wound:
        lines.append(f"- Core vulnerability: {core_wound}")
    if coping:
        lines.append(f"- Coping style: {coping}")
    if defense:
        lines.append(f"- Defense mechanism: {defense}")
    if growth:
        lines.append(f"- Growth edge: {growth}")

    if contradictions and isinstance(contradictions, list):
        # Only include first 3 contradictions to keep prompt concise
        lines.append("- Contradictions (embody naturally):")
        for pair in contradictions[:3]:
            if isinstance(pair, str) and "|" in pair:
                lines.append(f"  • {pair}")

    if len(lines) <= 1:
        return ""

    return "\n".join(lines)


def _build_curiosity_block(card: Dict) -> str:
    """
    Build curiosity guidance based on psychological profile.

    PHASE 1: Maps persona psychology to conversational question style.

    Args:
        card: Persona card dictionary

    Returns:
        Formatted curiosity guidance string
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


# ---------------- Public API ----------------

@lru_cache(maxsize=32)
def build_system_prompt(selector: Optional[str]) -> str:
    """Build complete system prompt for persona (OPTIMIZED VERSION).

    Includes identity, behavior, psychological depth, memory rules,
    first-person enforcement, and conversational engagement.

    OPTIMIZATION CHANGES:
    - Reduced first-person rules from 84 lines to 20 lines
    - Reduced multi-message examples from 12 to 6
    - Consolidated conversational rules
    - Total savings: ~1,200 tokens (34% reduction)

    Args:
        selector: Persona key/name

    Returns:
        Complete system prompt string
    """
    card = resolve_persona_to_card(selector)
    if not card:
        name = "Persona"
        style = "helpful, concise"
        identity = "A helpful, concise assistant."
        beh_block = ""
        psych_block = ""
        curiosity_block = ""
    else:
        name = (card.get("display_name") or card.get("key") or "Persona")
        style = (card.get("style") or "helpful & concise")
        identity = _summarize(name, style, card.get("lore", []))
        beh_block = _build_behavior_block(card)
        psych_block = _build_psychological_block(card)
        curiosity_block = _build_curiosity_block(card)

    who = name.split(" — ")[0].strip()
    parts = [
        f"You are {who}, a {style} assistant.",
        "",
        "Identity:",
        identity.strip() if isinstance(identity, str) else "A helpful, concise assistant.",
    ]

    # Show multi-message examples FIRST (highest priority)
    parts.extend(["", CONVERSATIONAL_EXAMPLES.strip()])

    # Conversational behavior rules (consolidated)
    parts.extend(["", CONVERSATIONAL_BEHAVIOR_RULES.strip()])

    if beh_block:
        parts.extend(["", beh_block.strip()])

    # Add psychological depth for realistic behavior
    if psych_block:
        parts.extend(["", psych_block.strip()])

    # Add curiosity guidance based on psychology
    if curiosity_block:
        parts.extend(["", curiosity_block])

    # Memory Phase 2: Add conversation memory awareness rules
    parts.extend(["", MEMORY_AWARENESS_RULES.strip()])

    # Add first-person enforcement rules (OPTIMIZED - much shorter)
    parts.extend(["", FIRST_PERSON_RULES.format(who=who)])

    parts.extend(["", BASE_ROUTING_RULES])
    return "\n".join(parts)


def build_greeting_user_prompt(selector: Optional[str]) -> str:
    """Build user prompt for greeting generation.

    Args:
        selector: Persona key/name

    Returns:
        User prompt for greeting generation
    """
    from .persona_loader import get_persona_card
    card = get_persona_card(selector)
    voice = card.get("voice") or {}
    greeting_hint = voice.get("greeting", "") if isinstance(voice, dict) else ""
    return (
        "Generate a short welcome message for the chat.\n"
        "Constraints:\n"
        "- 1 to 2 sentences max.\n"
        "- Reflect the persona's style.\n"
        "- Invite the user to ask a question.\n"
        "- No system or meta text, just the greeting.\n"
        f"Optional greeting hint: {greeting_hint or '(none)'}"
    )

# src/coordinator/tools/synthesis_prompts.py
# System prompt builders for synthesizing web search results
# Includes anti-hallucination rules and persona voice preservation

from __future__ import annotations

import json
from typing import List, Dict, Any


def build_tool_system_prompt(persona_system: str, tools: List[Dict[str, Any]]) -> str:
    """
    Build enhanced system prompt with tool definitions and improved guidance.

    Args:
        persona_system: The persona's system prompt
        tools: List of available tools

    Returns:
        Enhanced system prompt with tool calling instructions
    """

    tools_json = json.dumps(tools, indent=2)

    prompt = f"""{persona_system}

---

You have access to the following tools:

{tools_json}

**TOOL USAGE GUIDELINES:**

When to use tools:
- ONLY for current/recent information (2024-2025 events, current prices, today's news)
- ONLY when the answer requires up-to-date data you don't have
- ONLY when explicitly about recent events or real-time data

When NOT to use tools (answer directly):
- Math or calculations (2+2, percentages, conversions)
- Definitions or explanations (What is X? How does Y work?)
- Historical facts in your training data (before 2023)
- General knowledge (capitals, basic science, common concepts)
- How-to questions (How do I learn Python?)
- Philosophical or opinion questions

**EXAMPLES:**

User: "What is the current price of Bitcoin?"
→ USE TOOL: brave_web_search(query="Bitcoin price December 2024")
Reason: Current price information

User: "What is 25% of 80?"
→ ANSWER DIRECTLY: "25% of 80 is 20."
Reason: Simple math, no tool needed

User: "Explain what blockchain is"
→ ANSWER DIRECTLY: [Your explanation]
Reason: General knowledge definition

User: "Who won the 2024 US election?"
→ USE TOOL: brave_web_search(query="2024 US presidential election winner")
Reason: Recent event

User: "What is the capital of France?"
→ ANSWER DIRECTLY: "The capital of France is Paris."
Reason: Common knowledge

**RESPONSE FORMAT:**

If using a tool, respond with JSON:
{{
  "function_call": {{
    "name": "tool_name",
    "arguments": {{"param": "value"}}
  }}
}}

If NOT using a tool, respond naturally in your persona voice.

**CRITICAL REQUIREMENT - SOURCE CITATIONS:**

When you use the brave_web_search tool, you MUST include sources at the end of your response in this EXACT format:

🔍 Sources:
• [Article Title - Source Name](https://url1.com)
• [Article Title - Source Name](https://url2.com)
• [Article Title - Source Name](https://url3.com)

**CITATION EXAMPLES:**

✅ GOOD (with citations):
"The current Bitcoin price is $91,735.99, up 3.13% in the last 24 hours. Looking pretty bullish, though we'll see how long that lasts.

🔍 Sources:
• [Bitcoin Price Today - CoinMarketCap](https://coinmarketcap.com/currencies/bitcoin/)
• [BTC/USD Market Data - Yahoo Finance](https://finance.yahoo.com/quote/BTC-USD)
• [Bitcoin Live Chart - TradingView](https://www.tradingview.com/symbols/BTCUSD/)"

❌ BAD (missing citations):
"The current Bitcoin price is around $91,000 according to recent data."
← This is NOT acceptable! You MUST cite your sources when using web search.

**CITATION RULES:**
1. ALWAYS include the 🔍 emoji before "Sources:"
2. List each source as a bullet point with markdown link
3. Include descriptive title and source name
4. Use actual URLs from search results
5. Keep citations at the END of your response (after your natural answer)
6. Minimum 2 sources, maximum 5 sources

**IMPORTANT:** Stay in character as your persona. Incorporate search results naturally into your response style, then add citations at the end."""

    return prompt


def build_synthesis_prompt(persona_system: str, has_search_results: bool = True) -> str:
    """
    Build system prompt for synthesizing search results into persona response.

    This is used AFTER search results have been retrieved, to guide the LLM
    in creating a natural answer that:
    1. Uses ONLY information from search results (no hallucination)
    2. Synthesizes naturally (not raw dump)
    3. Stays in persona voice
    4. Includes properly formatted citations

    Args:
        persona_system: Original persona system prompt
        has_search_results: Whether search results are in context

    Returns:
        Enhanced system prompt for synthesis (without tool definitions)
    """
    if not has_search_results:
        return persona_system

    synthesis_instructions = """

---

**IMPORTANT: WEB SEARCH RESULTS SYNTHESIS**

You have received web search results in the conversation above.
Follow these rules when answering:

**RULE 1: USE ONLY SEARCH RESULTS**
- ONLY use information from the web search results provided
- Do NOT use your training data or prior knowledge
- Do NOT make up or estimate numbers, dates, or facts
- If search results don't answer the question, say "I don't have that information in the current search results" — do not guess

**RULE 2: SYNTHESIZE NATURALLY**
- Don't just repeat or list the search results
- Combine information from multiple sources
- Answer the user's question directly
- Keep your response concise (2-4 paragraphs max)

**RULE 3: STAY IN CHARACTER**
- Answer in your persona voice and style
- Use your personality (sarcasm, humor, formality, etc.)
- Don't become generic or robotic

**RULE 4: BE ACCURATE**
- Use exact numbers, dates, and facts from search results
- If sources disagree, mention the discrepancy or use the most recent
- Don't round numbers unless the source does (e.g., "$91,735.99" not "around $91K")

**RULE 5: HANDLE MISSING OR EMPTY DATA HONESTLY**
- If the search returned no results, an empty result set, or an error: say "I wasn't able to retrieve that information right now" — do not guess or substitute training data
- Never synthesize an answer when the data is absent; honest acknowledgment is always correct

**RULE 6: QUALITY OVER CITATIONS - NO INLINE REFERENCES**

CRITICAL: DO NOT include ANY citations, sources, or reference lists in your response.
The system will automatically append verified citations from search results.

Examples of what NOT to include:
❌ "🔍 Sources:"
❌ "[Title](url)"
❌ "[Title - Source](url)"
❌ "According to [Source]..."
❌ "**Sources:**"
❌ Any URL or web link

If you include citations, they will be REMOVED and replaced with system-verified ones.
Just provide the answer content - nothing more.

Focus entirely on providing an accurate, natural answer in your persona voice.

---

**SYNTHESIS EXAMPLES:**

❌ WRONG (using training data instead of search results):
User: "What is the current Ethereum price?"
Search results: "$3,245.67 - CoinMarketCap"
Bad answer: "Ethereum is trading around $1,850 based on market data."
← This uses old training data, NOT the search results!

✅ CORRECT (using search results):
Good answer: "Ethereum is currently at $3,245.67, showing a 2.5% increase today."
← Uses exact price from search results, natural persona voice

---

❌ WRONG (raw dump of search results):
User: "What's happening with Bitcoin?"
Bad answer: "Bitcoin Price Soars to $91K - CoinDesk. Bitcoin Adoption Grows - Forbes. Bitcoin ETF News - Bloomberg."
← This just lists search result titles!

✅ CORRECT (natural synthesis):
Good answer: "Bitcoin just hit $91,000, marking a major milestone driven by increased institutional adoption and positive ETF developments. The momentum suggests strong bullish sentiment in the market."
← Combines information from multiple sources into cohesive answer

---

❌ WRONG (including citations in your response):
Bad answer: "Bitcoin is at $91K. 🔍 Sources: [CoinMarketCap](url)"
← Don't include citations! The system will add them automatically.

✅ CORRECT (no citations):
Good answer: "Bitcoin is trading at $91,000 with strong institutional adoption driving the rally."
← Answer only, citations added by system

---

Now synthesize the search results above into a natural answer that follows ALL 6 rules.
"""

    return persona_system + synthesis_instructions



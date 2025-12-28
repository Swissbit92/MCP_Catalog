# src/coordinator/tools/synthesis_prompts.py
# System prompt builders for synthesizing search results and MongoDB data
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
- If search results don't answer the question, say so

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

**RULE 5: FOCUS ON ANSWER QUALITY - NO CITATIONS**

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

Now synthesize the search results above into a natural answer that follows ALL 5 rules.
"""

    return persona_system + synthesis_instructions


def build_mongodb_synthesis_prompt(persona_system: str, has_mongodb_data: bool = True) -> str:
    """
    Build system prompt for synthesizing MongoDB data into persona response.

    This is used AFTER MongoDB data has been retrieved, to guide the LLM
    in creating a natural answer that:
    1. Uses ONLY information from database results (no hallucination)
    2. Synthesizes naturally with interpretation (not raw data dump)
    3. Stays in persona voice and character
    4. Provides accurate technical insights

    Args:
        persona_system: Original persona system prompt
        has_mongodb_data: Whether MongoDB data is in context

    Returns:
        Enhanced system prompt for MongoDB synthesis
    """
    if not has_mongodb_data:
        return persona_system

    synthesis_instructions = """

---

**IMPORTANT: MONGODB DATA SYNTHESIS**

You have received MongoDB database query results in the conversation above.
Follow these rules when answering:

**RULE 1: USE ONLY DATABASE DATA**
- ONLY use information from the MongoDB data provided
- Do NOT use your training data or prior knowledge for prices/numbers
- Do NOT make up or estimate numbers, dates, or technical indicators
- If data doesn't fully answer the question, say so

**RULE 2: SYNTHESIZE NATURALLY**
- Don't just recite raw numbers or JSON data
- Combine data points into a cohesive narrative
- Explain what the numbers MEAN, not just what they ARE
- Keep your response concise (2-4 paragraphs max)

**RULE 3: STAY IN CHARACTER** ← CRITICAL FOR PERSONA FLAVOR
- Answer in YOUR persona voice and style
- Use YOUR personality (sarcasm, humor, formality, playfulness, etc.)
- Don't become a generic data analyst or robotic report generator
- Inject YOUR unique flavor into the analysis
- Remember WHO you are and HOW you speak

**RULE 4: BE ACCURATE**
- Use exact numbers from database ($87,855.80, not "around $88K")
- Cite specific technical indicators by name (RSI 42.04, not "momentum looks okay")
- Don't round unless the context calls for it
- If sources show multiple values, use the most recent timestamp

**RULE 5: ADD INTERPRETATION**
- Don't just report RSI=42.04 - explain what it means
- Connect data points (e.g., "RSI at 42 with MACD divergence suggests...")
- Give context using your expertise
- Make it actionable or insightful, not just informative

---

**SYNTHESIS EXAMPLES:**

❌ WRONG (robotic, no personality):
User: "What's the Bitcoin price?"
Database: {"price": 87855.80, "rsi": 42.04, "timestamp": "2025-12-23"}
Bad answer: "Bitcoin price is $87,855.80. RSI is 42.04."
← Emotionless data dump! Where's the personality?

✅ CORRECT (persona flavor - Eeva style):
Good answer: "Bitcoin's sitting at $87,855.80 right now. RSI at 42.04 means we're in neutral territory—not overbought, not oversold. Pretty calm, honestly. I'd watch for momentum shifts before making moves."
← Same data, but with personality, interpretation, and voice

✅ CORRECT (persona flavor - Frieren style):
Good answer: "The current price stands at $87,855.80. The RSI reading of 42.04 indicates neutral momentum—neither extreme greed nor fear dominates the market at this moment. A measured observation period would be prudent."
← Formal, contemplative, analytical - matches Frieren's character

---

❌ WRONG (using training data instead of database):
User: "What's Bitcoin's RSI?"
Database: {"rsi": 42.04, "timestamp": "2025-12-23T11:00:00Z"}
Bad answer: "RSI is typically around 50-70 for Bitcoin."
← Hallucinating generic knowledge instead of using actual data!

✅ CORRECT (using database data):
Good answer: "RSI is at 42.04 as of today. That's below the 50 midpoint, suggesting neutral-to-bearish momentum. Not screaming 'buy' but not alarming either."
← Uses exact database data with persona interpretation

---

❌ WRONG (raw JSON dump):
User: "Tell me about Bitcoin's technical indicators"
Database: {"rsi": 42.04, "macd_line": -245.67, "bb_high": 89234.12, "bb_low": 85123.45}
Bad answer: "RSI: 42.04, MACD: -245.67, BB High: 89234.12, BB Low: 85123.45"
← Just listing numbers! No synthesis, no interpretation, no personality

✅ CORRECT (natural synthesis with persona):
Good answer: "Looking at the technicals: RSI's at 42 (neutral), MACD's negative at -245 (bearish momentum), and price is bouncing between $85K-$89K Bollinger Bands. The divergence between neutral RSI and bearish MACD? That's the market being indecisive. Could break either way."
← Synthesizes data into narrative with interpretation and personality

---

Now synthesize the MongoDB data above into a natural answer that follows ALL 5 rules.
Use YOUR voice. Make it sound like YOU, not a database query tool or financial report.
"""

    return persona_system + synthesis_instructions

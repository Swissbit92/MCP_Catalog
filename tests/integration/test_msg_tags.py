#!/usr/bin/env python3
"""Test if nchapman model actually uses <msg> tags in raw output."""

from src.coordinator.llm_client import LC_OllamaClient
from src.coordinator.prompt_builder import build_system_prompt
from src.coordinator.config import settings

def test_raw_llm_output():
    """Check if LLM uses <msg> tags without post-processing."""

    # Build system prompt (includes <msg> tag instructions)
    system_prompt = build_system_prompt("Gojo")

    # Simple user query
    user_query = "What is Bitcoin mining?"

    # Get raw LLM response
    client = LC_OllamaClient(
        base=settings.ollama.base,
        model=settings.ollama.model,
        temperature=settings.ollama.temperature
    )

    raw_response = client.complete(
        system=system_prompt,
        user_prompt=user_query
    )

    print("="*70)
    print("RAW LLM OUTPUT TEST (nchapman model)")
    print("="*70)
    print(f"\nModel: {settings.ollama.model}")
    print(f"Temperature: {settings.ollama.temperature}")
    print(f"\nQuery: {user_query}")
    print(f"\nRaw Response:\n{raw_response}")
    print("\n" + "="*70)

    # Check for <msg> tags
    has_msg_tags = '<msg>' in raw_response

    print(f"\nContains <msg> tags: {has_msg_tags}")

    if has_msg_tags:
        import re
        tags = re.findall(r'<msg>(.*?)</msg>', raw_response, re.DOTALL)
        print(f"Number of <msg> blocks found: {len(tags)}")
        for i, tag in enumerate(tags, 1):
            preview = tag[:100] + "..." if len(tag) > 100 else tag
            print(f"  {i}. {preview}")
    else:
        print("\nLLM did NOT use <msg> tags despite prompt instructions.")
        print("This means _force_multi_message_split() is ALWAYS needed.")

    print("="*70)

    return has_msg_tags

if __name__ == "__main__":
    uses_tags = test_raw_llm_output()

    print("\n" + "="*70)
    print("CONCLUSION")
    print("="*70)

    if uses_tags:
        print("✅ Model follows <msg> tag instructions")
        print("   → Keep both _force_multi_message_split() AND _parse_multi_message_response()")
        print("   → Keep <msg> instructions in prompt")
    else:
        print("❌ Model does NOT follow <msg> tag instructions")
        print("   → Can remove <msg> instructions from prompt")
        print("   → Can refactor: force_split returns list directly, remove parse step")
        print("   → Simpler code path")

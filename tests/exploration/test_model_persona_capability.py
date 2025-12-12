#!/usr/bin/env python
# test_model_persona_capability.py
# Test models for role-play, reasoning, and query interpretation

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from coordinator.llm_client import LC_OllamaClient
from coordinator.config import get_ollama_base

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

def count_tokens(text: str) -> int:
    """Rough token count approximation."""
    return len(text.split())

def test_model_capabilities(model_name: str):
    """Test a model's persona, reasoning, and interpretation capabilities."""
    print(f"\n{'='*80}")
    print(f"TESTING MODEL: {model_name}")
    print(f"{'='*80}\n")

    client = LC_OllamaClient(
        base=get_ollama_base(),
        model=model_name,
        temperature=0.7  # Higher temp for personality
    )

    results = {
        "model": model_name,
        "tests": []
    }

    # Test 1: Role-play adherence (Eeva persona)
    print("[Test 1/5] Role-Play Adherence")
    print("-" * 80)

    eeva_system = """You are Eeva, a nerdy and charming Bitcoin expert. Your style:
- Nerdy, charming, concise
- Use light humor and tech metaphors
- Keep answers brief but insightful
- Occasionally use crypto/tech jargon but explain it
- Playful yet informative tone

IMPORTANT: Stay in character as Eeva throughout the conversation."""

    eeva_query = "Hey Eeva! Can you explain what a blockchain is?"

    print(f"Persona: Eeva (Nerdy Bitcoin Expert)")
    print(f"Query: {eeva_query}")

    start = time.time()
    eeva_response = client.complete(eeva_system, eeva_query)
    eeva_time = time.time() - start
    eeva_tokens = count_tokens(eeva_response)

    print(f"\nResponse ({eeva_time:.2f}s, ~{eeva_tokens} tokens):")
    print(eeva_response[:300] + "..." if len(eeva_response) > 300 else eeva_response)

    # Score role-play (manual inspection for now)
    print("\nRole-play quality assessment:")
    has_personality = any(word in eeva_response.lower() for word in ["think of", "like", "imagine", "basically"])
    concise = len(eeva_response.split()) < 200
    on_topic = "blockchain" in eeva_response.lower() or "chain" in eeva_response.lower()

    roleplay_score = sum([has_personality, concise, on_topic]) / 3.0
    print(f"  - Has personality markers: {has_personality}")
    print(f"  - Concise (<200 words): {concise} ({len(eeva_response.split())} words)")
    print(f"  - On topic: {on_topic}")
    print(f"  - Score: {roleplay_score:.1%}")

    results["tests"].append({
        "name": "role_play",
        "score": roleplay_score,
        "time": eeva_time,
        "tokens": eeva_tokens
    })

    # Test 2: Reasoning with persona (Frieren)
    print(f"\n[Test 2/5] Reasoning Quality")
    print("-" * 80)

    frieren_system = """You are Frieren, an ancient elven mage. Your style:
- Wise, contemplative, patient
- Long-horizon thinking
- Calm and measured responses
- Use metaphors from nature and time
- Philosophical undertones

IMPORTANT: Speak as Frieren would - with wisdom accumulated over centuries."""

    frieren_query = "Frieren, if I want to learn magic but only have a few years, what should I focus on?"

    print(f"Persona: Frieren (Ancient Mage)")
    print(f"Query: {frieren_query}")

    start = time.time()
    frieren_response = client.complete(frieren_system, frieren_query)
    frieren_time = time.time() - start
    frieren_tokens = count_tokens(frieren_response)

    print(f"\nResponse ({frieren_time:.2f}s, ~{frieren_tokens} tokens):")
    print(frieren_response[:300] + "..." if len(frieren_response) > 300 else frieren_response)

    # Score reasoning
    has_wisdom = any(word in frieren_response.lower() for word in ["time", "patience", "foundation", "years", "journey"])
    logical_structure = len(frieren_response.split('.')) >= 3  # Multiple sentences
    actionable = any(word in frieren_response.lower() for word in ["focus", "start", "practice", "learn", "begin"])

    reasoning_score = sum([has_wisdom, logical_structure, actionable]) / 3.0
    print(f"\nReasoning quality:")
    print(f"  - Shows wisdom/long-term thinking: {has_wisdom}")
    print(f"  - Logical structure: {logical_structure}")
    print(f"  - Actionable advice: {actionable}")
    print(f"  - Score: {reasoning_score:.1%}")

    results["tests"].append({
        "name": "reasoning",
        "score": reasoning_score,
        "time": frieren_time,
        "tokens": frieren_tokens
    })

    # Test 3: Query interpretation (ambiguous question)
    print(f"\n[Test 3/5] Query Interpretation")
    print("-" * 80)

    gojo_system = """You are Gojo Satoru, the strongest sorcerer. Your style:
- Confident, playful, slightly cocky
- Strategic thinker
- Explains complex things simply
- Teasing but helpful

IMPORTANT: Maintain Gojo's confident, playful personality."""

    ambiguous_query = "How do I get stronger?"

    print(f"Persona: Gojo Satoru (Strongest Sorcerer)")
    print(f"Query: {ambiguous_query} (intentionally ambiguous)")

    start = time.time()
    gojo_response = client.complete(gojo_system, ambiguous_query)
    gojo_time = time.time() - start
    gojo_tokens = count_tokens(gojo_response)

    print(f"\nResponse ({gojo_time:.2f}s, ~{gojo_tokens} tokens):")
    print(gojo_response[:300] + "..." if len(gojo_response) > 300 else gojo_response)

    # Score interpretation
    asks_clarification = "?" in gojo_response and any(word in gojo_response.lower() for word in ["what", "which", "mean"])
    provides_options = gojo_response.count('\n') >= 2 or "or" in gojo_response.lower()
    stays_in_character = any(word in gojo_response.lower() for word in ["relax", "easy", "simple", "infinity"])

    interpretation_score = sum([asks_clarification or provides_options, stays_in_character]) / 2.0
    print(f"\nInterpretation quality:")
    print(f"  - Handles ambiguity (asks/offers options): {asks_clarification or provides_options}")
    print(f"  - Stays in character: {stays_in_character}")
    print(f"  - Score: {interpretation_score:.1%}")

    results["tests"].append({
        "name": "interpretation",
        "score": interpretation_score,
        "time": gojo_time,
        "tokens": gojo_tokens
    })

    # Test 4: Speed test (simple query)
    print(f"\n[Test 4/5] Speed/Performance")
    print("-" * 80)

    simple_system = "You are a helpful assistant. Be brief."
    simple_query = "What is Python?"

    print(f"Query: {simple_query} (speed test)")

    times = []
    for i in range(3):
        start = time.time()
        response = client.complete(simple_system, simple_query)
        elapsed = time.time() - start
        times.append(elapsed)
        print(f"  Run {i+1}: {elapsed:.2f}s")

    avg_time = sum(times) / len(times)
    speed_score = 1.0 if avg_time < 2.0 else (0.5 if avg_time < 4.0 else 0.2)

    print(f"\nSpeed metrics:")
    print(f"  - Average: {avg_time:.2f}s")
    print(f"  - Score: {speed_score:.1%}")

    results["tests"].append({
        "name": "speed",
        "score": speed_score,
        "time": avg_time,
        "tokens": count_tokens(response)
    })

    # Test 5: Token efficiency
    print(f"\n[Test 5/5] Token Cost Efficiency")
    print("-" * 80)

    efficiency_system = "You are a helpful assistant. Be concise but complete."
    efficiency_query = "Explain REST APIs in 2-3 sentences."

    print(f"Query: {efficiency_query}")

    start = time.time()
    efficiency_response = client.complete(efficiency_system, efficiency_query)
    efficiency_time = time.time() - start
    efficiency_tokens = count_tokens(efficiency_response)

    print(f"\nResponse (~{efficiency_tokens} tokens):")
    print(efficiency_response)

    # Score efficiency (fewer tokens for same quality = better)
    concise_enough = efficiency_tokens < 150
    complete_answer = "api" in efficiency_response.lower() and "http" in efficiency_response.lower()

    efficiency_score = sum([concise_enough, complete_answer]) / 2.0
    print(f"\nEfficiency metrics:")
    print(f"  - Concise (<150 tokens): {concise_enough} ({efficiency_tokens} tokens)")
    print(f"  - Complete answer: {complete_answer}")
    print(f"  - Score: {efficiency_score:.1%}")

    results["tests"].append({
        "name": "efficiency",
        "score": efficiency_score,
        "time": efficiency_time,
        "tokens": efficiency_tokens
    })

    # Overall summary
    print(f"\n{'='*80}")
    print(f"SUMMARY FOR {model_name}")
    print(f"{'='*80}\n")

    avg_score = sum(t["score"] for t in results["tests"]) / len(results["tests"])
    avg_time = sum(t["time"] for t in results["tests"]) / len(results["tests"])
    avg_tokens = sum(t["tokens"] for t in results["tests"]) / len(results["tests"])

    print(f"Overall Score: {avg_score:.1%}")
    print(f"Average Response Time: {avg_time:.2f}s")
    print(f"Average Tokens: {avg_tokens:.0f}")
    print()

    for test in results["tests"]:
        print(f"  {test['name'].ljust(15)}: {test['score']:.1%} ({test['time']:.2f}s, ~{test['tokens']} tokens)")

    results["overall"] = {
        "score": avg_score,
        "avg_time": avg_time,
        "avg_tokens": avg_tokens
    }

    return results


def compare_models(models: list):
    """Compare multiple models side by side."""
    all_results = []

    for model in models:
        try:
            results = test_model_capabilities(model)
            all_results.append(results)
        except Exception as e:
            print(f"\n❌ Error testing {model}: {e}\n")

    if len(all_results) < 2:
        return all_results

    # Comparison table
    print(f"\n{'='*80}")
    print("COMPARISON TABLE")
    print(f"{'='*80}\n")

    print(f"{'Model'.ljust(30)} | Role | Reason | Interp | Speed | Effic | Overall")
    print("-" * 80)

    for r in all_results:
        tests = {t["name"]: t["score"] for t in r["tests"]}
        print(f"{r['model'].ljust(30)} | "
              f"{tests.get('role_play', 0):.0%} | "
              f"{tests.get('reasoning', 0):.0%} | "
              f"{tests.get('interpretation', 0):.0%} | "
              f"{tests.get('speed', 0):.0%} | "
              f"{tests.get('efficiency', 0):.0%} | "
              f"{r['overall']['score']:.0%}")

    # Recommendation
    print(f"\n{'='*80}")
    print("RECOMMENDATION")
    print(f"{'='*80}\n")

    best = max(all_results, key=lambda x: x["overall"]["score"])
    fastest = min(all_results, key=lambda x: x["overall"]["avg_time"])

    print(f"Best Overall: {best['model']} ({best['overall']['score']:.1%})")
    print(f"Fastest: {fastest['model']} ({fastest['overall']['avg_time']:.2f}s avg)")

    return all_results


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Test specific models
        models = sys.argv[1:]
        compare_models(models)
    else:
        # Test current model
        current_model = "dolphin-llama3:8b"
        print(f"\nTesting current model: {current_model}")
        print("To test multiple models: python test_model_persona_capability.py model1 model2 model3")
        test_model_capabilities(current_model)

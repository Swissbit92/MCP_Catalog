#!/usr/bin/env python
# test_function_calling.py
# Test if dolphin-llama3:8b supports function calling

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from coordinator.llm_client import LC_OllamaClient
from coordinator.config import get_ollama_base, get_persona_model

def test_function_calling():
    """Test if the current model supports function calling."""
    print("\n" + "=" * 70)
    print("FUNCTION CALLING CAPABILITY TEST")
    print("=" * 70)

    model_name = get_persona_model()
    print(f"\nModel: {model_name}")
    print("Testing with Ollama function calling format...")

    # Create client
    client = LC_OllamaClient(
        base=get_ollama_base(),
        model=model_name,
        temperature=0.1
    )

    # Define a simple function
    tools = [{
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web for current information using Brave Search API",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to execute"
                    }
                },
                "required": ["query"]
            }
        }
    }]

    # Test scenarios
    scenarios = [
        {
            "query": "What is the current price of Bitcoin?",
            "should_call": True,
            "reason": "Requires current information"
        },
        {
            "query": "Explain what blockchain technology is",
            "should_call": False,
            "reason": "General knowledge question"
        },
        {
            "query": "What happened in the 2024 US election?",
            "should_call": True,
            "reason": "Recent event requiring current data"
        },
        {
            "query": "What is 2 + 2?",
            "should_call": False,
            "reason": "Simple math, no web search needed"
        }
    ]

    print("\n" + "-" * 70)
    print("Test Method: OpenAI-style function calling prompt")
    print("-" * 70)

    # Build system prompt with function definition
    system_prompt = f"""You are a helpful AI assistant with access to tools. You can call functions to help answer questions.

Available functions:
{json.dumps(tools, indent=2)}

When you need to use a function, respond with a JSON object in this format:
{{
  "function_call": {{
    "name": "function_name",
    "arguments": {{"param": "value"}}
  }}
}}

If you don't need to call a function, just answer the question directly.

IMPORTANT: Only call search_web when you need CURRENT or RECENT information that you don't have in your training data. For general knowledge, answer directly without calling functions."""

    results = []

    for i, scenario in enumerate(scenarios, 1):
        print(f"\n[Test {i}/4] {scenario['query']}")
        print(f"Expected: {'CALL search_web' if scenario['should_call'] else 'NO CALL (direct answer)'}")

        try:
            response = client.complete(system_prompt, scenario["query"])

            # Check if response contains function call
            has_function_call = False
            if "function_call" in response.lower() or '"name":' in response:
                try:
                    # Try to parse as JSON
                    response_json = json.loads(response)
                    if "function_call" in response_json:
                        has_function_call = True
                        func_name = response_json["function_call"]["name"]
                        func_args = response_json["function_call"]["arguments"]
                        print(f"Result: CALLED {func_name}({func_args})")
                    else:
                        print(f"Result: DIRECT ANSWER")
                except json.JSONDecodeError:
                    print(f"Result: DIRECT ANSWER (not valid JSON)")
            else:
                print(f"Result: DIRECT ANSWER")

            # Determine if test passed
            passed = has_function_call == scenario["should_call"]
            status = "PASS" if passed else "FAIL"

            print(f"Status: {status}")
            if not passed:
                print(f"Response preview: {response[:200]}...")

            results.append({
                "scenario": scenario["query"],
                "expected_call": scenario["should_call"],
                "actual_call": has_function_call,
                "passed": passed
            })

        except Exception as e:
            print(f"ERROR: {e}")
            results.append({
                "scenario": scenario["query"],
                "expected_call": scenario["should_call"],
                "actual_call": None,
                "passed": False
            })

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    passed = sum(1 for r in results if r["passed"])
    total = len(results)

    print(f"\nTests Passed: {passed}/{total}")

    if passed == total:
        print("\nRESULT: Model SUPPORTS function calling")
        print("Recommendation: Proceed with function calling implementation")
        return True
    elif passed >= total / 2:
        print("\nRESULT: Model PARTIALLY supports function calling")
        print("Recommendation: Implement with fallback heuristics")
        return "partial"
    else:
        print("\nRESULT: Model DOES NOT support function calling reliably")
        print("Recommendation: Use alternative approach (keyword heuristics or different model)")
        print("\nAlternative models for RTX 4090 16GB:")
        print("  1. dolphin-mixtral:8x7b - Uncensored, supports function calling, fits 16GB")
        print("  2. hermes-2-pro-mistral:7b - Excellent function calling support")
        print("  3. mistral-nemo:latest - Good function calling, 12B params")
        print("  4. llama3.1:8b - Native tool support")
        return False

    print("\n" + "=" * 70)


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except:
        pass

    result = test_function_calling()

    # Exit code: 0 = supports, 1 = partial, 2 = doesn't support
    if result is True:
        sys.exit(0)
    elif result == "partial":
        sys.exit(1)
    else:
        sys.exit(2)

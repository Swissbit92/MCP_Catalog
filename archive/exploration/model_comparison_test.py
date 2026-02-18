#!/usr/bin/env python3
"""Model Comparison Test for Phase 2 Conversational AI.

Tests both seamon67/Gemma3-Abliterated:4b-f16 and nchapman/gemma-2-9b-it-abliterated:9b
across multiple conversational scenarios to evaluate:
- Personality adherence
- Multi-message quality
- Conversational flow
- Question engagement
- Response coherence
"""

import requests
import json
import time
from typing import Dict, List

BACKEND_URL = "http://127.0.0.1:8000"

# Test scenarios covering different conversation types
TEST_SCENARIOS = [
    {
        "name": "Beginner Question",
        "persona": "Gojo",
        "message": "I'm new to Bitcoin. Can you help me understand the basics?",
        "expectations": ["multi-message", "questions", "concise"]
    },
    {
        "name": "Technical Question",
        "persona": "Eeva",
        "message": "How does the Bitcoin halving affect the price long-term?",
        "expectations": ["personality", "analytical"]
    },
    {
        "name": "Emotional Context",
        "persona": "Frieren",
        "message": "I lost money on my first Bitcoin investment and I'm worried.",
        "expectations": ["empathy", "guidance"]
    },
    {
        "name": "Follow-up Question",
        "persona": "Gojo",
        "message": "What about mining? How does that work?",
        "expectations": ["concise", "questions"]
    },
]

def create_session(persona: str, title: str) -> str:
    """Create a new chat session."""
    response = requests.post(
        f"{BACKEND_URL}/sessions",
        json={"persona_key": persona, "title": title}
    )
    if response.status_code == 200:
        return response.json()["id"]
    raise Exception(f"Failed to create session: {response.status_code}")

def send_message(session_id: str, message: str) -> Dict:
    """Send a message and get response."""
    response = requests.post(
        f"{BACKEND_URL}/sessions/{session_id}/chat",
        json={"message": message}
    )
    if response.status_code == 200:
        return response.json()
    raise Exception(f"Failed to send message: {response.status_code}")

def analyze_response(response: Dict, expectations: List[str]) -> Dict:
    """Analyze response quality against expectations."""
    analysis = {
        "is_multi": isinstance(response.get("answer"), list),
        "message_count": response.get("message_count", 1),
        "has_questions": False,
        "avg_length": 0,
        "total_length": 0,
        "personality_score": 0
    }

    # Extract answer text
    answer = response.get("answer")
    if isinstance(answer, list):
        messages = answer
        analysis["has_questions"] = any("?" in msg for msg in messages)
        analysis["avg_length"] = sum(len(msg) for msg in messages) / len(messages)
        analysis["total_length"] = sum(len(msg) for msg in messages)
    else:
        messages = [answer]
        analysis["has_questions"] = "?" in answer
        analysis["avg_length"] = len(answer)
        analysis["total_length"] = len(answer)

    # Check expectations
    expectations_met = []
    if "multi-message" in expectations:
        expectations_met.append(("multi-message", analysis["is_multi"]))
    if "questions" in expectations:
        expectations_met.append(("questions", analysis["has_questions"]))
    if "concise" in expectations:
        expectations_met.append(("concise", analysis["avg_length"] < 300))

    analysis["expectations_met"] = expectations_met
    analysis["response_text"] = messages

    return analysis

def run_test_scenario(scenario: Dict, model_name: str) -> Dict:
    """Run a single test scenario."""
    print(f"\n  Testing: {scenario['name']}")

    # Create session
    session_id = create_session(
        scenario["persona"],
        f"{model_name} - {scenario['name']}"
    )

    # Send message
    response = send_message(session_id, scenario["message"])

    # Analyze
    analysis = analyze_response(response, scenario["expectations"])

    # Print results
    print(f"    Format: {'Multi-message' if analysis['is_multi'] else 'Single'} ({analysis['message_count']} msgs)")
    print(f"    Length: {analysis['total_length']} chars (avg: {analysis['avg_length']:.0f})")
    print(f"    Questions: {'Yes' if analysis['has_questions'] else 'No'}")

    return {
        "scenario": scenario["name"],
        "analysis": analysis,
        "response": response
    }

def compare_models():
    """Run all scenarios and compare results."""
    print("="*70)
    print("MODEL COMPARISON TEST - Phase 2 Conversational AI")
    print("="*70)

    # Note: This script assumes server is already running with the model
    # Run this twice - once with each model configured in .env

    model_name = input("\nEnter current model name (e.g., 'seamon67' or 'nchapman'): ")

    results = []

    for scenario in TEST_SCENARIOS:
        try:
            result = run_test_scenario(scenario, model_name)
            results.append(result)
            time.sleep(1)  # Brief pause between tests
        except Exception as e:
            print(f"    ERROR: {e}")

    # Summary
    print("\n" + "="*70)
    print(f"SUMMARY - {model_name}")
    print("="*70)

    multi_count = sum(1 for r in results if r["analysis"]["is_multi"])
    question_count = sum(1 for r in results if r["analysis"]["has_questions"])
    avg_total_length = sum(r["analysis"]["total_length"] for r in results) / len(results)

    print(f"Multi-message responses: {multi_count}/{len(results)}")
    print(f"Responses with questions: {question_count}/{len(results)}")
    print(f"Average total response length: {avg_total_length:.0f} chars")

    # Save detailed results
    filename = f"model_test_results_{model_name}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump({
            "model": model_name,
            "scenarios": results,
            "summary": {
                "multi_message_count": multi_count,
                "question_count": question_count,
                "avg_total_length": avg_total_length
            }
        }, f, indent=2, ensure_ascii=False)

    print(f"\nDetailed results saved to: {filename}")
    print("="*70)

if __name__ == "__main__":
    try:
        compare_models()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

#!/usr/bin/env python3
"""Quick test to check actual persona responses"""

import requests

BASE_URL = "http://localhost:8000"

queries = [
    ("Eeva", "Who are you?"),
    ("Frieren", "Tell me about yourself"),
    ("Gojo", "Describe Gojo to me"),
]

for persona, query in queries:
    print(f"\n{'='*80}")
    print(f"Persona: {persona}")
    print(f"Query: '{query}'")
    print(f"{'='*80}")

    try:
        response = requests.post(
            f"{BASE_URL}/persona/chat",
            json={"persona": persona, "message": query, "history": []},
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            answer = data.get("response", "")

            print(f"\nResponse ({len(answer)} chars):")
            print(answer)

            # Check first-person usage
            has_first_person = any(p in answer.lower() for p in [" i ", " my ", " me ", " i'm ", " i've "])
            has_first_person = has_first_person or answer.lower().startswith(("i ", "i'm ", "i've ", "hey", "yo", "hello"))

            # Check third-person (simple check)
            persona_name = persona.lower()
            has_third_person_pattern = f"{persona_name} is " in answer.lower() or f"{persona_name} has " in answer.lower()

            print(f"\n✓ Has first-person pronouns: {has_first_person}")
            print(f"✓ No obvious third-person: {not has_third_person_pattern}")

        else:
            print(f"ERROR: HTTP {response.status_code}")
            print(response.text)

    except Exception as e:
        print(f"ERROR: {e}")

#!/usr/bin/env python3
"""Debug script to see full API response"""

import requests
import json

BASE_URL = "http://localhost:8000"

print("Testing persona API response structure...\n")

response = requests.post(
    f"{BASE_URL}/persona/chat",
    json={"persona": "Eeva", "message": "Who are you?", "history": []},
    timeout=30
)

print(f"Status Code: {response.status_code}")
print(f"\nFull Response JSON:")
print(json.dumps(response.json(), indent=2))

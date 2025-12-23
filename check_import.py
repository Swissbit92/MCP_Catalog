#!/usr/bin/env python3
"""Check which server.py file is being imported."""

import sys
sys.path.insert(0, "C:\\Users\\rzehn\\desktop\\MCP_Catalog")

from src.coordinator import server

print(f"Server module loaded from: {server.__file__}")

# Check the actual code
import inspect
source = inspect.getsource(server.chat)
if "Assistant: {t.content}" in source:
    print("\n[OK] Code contains NEW format: 'Assistant: {t.content}'")
elif '[Assistant]' in source:
    print("\n[ERROR] Code contains OLD format: '[Assistant]'")
else:
    print("\n[UNKNOWN] Can't find formatting code")

# Show a snippet
lines = source.split('\n')
for i, line in enumerate(lines):
    if 'lines.append' in line and 'Assistant' in line:
        print(f"\nLine {i}: {line}")

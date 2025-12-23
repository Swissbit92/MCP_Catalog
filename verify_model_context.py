#!/usr/bin/env python3
"""Verify the context window size of the current LLM model.

This script queries Ollama for the configured model's context window size
to help configure optimal memory window settings.
"""

import subprocess
import json
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from coordinator.config import get_persona_model, get_ollama_base


def get_model_context_window(model_name: str) -> dict:
    """Query Ollama for model context window size.

    Args:
        model_name: Name of the Ollama model (e.g., 'llama3.1:latest')

    Returns:
        Dictionary with model info and context window size
    """
    try:
        # Get model information
        result = subprocess.run(
            ["ollama", "show", model_name],
            capture_output=True,
            text=True,
            check=True
        )

        output = result.stdout
        context_size = None

        print(f"Model: {model_name}")
        print("=" * 70)

        # Look for context_length or num_ctx parameter
        for line in output.split('\n'):
            line_lower = line.lower()
            if 'context' in line_lower or 'num_ctx' in line_lower:
                print(f"Context info: {line}")
                # Try to extract number
                import re
                numbers = re.findall(r'\d+', line)
                if numbers:
                    context_size = int(numbers[0])

        # Try to get modelfile to see parameters
        print("\n" + "=" * 70)
        print("Model Configuration:")
        print("=" * 70)

        result_modelfile = subprocess.run(
            ["ollama", "show", model_name, "--modelfile"],
            capture_output=True,
            text=True,
            check=True
        )

        modelfile_output = result_modelfile.stdout
        print(modelfile_output)

        # Parse modelfile for num_ctx parameter
        for line in modelfile_output.split('\n'):
            if 'num_ctx' in line.lower():
                import re
                match = re.search(r'num_ctx\s+(\d+)', line, re.IGNORECASE)
                if match:
                    context_size = int(match.group(1))
                    print(f"\n[+] Found context window: {context_size} tokens")

        # Common defaults if not found
        if not context_size:
            print("\n[!] Could not detect context window from model config")
            print("Common defaults:")
            print("  - llama3.1, llama3: 8192 tokens")
            print("  - mistral: 8192 tokens")
            print("  - mixtral: 32768 tokens")
            print("  - gemma: 8192 tokens")
            print("  - Default fallback: 4096 tokens")

            # Try to guess based on model name
            model_lower = model_name.lower()
            if 'llama3' in model_lower or 'mistral' in model_lower or 'gemma' in model_lower:
                context_size = 8192
                print(f"\n[~] Estimated context window: {context_size} tokens (based on model name)")
            elif 'mixtral' in model_lower:
                context_size = 32768
                print(f"\n[~] Estimated context window: {context_size} tokens (based on model name)")
            else:
                context_size = 4096
                print(f"\n[~] Using fallback context window: {context_size} tokens")

        return {
            "model": model_name,
            "context_window": context_size,
            "raw_output": output
        }

    except subprocess.CalledProcessError as e:
        print(f"[X] Error querying model: {e}")
        print(f"Stderr: {e.stderr}")
        return None
    except FileNotFoundError:
        print("[X] Error: 'ollama' command not found")
        print("Make sure Ollama is installed and in your PATH")
        return None


def calculate_recommended_settings(context_window: int) -> dict:
    """Calculate recommended memory settings based on context window.

    Args:
        context_window: Model's context window size in tokens

    Returns:
        Dictionary with recommended settings
    """
    # Reserve tokens for system prompt (~1500-2000 tokens typically)
    # Reserve tokens for response generation (~500 tokens)
    reserved_tokens = 2500

    available_for_history = context_window - reserved_tokens

    # Estimate messages based on ~100 tokens per message average
    avg_tokens_per_message = 100
    recommended_messages = max(10, int(available_for_history / avg_tokens_per_message))

    # Phase 1 conservative target: 30 messages
    phase1_messages = min(30, recommended_messages)

    # Phase 2 optimized target: 70-80% of available
    phase2_messages = int(recommended_messages * 0.75)

    return {
        "context_window": context_window,
        "reserved_tokens": reserved_tokens,
        "available_for_history": available_for_history,
        "avg_tokens_per_message": avg_tokens_per_message,
        "max_messages_theoretical": recommended_messages,
        "phase1_target": phase1_messages,
        "phase2_target": phase2_messages,
        "utilization_percent": round((available_for_history / context_window) * 100, 1)
    }


def main():
    """Main entry point."""
    # Get configured model from environment
    model = get_persona_model()
    ollama_base = get_ollama_base()

    print("[*] Model Context Window Verification")
    print("=" * 70)
    print(f"Configured Model: {model}")
    print(f"Ollama Base URL: {ollama_base}")
    print()

    # Allow override via command line
    if len(sys.argv) > 1:
        model = sys.argv[1]
        print(f"Using command-line model: {model}")
        print()

    # Get model info
    model_info = get_model_context_window(model)

    if not model_info:
        print("\n[X] Failed to retrieve model information")
        sys.exit(1)

    context_window = model_info["context_window"]

    # Calculate recommendations
    print("\n" + "=" * 70)
    print("[#] Recommended Memory Settings")
    print("=" * 70)

    settings = calculate_recommended_settings(context_window)

    print(f"\nContext Window:        {settings['context_window']:,} tokens")
    print(f"Reserved (system+gen): {settings['reserved_tokens']:,} tokens")
    print(f"Available for history: {settings['available_for_history']:,} tokens ({settings['utilization_percent']}%)")
    print()
    print(f"[>] Message Capacity Estimates:")
    print(f"  - Theoretical max:   {settings['max_messages_theoretical']} messages")
    print(f"  - Phase 1 target:    {settings['phase1_target']} messages (conservative)")
    print(f"  - Phase 2 target:    {settings['phase2_target']} messages (optimized)")
    print()
    print(f"[!] Configuration Recommendations:")
    print(f"  1. Update chat_with_session() to load last {settings['phase1_target']} messages")
    print(f"  2. Monitor token usage with log_context_stats()")
    print(f"  3. Set model_context_window={settings['context_window']} in config")
    print(f"  4. Phase 2: Implement smart windowing to reach {settings['phase2_target']} messages")

    # Write to config file suggestion
    print("\n" + "=" * 70)
    print("[=] Add to your configuration:")
    print("=" * 70)
    print(f"MODEL_CONTEXT_WINDOW={settings['context_window']}")
    print(f"MEMORY_WINDOW_SIZE={settings['phase1_target']}  # Phase 1")
    print(f"# MEMORY_WINDOW_SIZE={settings['phase2_target']}  # Phase 2 (future)")
    print()


if __name__ == "__main__":
    main()

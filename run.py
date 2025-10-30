# run.py
# Entrypoint for GraphRAG Local QA Chat with Personas
# Starts the Local Coordinator and Streamlit UI.
# Requires Ollama to be running with the specified model pulled.

#!/usr/bin/env python
import os
import sys
import time
import subprocess
from pathlib import Path

# 1) Env
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

ROOT = Path(__file__).parent.resolve()

# 2) Make local src importable
sys.path.append(str(ROOT / "src"))

# 2b) Import UI helper for persona listing (doesn't pull Streamlit)
try:
    from ui.personas import load_persona_cards, build_coordinator_label, persona_dir
except Exception:
    load_persona_cards = None
    build_coordinator_label = None
    persona_dir = lambda: os.getenv("PERSONA_DIR", "personas")  # type: ignore

# 3) Ollama helpers (reuse your coordinator utilities)
try:
    from coordinator.ollama_utils import (
        assert_model_available,
        list_local_models,
        OllamaModelNotFound,
    )
except Exception as e:
    print("❌ Could not import coordinator.ollama_utils. Is the project layout intact?")
    print(f"   Error: {e}")
    sys.exit(1)

# 4) Summary preflight (serialized)
try:
    from coordinator.persona_memory import ensure_all_summaries_serialized
except Exception as e:
    print("❌ Could not import coordinator.persona_memory for summary preflight.")
    print(f"   Error: {e}")
    sys.exit(1)


def _required_env(name: str, default: str | None = None) -> str:
    val = os.getenv(name, default if default is not None else "").strip()
    if not val:
        print(f"❌ Missing required environment variable: {name}")
        print(f"   Set it in your .env (e.g. {name}=value)")
        sys.exit(1)
    return val

def _discover_persona_labels() -> str:
    try:
        if not (load_persona_cards and build_coordinator_label):
            return "—"
        cards = load_persona_cards(persona_dir())
        labels = []
        for c in cards:
            key = (c.get("key") or "AI").split()[0].capitalize()
            labels.append(build_coordinator_label(c, key))
        return ", ".join(labels) if labels else "—"
    except Exception:
        return "—"

def welcome_banner(coord_port: str, model: str, base: str):
    personas_line = _discover_persona_labels()
    print("\n" + "=" * 78)
    print("  🎉 Welcome to GraphRAG — Local Coordinator + UI (Chat-Only)")
    print("=" * 78)
    print(f"  • Ollama base   : {base}")
    print(f"  • Model         : {model}")
    print(f"  • Coordinator   : http://127.0.0.1:{coord_port}")
    print(f"  • Streamlit UI  : http://localhost:8501")
    print("-" * 78)
    print(f"  Personas: {personas_line}")
    print("  Tip: Press Ctrl+C to stop both services gracefully.")
    print("=" * 78 + "\n")

def check_ollama(base: str, model: str):
    """Verify Ollama is reachable and the requested model is pulled."""
    try:
        assert_model_available(base, model)
    except OllamaModelNotFound as e:
        print("❌ Ollama is reachable, but the requested model is not available.")
        print(f"   Requested model: {model}")
        try:
            available = list_local_models(base)
            if available:
                print("   Available models:")
                for m in available:
                    print(f"     • {m}")
        except Exception:
            pass
        print("\n   👉 Pull the model first:")
        print(f"      ollama pull {model}\n")
        sys.exit(1)
    except Exception as e:
        print("❌ Could not contact Ollama. Is it running?")
        print(f"   Base URL: {base}")
        print(f"   Error   : {e}")
        print("\n   👉 Start Ollama app or run the daemon, then try again.")
        sys.exit(1)

def main():
    # Read env
    coord_port = os.getenv("COORD_PORT", "8000").strip() or "8000"
    base = _required_env("OLLAMA_BASE")
    model = _required_env("PERSONA_MODEL")

    # Health checks
    check_ollama(base, model)

    # Friendly greeting
    welcome_banner(coord_port, model, base)

    # ---- SERIALIZED SUMMARY PREFLIGHT (BLOCKING) ----
    # Ensures summaries exist/are fresh before Coordinator/UI start
    print("⏳ Pre-warming persona CV summaries (serialized)…")
    try:
        built, skipped = ensure_all_summaries_serialized(timeout_sec=900, poll_sec=0.25)
        print(f"✅ Summary preflight complete — built: {built}, up-to-date: {skipped}")
    except Exception as e:
        print(f"⚠️ Summary preflight encountered an issue: {e}")
        # Non-fatal — the app can still run, but first greet might rebuild a missing one

    # Commands
    coord_cmd = [
        sys.executable, "-m", "uvicorn",
        "src.coordinator.server:app",
        "--port", coord_port, "--reload"
    ]
    ui_cmd = [sys.executable, "-m", "streamlit", "run", "ui/app.py"]

    # Start processes
    try:
        coord_proc = subprocess.Popen(coord_cmd)
    except FileNotFoundError:
        print("❌ Could not start Coordinator (uvicorn missing?).")
        print("   👉 pip install -r requirements.txt")
        sys.exit(1)

    # brief warmup so UI can connect immediately
    time.sleep(2)

    try:
        ui_proc = subprocess.Popen(ui_cmd)
    except FileNotFoundError:
        print("❌ Could not start Streamlit UI (streamlit missing?).")
        print("   👉 pip install -r requirements.txt")
        # stop coordinator if UI failed to start
        coord_proc.terminate()
        coord_proc.wait()
        sys.exit(1)

    # Wait & handle Ctrl+C
    try:
        coord_proc.wait()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down…")
        try:
            coord_proc.terminate()
        except Exception:
            pass
        try:
            ui_proc.terminate()
        except Exception:
            pass
        try:
            coord_proc.wait(timeout=5)
        except Exception:
            pass
        try:
            ui_proc.wait(timeout=5)
        except Exception:
            pass

if __name__ == "__main__":
    main()

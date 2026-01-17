# run_react.py
# Entrypoint for GraphRAG Coordinator + React UI
# Starts the Local Coordinator and React dev server.
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

# 3) Ollama helpers (reuse your coordinator utilities)
try:
    from coordinator.ollama_utils import (
        assert_model_available,
        list_local_models,
        OllamaModelNotFound,
    )
except Exception as e:
    print("ERROR: Could not import coordinator.ollama_utils. Is the project layout intact?")
    print(f"   Error: {e}")
    sys.exit(1)

def _required_env(name: str, default: str | None = None) -> str:
    val = os.getenv(name, default if default is not None else "").strip()
    if not val:
        print(f"ERROR: Missing required environment variable: {name}")
        print(f"   Set it in your .env (e.g. {name}=value)")
        sys.exit(1)
    return val

def welcome_banner(coord_port: str, react_port: str, model: str, base: str):
    print("\n" + "=" * 78)
    print("  Welcome to GraphRAG - Local Coordinator + React UI")
    print("=" * 78)
    print(f"  * Ollama base   : {base}")
    print(f"  * Model         : {model}")
    print(f"  * Coordinator   : http://127.0.0.1:{coord_port}")
    print(f"  * React UI      : http://localhost:{react_port}")
    print("-" * 78)
    print("  Tip: Press Ctrl+C to stop both services gracefully.")
    print("=" * 78 + "\n")

def check_ollama(base: str, model: str):
    """Verify Ollama is reachable and the requested model is pulled."""
    try:
        assert_model_available(base, model)
    except OllamaModelNotFound as e:
        print("ERROR: Ollama is reachable, but the requested model is not available.")
        print(f"   Requested model: {model}")
        try:
            available = list_local_models(base)
            if available:
                print("   Available models:")
                for m in available:
                    print(f"     - {m}")
        except Exception:
            pass
        print("\n   -> Pull the model first:")
        print(f"      ollama pull {model}\n")
        sys.exit(1)
    except Exception as e:
        print("ERROR: Could not contact Ollama. Is it running?")
        print(f"   Base URL: {base}")
        print(f"   Error   : {e}")
        print("\n   -> Start Ollama app or run the daemon, then try again.")
        sys.exit(1)

def check_npm():
    """Check if npm is available."""
    try:
        result = subprocess.run(["npm", "--version"], capture_output=True, text=True, timeout=5, shell=True)
        if result.returncode == 0:
            print(f"npm version: {result.stdout.strip()}")
            return True
        else:
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        return False

def main():
    # Read env
    coord_port = os.getenv("COORD_PORT", "8000").strip() or "8000"
    react_port = os.getenv("REACT_PORT", "3000").strip() or "3000"
    base = _required_env("OLLAMA_BASE")
    model = _required_env("PERSONA_MODEL")

    # Check if npm is available
    if not check_npm():
        print("ERROR: npm is not available. Please install Node.js from https://nodejs.org/")
        print("   After installing Node.js, run: cd react-ui && npm install")
        sys.exit(1)

    # Health checks
    check_ollama(base, model)

    # Friendly greeting
    welcome_banner(coord_port, react_port, model, base)

    # Commands
    coord_cmd = [
        sys.executable, "-m", "uvicorn",
        "src.coordinator.server:app",
        "--port", coord_port, "--reload"
    ]

    react_cmd = [
        "npm", "run", "start:dev"
    ]

    # Change to react-ui directory for React commands
    react_cwd = ROOT / "react-ui"

    # Start processes
    try:
        coord_proc = subprocess.Popen(coord_cmd, cwd=ROOT)
    except FileNotFoundError:
        print("ERROR: Could not start Coordinator (uvicorn missing?).")
        print("   -> pip install -r requirements.txt")
        sys.exit(1)

    # brief warmup so React can connect immediately
    time.sleep(3)

    try:
        react_proc = subprocess.Popen(react_cmd, cwd=react_cwd, shell=True)
    except FileNotFoundError:
        print("ERROR: Could not start React UI (npm missing?).")
        print("   -> Install Node.js and run: cd react-ui && npm install")
        # stop coordinator if React failed to start
        coord_proc.terminate()
        coord_proc.wait()
        sys.exit(1)

    # Wait & handle Ctrl+C
    try:
        coord_proc.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        try:
            coord_proc.terminate()
        except Exception:
            pass
        try:
            react_proc.terminate()
        except Exception:
            pass
        try:
            coord_proc.wait(timeout=5)
        except Exception:
            pass
        try:
            react_proc.wait(timeout=5)
        except Exception:
            pass

if __name__ == "__main__":
    main()
# Setup Scripts

Automated installation scripts for local development environment.

## Prerequisites

Before running setup scripts, ensure you have:

- **Python 3.8+**: `python --version`
- **Node.js 24 LTS recommended** — matches CI and `react-ui/.nvmrc`. Node 20 reached EOL in April 2026. react-scripts@5 breaks on any Node 17+ without the OpenSSL legacy flag, which is baked into `react-ui/package.json`: `node --version`
- **pip**: `pip --version`
- **npm**: `npm --version`

## Automated Setup (Recommended)

**Linux/macOS:**
```bash
chmod +x setup.sh
./setup.sh
```

**What it installs:**

**Python Dependencies:**
- `fastapi`, `uvicorn` - Web framework
- `langchain-core`, `langchain-ollama` - LLM integration
- `faiss-cpu`, `langchain-community` - Vector search (Phase 3 memory)
- `pydantic`, `python-dotenv` - Configuration management

**React Dependencies:**
- `react`, `react-dom` - Core framework
- `typescript` - Type safety
- `framer-motion` - Animations
- `tailwindcss` - Styling
- `@tsparticles/react` - Particle effects

## Manual Setup (Alternative)

If automated setup fails:

```bash
# Backend
pip install -r requirements.txt

# Frontend
cd react-ui
npm install
```

## Backend Launcher

For unified startup (backend + frontend), use:
```bash
python ../utils/run_react.py
```

## Troubleshooting

**Python Packages Fail:**
- Upgrade pip: `python -m pip install --upgrade pip`
- Use virtual environment: `python -m venv venv && source venv/bin/activate`
- Windows: `py -m venv venv && venv\Scripts\activate` (Windows only)

**npm Install Fails:**
- Clear cache: `npm cache clean --force`
- Delete `node_modules`: `rm -rf react-ui/node_modules`
- Retry: `cd react-ui && npm install`

**Permission Errors:**
- Linux/Mac: Use `sudo` for system-wide install (not recommended)
- Better: Use virtual environment (Python) and local npm install

## Next Steps

After setup completes:

1. **Configure Environment:**
   - Copy `.env.example` to `.env`
   - Set `OLLAMA_BASE`, `PERSONA_MODEL`
   - Optional: Add `BRAVE_API_KEY`, `MONGODB_URI`

2. **Start Ollama:**
   ```bash
   ollama serve
   ollama pull gemma2:9b-instruct-q5_K_M
   ```

3. **Run Application:**
   ```bash
   python ../utils/run_react.py
   ```

## Related Documentation

- [../../docs/development/TESTING_GUIDE.md](../../docs/development/TESTING_GUIDE.md) - Testing setup
- [../../CLAUDE.md](../../CLAUDE.md) - Full development guide
- [../../README.md](../../README.md) - Project overview

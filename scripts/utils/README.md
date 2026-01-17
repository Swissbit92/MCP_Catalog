# Python Utilities

Collection of Python utility scripts for development and maintenance.

## Unified Application Launcher

### run_react.py

**Purpose:** Start backend + frontend together in a single process

**Usage:**
```bash
python run_react.py
```

**What it does:**
1. Starts FastAPI backend on port 8000 (from .env `COORD_PORT`)
2. Starts React dev server on port 3000 (from .env `REACT_PORT`)
3. Provides graceful shutdown with `Ctrl+C`
4. Logs both services to console

**Configuration (.env):**
```bash
COORD_PORT=8000           # Backend port
REACT_PORT=3000           # Frontend port
COORD_URL=http://127.0.0.1:8000  # Backend URL for frontend
```

**When to use:**
- Local development (recommended)
- Testing full-stack changes
- Quick demo/prototype sessions

**When NOT to use:**
- Production (use Docker instead)
- Debugging single service (use `uvicorn` or `npm start:dev`)
- CI/CD pipelines (use dedicated commands)

## Quality Assurance

### validate_golden_qa.py

**Purpose:** Validate persona responses against golden test set

**Usage:**
```bash
python validate_golden_qa.py
```

**What it does:**
- Runs predefined test queries against personas
- Compares responses to expected outputs
- Generates validation report
- Detects regressions in persona quality

**Configuration:**
- Test cases: `tests/fixtures/golden_qa.json` (if exists)
- Reports: `test_reports/qa_validation_<timestamp>.json`

**Import example:**
```python
from validate_golden_qa import run_validation, compare_responses

# Run validation suite
results = run_validation(persona_key="eeva", test_set="basic")

# Compare specific responses
similarity = compare_responses(expected, actual)
```

## Docker Maintenance

### cleanup_orphan_containers.py

**Purpose:** Remove orphaned Docker containers and networks

**Usage:**
```bash
python cleanup_orphan_containers.py
```

**What it does:**
- Identifies stopped MCP containers
- Removes orphaned networks
- Cleans up dangling volumes
- Preserves active containers

**When to use:**
- After many dev sessions with MCP servers
- "Network not found" errors
- Disk space cleanup
- Before production deployment

**Import example:**
```python
from cleanup_orphan_containers import clean_orphans, list_orphans

# List orphaned containers
orphans = list_orphans(project_prefix="mcp_catalog")

# Clean up
removed = clean_orphans(dry_run=False)
```

## Security Validation

### test_security_hardening.py

**Purpose:** Validate security configurations and hardening

**Usage:**
```bash
python test_security_hardening.py
```

**What it tests:**
- Environment variable sanitization
- SQL injection prevention
- XSS attack mitigation
- CORS configuration
- API input validation
- Docker security settings

**Import example:**
```python
from test_security_hardening import run_security_tests, check_cors

# Run all security tests
results = run_security_tests()

# Check specific security aspect
cors_valid = check_cors(allowed_origins=["http://localhost:3000"])
```

**When to run:**
- Before production deployment
- After security-related changes
- During security audits
- As part of CI/CD pipeline

## Best Practices

### Running Scripts

**From project root:**
```bash
# Correct
python scripts/utils/run_react.py

# Incorrect (old path)
python run_react.py  # ❌ File not found
```

**From scripts/utils/ directory:**
```bash
cd scripts/utils
python run_react.py  # ✅ Works
python validate_golden_qa.py  # ✅ Works
```

### Importing Utilities

**In other Python files:**
```python
# Correct (relative import from project root)
from scripts.utils.validate_golden_qa import run_validation

# Correct (if scripts/utils in PYTHONPATH)
from validate_golden_qa import run_validation
```

**Adding to PYTHONPATH:**
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/scripts/utils"
python -c "from validate_golden_qa import run_validation"
```

## Related Documentation

- [../../CLAUDE.md](../../CLAUDE.md) - Development commands
- [../../docs/development/TESTING_GUIDE.md](../../docs/development/TESTING_GUIDE.md) - Testing guide
- [../../README.md](../../README.md) - Project overview

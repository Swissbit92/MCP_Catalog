# CI/CD Getting Started Guide

**Audience:** Developers new to CI/CD or GitHub Actions
**Reading Time:** 10 minutes
**Prerequisites:** Basic Git knowledge

---

## What is CI/CD?

**CI/CD = Continuous Integration / Continuous Deployment**

**Simple explanation:** Automated quality checks that run every time you push code to GitHub.

**Think of it like:** A robot assistant that automatically tests your code, builds your app, and checks for problems - so you don't have to remember to do it manually.

**Real-world analogy:**
- **Without CI/CD:** You cook a meal, serve it to guests, then realize you forgot to taste it (bug in production)
- **With CI/CD:** A robot chef automatically tastes every dish before serving (catches bugs before users see them)

---

## Why MCP Coordinator Has CI/CD

### Problem Without CI/CD

**Scenario:** You refactor `tool_definitions.py`

```
❌ Manual Process:
1. You push code to GitHub
2. You forget to run tests
3. You deploy to production
4. Users report: "Search is broken!"
5. You spend 2 hours debugging
6. You discover: Intent classification broke
7. You roll back and fix
8. Total time wasted: 2+ hours
```

**User impact:** Production was broken for 2 hours

### Solution With CI/CD

**Same scenario with automation:**

```
✅ Automated Process:
1. You push code to GitHub
2. GitHub Actions automatically runs
3. Intent classification tests fail (360 tests)
4. You get notification: "❌ CI failed"
5. You see which test failed immediately
6. You fix the bug in 5 minutes
7. Push again, CI passes ✅
8. Total time: 10 minutes
```

**User impact:** Zero (bug caught before deployment)

**Time saved:** 2 hours → 10 minutes (12x faster)

---

## What Our CI/CD Pipeline Does

When you push code to GitHub, **5 automated jobs** run in parallel:

### Job 1: Backend Tests 🐍
```bash
Runs: All Python tests (10 test files)
Time: ~3 minutes
```

**What it tests:**
- ✅ Server startup works
- ✅ Tool calling works (MongoDB, Brave MCP)
- ✅ Citations are validated correctly
- ✅ Intent classification works (360 test cases)
- ✅ Persona schema validation works
- ✅ Phase 3 memory system works (11 tests)

**Example failure:**
```
❌ test_intent_classification.py failed

Query: "What is the Bitcoin price?"
Expected: NEEDS_MONGODB
Actual: NEEDS_NEITHER

→ You broke the intent classifier!
```

### Job 2: Frontend Tests ⚛️
```bash
Runs: All React component tests
Time: ~5 minutes
Coverage: Tracks what % of code is tested
```

**What it tests:**
- ✅ All React components render correctly
- ✅ MessageBubble displays messages properly
- ✅ CharacterCard shows persona info correctly
- ✅ Header navigation works
- ✅ Mobile menu opens/closes
- ✅ Test coverage: 68.42% (tracked)

**Example failure:**
```
❌ MessageBubble.test.tsx failed

Error: Cannot read property 'content' of undefined

→ You changed the message props structure!
```

### Job 3: Frontend Build 🏗️
```bash
Runs: Production build (npm run build)
Time: ~4 minutes
```

**What it checks:**
- ✅ TypeScript compiles without errors
- ✅ All imports resolve correctly
- ✅ Webpack bundles successfully
- ✅ Production bundle size is reasonable

**Example failure:**
```
❌ Build failed

Error: Module not found: Can't resolve './HeaderVisuals'

→ You have a missing import!
```

### Job 4: Code Quality 📊
```bash
Runs: Syntax checks, TODO tracking
Time: ~1 minute
```

**What it checks:**
- ✅ Python syntax is valid
- ✅ No obvious syntax errors
- ✅ Tracks TODO comments (technical debt)
- ✅ Counts files (monitors growth)

**Example failure:**
```
❌ Python syntax error

File "persona_loader.py", line 42
    def _load_card(path:
                        ^
SyntaxError: invalid syntax

→ You have a syntax error!
```

### Job 5: Security 🔒
```bash
Runs: Vulnerability scans, secret detection
Time: ~1 minute
```

**What it checks:**
- ✅ No npm package vulnerabilities (high-severity)
- ✅ No hardcoded API keys in code
- ✅ No passwords in source files
- ✅ No secret tokens committed

**Example failure:**
```
❌ Security issue detected

Found in config.py:
BRAVE_API_KEY = "sk_live_abc123..."

→ You committed an API key!
```

---

## How GitHub Actions Works (Step-by-Step)

### Step 1: You Push Code
```bash
git add .
git commit -m "Fix persona loading bug"
git push origin main
```

### Step 2: GitHub Detects the Push
- GitHub sees new commits on `main` branch
- Reads `.github/workflows/ci.yml` config
- Triggers workflow automatically

### Step 3: GitHub Creates Virtual Machines
```
GitHub spins up 5 separate Ubuntu VMs:
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ VM 1        │ │ VM 2        │ │ VM 3        │
│ Backend     │ │ Frontend    │ │ Build       │
│ Tests       │ │ Tests       │ │             │
└─────────────┘ └─────────────┘ └─────────────┘

┌─────────────┐ ┌─────────────┐
│ VM 4        │ │ VM 5        │
│ Code        │ │ Security    │
│ Quality     │ │             │
└─────────────┘ └─────────────┘
```

Each VM is a **fresh Ubuntu Linux machine** (completely isolated).

### Step 4: Each VM Runs Its Steps
```yaml
VM 1 (Backend Tests):
  Step 1: Download your code from GitHub
  Step 2: Install Python 3.11
  Step 3: Install dependencies (pip install)
  Step 4: Run all Python tests
  Step 5: Report results ✅ or ❌
```

### Step 5: You See Results
**GitHub shows you the results:**

```
✅ All checks have passed (5/5)

Backend Tests        ✅ 2m 34s
Frontend Tests       ✅ 4m 12s
Frontend Build       ✅ 3m 45s
Code Quality         ✅ 1m 08s
Security Checks      ✅ 0m 52s

Total time: 4m 12s (parallel)
```

Or if something failed:

```
❌ Some checks failed (4/5)

Backend Tests        ✅ 2m 34s
Frontend Tests       ❌ 4m 12s  ← FAILED
Frontend Build       ✅ 3m 45s
Code Quality         ✅ 1m 08s
Security Checks      ✅ 0m 52s
```

---

## Viewing CI Results

### Option 1: GitHub Actions Tab
```
1. Go to your repository on GitHub
2. Click "Actions" tab at the top
3. See list of all workflow runs
```

**What you'll see:**
```
Workflow runs

✅ Fix persona loading bug         #123  main  2m ago   4m 12s
✅ Add CI/CD pipeline              #122  main  1h ago   3m 45s
❌ Refactor tool_definitions       #121  main  3h ago   2m 18s
✅ Split Header component          #120  main  5h ago   4m 32s
```

**Click any run to see detailed logs:**
```
✅ Backend Tests (2m 34s)

  ✅ Set up job
  ✅ Checkout code
  ✅ Set up Python 3.11
  ✅ Install dependencies
  ✅ Run backend unit tests
     - test_server.py ...................... PASSED
     - test_tool_calling.py ................ PASSED
     - test_intent_classification.py ....... PASSED (360 tests)
  ✅ Complete job
```

### Option 2: Commit Page
```
1. Go to your repository
2. Click "Commits" (or click on any commit)
3. See status checks inline
```

**What you'll see:**
```
commit 4fac94ba - Fix Phase 3 fact extraction bug

✅ All checks have passed
   5 successful checks

   ✅ Backend Tests
   ✅ Frontend Tests
   ✅ Frontend Build
   ✅ Code Quality Checks
   ✅ Security Checks
```

### Option 3: Pull Request Checks
```
1. Open any pull request
2. Scroll to "Checks" section
3. See all status checks
```

**What you'll see:**
```
Pull Request #42: Add async conversion

All checks have passed
10 successful checks

✅ CI/CD Pipeline
  ✅ Backend Tests
  ✅ Frontend Tests
  ✅ Frontend Build
  ✅ Code Quality
  ✅ Security

✅ PR Checks
  ✅ PR Size Check (25 files changed - OK)
  ✅ File Naming (all files snake_case - OK)
  ✅ Coverage Diff (70.1% → 72.3% +2.2%)
  ✅ Breaking Changes (none detected)
  ✅ Code Review (1 approval required)
```

---

## What Happens When Tests Fail

### Example Failure Scenario

**1. You push code:**
```bash
git add src/coordinator/tools/intent_classifier.py
git commit -m "Refactor intent classification"
git push origin main
```

**2. GitHub runs CI automatically**

**3. Tests fail:**
```
❌ Backend Tests failed (2m 15s)

FAILED tests/integration/test_intent_classification.py::test_bitcoin_price_query

AssertionError: Intent classification error
  Query: "What is the current Bitcoin price?"
  Expected: QueryIntent.NEEDS_MONGODB
  Actual: QueryIntent.NEEDS_NEITHER

  The classifier is not detecting Bitcoin price queries correctly!
```

**4. You get notified:**
- 📧 Email: "GitHub Actions: CI failed on main"
- 🔔 GitHub notification
- (Optional: Slack/Discord webhook)

**5. Deployment is blocked:**
```
⛔ Cannot deploy to production
   Required check "Backend Tests" must pass
```

**6. You fix the bug:**
```python
# src/coordinator/tools/intent_classifier.py
def classify_query_intent(query: str, persona_rarity: str):
    query_lower = query.lower()

    # FIX: Was missing this check!
    if "bitcoin" in query_lower and "price" in query_lower:
        return QueryIntent.NEEDS_MONGODB

    # ... rest of logic
```

**7. You push the fix:**
```bash
git add src/coordinator/tools/intent_classifier.py
git commit -m "Fix: Restore Bitcoin price detection"
git push origin main
```

**8. CI re-runs automatically:**
```
✅ All checks have passed (5/5)

Backend Tests        ✅ 2m 18s
  → test_intent_classification.py: 360/360 PASSED ✅

Safe to deploy!
```

**Total time to fix:** 5-10 minutes (instead of discovering in production later)

---

## Understanding the Configuration Files

### `.github/workflows/ci.yml` (Main Pipeline)

**This file defines WHAT runs and WHEN:**

```yaml
# WHEN to run
on:
  push:
    branches: [ main, develop ]      # Run on pushes to main/develop
  pull_request:
    branches: [ main, develop ]      # Run on PRs to main/develop

# WHAT to run
jobs:
  backend-tests:                     # Job name
    name: Backend Tests (Python)     # Display name
    runs-on: ubuntu-latest           # Use Ubuntu VM
    timeout-minutes: 15              # Kill if takes >15 min

    steps:                           # What to do (in order)
      - name: Checkout code          # Step 1
        uses: actions/checkout@v4    # Download your repo

      - name: Set up Python 3.11     # Step 2
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'               # Cache dependencies

      - name: Install dependencies   # Step 3
        run: pip install -r requirements.txt

      - name: Run tests              # Step 4
        run: python tests/backend/coordinator/test_server.py
```

**Key concepts:**

- `on:` = Triggers (when to run)
- `jobs:` = What to run (can run in parallel)
- `steps:` = Commands to execute (run in sequence)
- `uses:` = Pre-built actions (from GitHub marketplace)
- `run:` = Shell commands (bash)
- `with:` = Configuration for actions

### `.github/workflows/pr-checks.yml` (PR-Specific)

**This file runs ONLY on pull requests:**

```yaml
on:
  pull_request:                      # Only on PRs
    types: [opened, synchronize]     # When PR opened or updated

jobs:
  pr-size:
    name: PR Size Check
    runs-on: ubuntu-latest

    steps:
      - name: Check PR size
        run: |
          FILES=$(git diff --name-only origin/main...HEAD | wc -l)

          if [ "$FILES" -gt 50 ]; then
            echo "⚠️  Warning: PR changes $FILES files"
            echo "Recommended: Keep PRs under 50 files for easier review"
          fi
```

**Why separate file:**
- PR-specific checks don't apply to direct pushes
- Keeps main CI file focused
- Easier to enable/disable PR checks

---

## Caching: Why CI is Fast

### Without Caching (Slow)
```bash
# EVERY run downloads ALL dependencies
pip install -r requirements.txt     # 2 minutes
npm install                          # 3 minutes

Total wait: 5 minutes PER RUN
```

If you push 20 times/day = **100 minutes wasted** downloading the same packages!

### With Caching (Fast)
```yaml
- uses: actions/setup-python@v5
  with:
    cache: 'pip'  # Magic line that enables caching
```

**How it works:**
```
First run:
  1. GitHub: "requirements.txt hash = abc123"
  2. GitHub: "No cache found, downloading packages..."
  3. pip install -r requirements.txt (2 minutes)
  4. GitHub: "Caching packages with key abc123"

Second run (requirements.txt unchanged):
  1. GitHub: "requirements.txt hash = abc123"
  2. GitHub: "Cache found! Restoring packages..."
  3. pip install -r requirements.txt (10 seconds - uses cache!)

Third run (you add a new package):
  1. GitHub: "requirements.txt hash = xyz789" (changed!)
  2. GitHub: "No cache for xyz789, downloading..."
  3. pip install -r requirements.txt (2 minutes - new packages)
  4. GitHub: "Caching packages with key xyz789"
```

**Result:**
- First run: 2 minutes (downloads)
- Subsequent runs: 10 seconds (cached)
- **Speedup: 12x faster** ⚡

**Cache invalidation:**
- Cache key = hash of `requirements.txt`
- If file changes → new hash → download again
- If unchanged → same hash → use cache

---

## Cost (Spoiler: It's Free)

### GitHub Actions Pricing

**Public repositories (this project):**
- ✅ **Unlimited free minutes**
- ✅ **Unlimited free storage**
- ✅ **No cost whatsoever**

**Private repositories:**
- 2,000 free minutes/month
- Then $0.008/minute (~$0.48/hour)

### Our Usage
```
Per push:
  Backend Tests:    3 minutes
  Frontend Tests:   5 minutes
  Frontend Build:   4 minutes
  Code Quality:     1 minute
  Security:         1 minute

  Total (parallel): 5 minutes (longest job)

Monthly (50 pushes):
  50 pushes × 5 min = 250 minutes
  Cost: $0 (public repo)
```

**Why parallel matters:**
```
If run sequentially: 3+5+4+1+1 = 14 minutes/push
If run parallel:     max(3,5,4,1,1) = 5 minutes/push

Speedup: 2.8x faster
```

---

## Common Questions

### Q: "Do I need to do anything to trigger CI?"
**A:** No! It runs automatically when you push to `main` or `develop`, or open a PR.

### Q: "What if I want to skip CI for a commit?"
**A:** Add `[skip ci]` to your commit message:
```bash
git commit -m "Update README [skip ci]"
```

**When to use:**
- Documentation-only changes
- README updates
- Comment changes

**When NOT to use:**
- Any code changes (tests should always run)

### Q: "Can I run CI locally before pushing?"
**A:** Yes! Run the same commands CI runs:

```bash
# Backend tests (what CI runs)
python tests/backend/coordinator/test_server.py
python tests/backend/coordinator/test_tool_calling.py
# ... etc

# Frontend tests (what CI runs)
cd react-ui
npm test -- --watchAll=false

# Frontend build (what CI runs)
npm run build
```

### Q: "Why does CI sometimes take longer?"
**A:** Several reasons:
- Cold start (no cache available)
- GitHub Actions queue (busy time)
- Slow network (downloading packages)
- More tests were added

**Typical range:** 4-10 minutes

### Q: "What if CI fails but I know it's a fluke?"
**A:** You can re-run failed jobs:
```
1. Go to Actions tab
2. Click the failed run
3. Click "Re-run failed jobs"
```

**Flaky test reasons:**
- Network timeout (rare)
- Race condition (needs fixing)
- GitHub Actions hiccup (rare)

### Q: "Can I test specific files instead of everything?"
**A:** Not in CI (it always runs everything), but locally:
```bash
# Test specific file
python tests/backend/coordinator/test_server.py

# Test specific React component
npm test -- MessageBubble --watchAll=false
```

---

## Troubleshooting

### CI is failing but works locally

**Cause:** Environment differences

**Check:**
1. Python version (CI uses 3.11, are you using 3.11?)
2. Node version (CI uses 20, are you using 20?)
3. Missing dependencies (did you update requirements.txt?)
4. OS differences (CI uses Linux, are you on Windows?)

**Fix:**
```bash
# Match CI environment locally
pyenv install 3.11
pyenv local 3.11

nvm install 20
nvm use 20
```

### CI is timing out (>15 minutes)

**Cause:** Tests are taking too long

**Check:**
1. Infinite loop in test?
2. Network request without timeout?
3. Too many tests added?

**Fix:**
```yaml
# Increase timeout temporarily
timeout-minutes: 30  # Was 15
```

### Cache is not working

**Cause:** Cache key changed but shouldn't have

**Check:**
```bash
# Did requirements.txt change?
git diff origin/main -- requirements.txt

# Did package-lock.json change?
git diff origin/main -- react-ui/package-lock.json
```

**Fix:** Commit the lockfile changes properly

### Getting too many notifications

**GitHub Settings:**
```
Settings → Notifications → GitHub Actions
  → Only notify me: On failure
```

---

## Next Steps

### 1. Trigger Your First CI Run
```bash
# Make a small change
echo "# CI Test" >> README.md

# Commit and push
git add README.md
git commit -m "Test CI pipeline"
git push origin main

# Watch it run!
# Go to: https://github.com/<your-repo>/actions
```

### 2. View the Results
1. Open GitHub Actions tab
2. Click the workflow run
3. Explore each job's logs
4. See what commands are executed

### 3. Make CI Fail (Intentionally)
```bash
# Break a test
# Open tests/backend/coordinator/test_server.py
# Add: assert False, "Intentional failure for testing"

git add tests/backend/coordinator/test_server.py
git commit -m "Test CI failure"
git push origin main

# Watch it fail!
# Then fix it and push again
```

### 4. Read Full Documentation
- **Technical details:** `.github/CICD_DOCUMENTATION.md`
- **Architecture summary:** `AI_documentation/01_implementation_history/ARCHITECTURE_IMPROVEMENTS_SUMMARY.md`

---

## Summary

**What is CI/CD:**
- Automated testing on every push
- Runs 5 jobs in parallel (~5 minutes)
- Catches bugs before production

**Why it matters:**
- Saves hours of manual testing
- Prevents bugs from reaching users
- Enforces quality standards
- Free for public repos

**How it works:**
1. You push → GitHub detects it
2. Creates 5 VMs → Runs tests
3. Reports results → Green ✅ or Red ❌
4. Blocks deployment if failing

**What you need to do:**
- Nothing! It's automatic
- Just fix failures when they occur
- Review results before merging

**Key benefit for this project:**
- You refactored 4 massive files today
- CI automatically verified nothing broke
- Without it: Hours of manual testing
- With it: Automatic verification in 5 minutes

---

**Next:** Make a test commit and watch CI run!

```bash
git commit -m "Update documentation [skip ci]" --allow-empty
git push origin main
```

Then visit: `https://github.com/<your-username>/MCP_Catalog/actions`

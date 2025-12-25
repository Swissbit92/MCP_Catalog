# CI/CD Pipeline Documentation

**For beginners:** See [CICD_GETTING_STARTED.md](CICD_GETTING_STARTED.md) for a friendly introduction to CI/CD concepts.

**This document:** Technical reference for the CI/CD pipeline configuration and maintenance.

---

## Overview

This repository uses GitHub Actions for continuous integration and deployment. The pipeline automatically runs tests, builds the application, and performs code quality checks on every push and pull request.

**Quick stats:**
- **5 automated jobs** run in parallel
- **~5 minutes** per push (typical)
- **Free** (public repository)
- **360+ tests** executed automatically
- **68%+ code coverage** tracked

## Workflows

### 1. Main CI/CD Pipeline (`.github/workflows/ci.yml`)

**Triggered on:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

**Jobs:**

#### Backend Tests (Python)
- **Runtime**: Ubuntu Latest, Python 3.11
- **Timeout**: 15 minutes
- **Steps**:
  1. Checkout code
  2. Set up Python 3.11 with pip caching
  3. Install dependencies from `requirements.txt`
  4. Run backend unit tests (8 test files)
  5. Run integration tests (2 test files)

**Test Files Executed:**
- `test_server.py` - FastAPI server tests
- `test_tool_calling.py` - MCP tool calling functionality
- `test_citation_validation.py` - Brave search citation validation
- `test_synthesis_prompt.py` - MongoDB/Brave synthesis prompts
- `test_summarization.py` - Conversation summarization
- `test_persona_schema.py` - Pydantic schema validation
- `test_persona_truncation.py` - Token truncation logic
- `test_repositories.py` - Repository pattern tests
- `test_intent_classification.py` - Intent classifier (360 test cases)
- `test_phase3_simple.py` - Phase 3 memory system (11 component tests)

#### Frontend Tests (React)
- **Runtime**: Ubuntu Latest, Node.js 20
- **Timeout**: 15 minutes
- **Steps**:
  1. Checkout code
  2. Set up Node.js 20 with npm caching
  3. Install dependencies with `npm ci`
  4. Run Jest tests with coverage reporting
  5. Upload coverage artifacts

**Coverage Reporters:**
- Text (console output)
- LCOV (for coverage visualization)

#### Frontend Build (Production)
- **Runtime**: Ubuntu Latest, Node.js 20
- **Timeout**: 10 minutes
- **Steps**:
  1. Checkout code
  2. Set up Node.js 20 with npm caching
  3. Install dependencies with `npm ci`
  4. Build production bundle with `npm run build`
  5. Upload build artifacts

**Build Validation:**
- Ensures production build succeeds
- Verifies no TypeScript errors
- Validates webpack configuration

#### Code Quality Checks
- **Runtime**: Ubuntu Latest, Python 3.11
- **Timeout**: 10 minutes
- **Steps**:
  1. Check Python syntax (compileall)
  2. Count Python files in src/
  3. Search for TODO comments

#### Security Checks
- **Runtime**: Ubuntu Latest
- **Timeout**: 10 minutes
- **Steps**:
  1. Run `npm audit` on frontend dependencies (high-severity only)
  2. Search for hardcoded secrets in source code

### 2. Pull Request Checks (`.github/workflows/pr-checks.yml`)

**Triggered on:**
- Pull request opened, synchronized, or reopened

**Jobs:**

#### PR Size Check
- Counts changed files (warns if >50)
- Counts changed lines (warns if >1000)
- Promotes smaller, focused PRs

#### File Naming Convention Check
- **Python**: Enforces `snake_case` for `.py` files
- **React**: Checks `PascalCase` for `.tsx` components
- Fails if Python files use incorrect casing

#### Test Coverage Diff
- Runs frontend tests with coverage
- Extracts coverage percentage
- Reports coverage change (future enhancement: compare with base branch)

#### Breaking Changes Detection
- **Database Schema**: Detects changes to repository files
- **API Contract**: Detects changes to `schemas.py`
- Warns reviewers about potential breaking changes

## Running Tests Locally

### Backend Tests
```bash
# Run all backend unit tests
python tests/backend/coordinator/test_server.py
python tests/backend/coordinator/test_tool_calling.py
python tests/backend/coordinator/test_citation_validation.py
python tests/backend/coordinator/test_synthesis_prompt.py
python tests/backend/coordinator/test_summarization.py
python tests/backend/coordinator/test_persona_schema.py
python tests/backend/coordinator/test_persona_truncation.py
python tests/backend/coordinator/test_repositories.py

# Run integration tests
python tests/integration/test_intent_classification.py
python tests/integration/test_phase3_simple.py
```

### Frontend Tests
```bash
cd react-ui

# Run tests once
npm test -- --watchAll=false

# Run tests with coverage
npm test -- --watchAll=false --coverage

# Run specific test file
npm test -- --testPathPattern="MessageBubble" --watchAll=false
```

### Production Build
```bash
cd react-ui
npm run build
```

## Artifacts

The CI pipeline uploads the following artifacts:

1. **frontend-coverage** - Jest coverage reports (LCOV format)
2. **frontend-build** - Production build directory

**Artifact Retention**: 30 days (GitHub default)

## Performance

**Typical Run Times:**
- Backend Tests: 3-5 minutes
- Frontend Tests: 5-7 minutes
- Frontend Build: 3-4 minutes
- Code Quality: 1-2 minutes
- PR Checks: 2-3 minutes

**Total CI Time**: ~10-15 minutes per push

## Caching Strategy

**Python (`pip`):**
- Cache key: Python version + `requirements.txt` hash
- Speeds up dependency installation by ~80%

**Node.js (`npm`):**
- Cache key: Node version + `package-lock.json` hash
- Speeds up dependency installation by ~70%

## Future Enhancements

1. **Code Coverage Enforcement**
   - Set minimum coverage thresholds (e.g., 70%)
   - Fail CI if coverage decreases

2. **E2E Tests**
   - Add Playwright/Cypress for end-to-end testing
   - Test full user flows (gacha pull, chat, session management)

3. **Performance Testing**
   - Lighthouse CI for frontend performance
   - Load testing for backend API

4. **Deployment**
   - Automatic deployment to staging on PR merge
   - Production deployment on main branch push

5. **Notifications**
   - Slack/Discord notifications for failures
   - Coverage report comments on PRs

6. **Dependency Updates**
   - Dependabot for automated dependency updates
   - Automated security patching

## Troubleshooting

### Test Failures

**Backend tests failing:**
- Check Python version (must be 3.11+)
- Verify all dependencies installed: `pip install -r requirements.txt`
- Check for missing environment variables

**Frontend tests failing:**
- Check Node version (must be 20+)
- Clear node_modules: `rm -rf react-ui/node_modules && npm ci`
- Verify Jest configuration in `package.json`

### Build Failures

**Frontend build failing:**
- Check for TypeScript errors
- Verify all imports resolve correctly
- Check webpack configuration

### Timeout Issues

**Job timeout (15 minutes):**
- Check for infinite loops in tests
- Verify network requests have proper timeouts
- Consider splitting tests into smaller jobs

## Monitoring

**GitHub Actions Dashboard:**
- View all workflow runs: Repository → Actions tab
- Filter by workflow, branch, or status
- Download artifacts from completed runs

**Coverage Reports:**
- Download `frontend-coverage` artifact
- Open `lcov-report/index.html` in browser
- View line-by-line coverage data

## Best Practices

1. **Run tests locally before pushing**
   - Catch failures early
   - Faster feedback loop

2. **Keep PRs small and focused**
   - Easier to review
   - Faster CI runs
   - Fewer merge conflicts

3. **Write tests for new features**
   - Maintain coverage levels
   - Prevent regressions

4. **Fix failing tests immediately**
   - Don't let main branch break
   - Maintain team velocity

5. **Review CI logs for warnings**
   - npm audit warnings
   - TODO comments
   - Potential breaking changes

## Related Documentation

- `README.md` - Project setup and overview
- `CLAUDE.md` - Development guidelines for Claude Code
- `CHANGELOG.md` - Version history and changes
- `react-ui/package.json` - Frontend test configuration

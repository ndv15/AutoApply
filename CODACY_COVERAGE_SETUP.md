# Codacy Coverage Reporting Setup

## Overview
This document describes the Codacy coverage integration for the AutoApply Python project. The integration automatically generates and uploads code coverage reports to Codacy on every push and pull request affecting source or test code.

## Workflow Configuration

### File Location
`.github/workflows/codacy-coverage.yml`

### Triggers
The workflow runs on:
- **Pushes to `main`** branch (when source/test files change)
- **Pull requests to `main`** branch (when source/test files change)

### Path Filters
Only triggers when these paths are modified:
- `autoapply/**` - Application source code
- `tests/**` - Test files
- `pyproject.toml` - Project dependencies

This ensures the workflow doesn't run unnecessarily for documentation-only changes.

## Workflow Steps

### 1. Checkout Code
```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0
```
Full git history is fetched for accurate coverage tracking.

### 2. Set Up Python 3.11
```yaml
- uses: actions/setup-python@v5
  with:
    python-version: '3.11'
    cache: 'pip'
```
Uses pip caching to speed up dependency installation.

### 3. Install Dependencies
```bash
pip install -e .
pip install -e ".[dev]"
```
Installs:
- Production dependencies from `pyproject.toml`
- Development dependencies including `pytest>=8.0` and `pytest-cov>=4.1`

### 4. Run Tests with Coverage
```bash
pytest --cov=autoapply --cov-report=xml:coverage.xml --cov-report=term -v
```

**Options explained:**
- `--cov=autoapply` - Measure coverage for the `autoapply` package
- `--cov-report=xml:coverage.xml` - Generate Cobertura XML format (required by Codacy)
- `--cov-report=term` - Display coverage summary in terminal
- `-v` - Verbose output

### 5. Upload Coverage to Codacy
```bash
bash <(curl -Ls https://coverage.codacy.com/get.sh) report -r coverage.xml
```

**Features:**
- Uses official Codacy Coverage Reporter bash script
- Automatically downloads latest reporter version
- Requires `CODACY_PROJECT_TOKEN` secret
- Graceful fallback if token not configured (warning, not failure)

### 6. Archive Coverage Report
```yaml
- uses: actions/upload-artifact@v4
  with:
    name: coverage-report
    path: coverage.xml
    retention-days: 30
```
Saves coverage.xml as GitHub Actions artifact for 30 days.

## Setup Instructions

### Prerequisites
1. ✅ Codacy account with AutoApply repository added
2. ✅ pytest and pytest-cov installed (already in pyproject.toml)
3. ⏳ Codacy Project Token (see below)

### Step 1: Get Codacy Project Token

1. Go to your Codacy dashboard: https://app.codacy.com
2. Navigate to your `AutoApply` repository
3. Go to **Settings** → **Coverage** → **API Tokens**
4. Copy the **Project API Token**

### Step 2: Add Token to GitHub Secrets

1. Go to GitHub repository: https://github.com/ndv15/AutoApply
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `CODACY_PROJECT_TOKEN`
5. Value: Paste the token from Codacy
6. Click **Add secret**

⚠️ **Security Note**: Never commit the token to code or logs. The workflow is configured to handle missing tokens gracefully.

### Step 3: Enable the Workflow

The workflow is already committed. It will automatically run on:
- Next push to `main` branch (if source/tests changed)
- Next PR to `main` branch (if source/tests changed)

### Step 4: Verify Setup

After the first workflow run:

1. **Check GitHub Actions**
   - Go to: https://github.com/ndv15/AutoApply/actions
   - Look for "Codacy Coverage Reporter" workflow
   - Verify it completes successfully (green checkmark)

2. **Check Codacy Dashboard**
   - Go to: https://app.codacy.com/gh/ndv15/AutoApply
   - Navigate to **Coverage** tab
   - Verify coverage data appears for the commit
   - Look for coverage percentage and file-by-file breakdown

3. **Check Coverage Artifacts**
   - In GitHub Actions workflow run page
   - Look for "coverage-report" artifact
   - Download to inspect coverage.xml locally if needed

## Coverage Metrics

### Current Test Files
```
tests/
├── test_fsm.py              # State machine tests
├── test_quota.py            # Quota system tests
├── test_validators.py       # AMOT/Skills validators tests
└── integration/
    └── test_e2e_pipeline.py # End-to-end pipeline tests
```

### Coverage Targets
The workflow measures coverage for all modules in `autoapply/`:
- `autoapply/domain/` - Domain models and validators
- `autoapply/services` - Business logic services
- `autoapply/orchestration/` - Workflow orchestration
- `autoapply/providers/` - LLM provider adapters
- `autoapply/store/` - Data persistence
- `autoapply/config/` - Configuration management
- `autoapply/cli/` - Command-line interface
- `autoapply/ingestion/` - Document parsing
- `autoapply/util/` - Utilities

### Expected Coverage
- **Unit tests**: High coverage (>80%) for domain, validators, services
- **Integration tests**: Medium coverage (50-70%) for orchestration
- **CLI tests**: Lower coverage (30-50%) - manual testing heavy

## Troubleshooting

### Issue: Workflow doesn't trigger

**Cause**: No changes to `autoapply/`, `tests/`, or `pyproject.toml`

**Solution**: This is expected behavior. The workflow only runs when source or test code changes. Documentation-only commits won't trigger it.

### Issue: "CODACY_PROJECT_TOKEN secret not set"

**Cause**: Token not added to GitHub Secrets

**Solution**: 
1. Follow "Step 2: Add Token to GitHub Secrets" above
2. Re-run the workflow from GitHub Actions UI
3. Verify the warning becomes "Uploading coverage report to Codacy..."

### Issue: Tests fail during coverage run

**Cause**: Test failures or missing dependencies

**Solution**:
1. Run tests locally: `pytest --cov=autoapply --cov-report=term`
2. Fix any failing tests
3. Ensure all dependencies installed: `pip install -e ".[dev]"`
4. Push fix to trigger workflow again

### Issue: Coverage upload fails

**Possible Causes:**
1. Invalid Codacy token
2. Codacy API temporarily unavailable
3. coverage.xml corrupted or missing

**Solutions:**
1. Verify token in GitHub Secrets matches Codacy dashboard
2. Check Codacy status page: https://status.codacy.com
3. Download coverage-report artifact from workflow run to inspect XML
4. Re-run workflow after checking issues

### Issue: Coverage not showing on PRs

**Cause**: Need coverage for both PR head and common ancestor commits

**Solution**: 
1. Ensure workflow ran successfully on both commits
2. Check Codacy dashboard → Coverage → "Test your integration"
3. Look for commit status (should be "Processed")
4. Wait 5-10 minutes for Codacy to calculate PR metrics

## Integration with Existing Workflows

### Compatibility

✅ **No conflicts** with existing workflows:
- `docs-guard.yml` - Only runs on docs changes
- `deepseek-reviewer.yml` - Runs on all file types

✅ **Path filters prevent**:
- Running on documentation-only changes
- Unnecessary workflow executions
- Resource waste

✅ **Non-blocking**:
- Graceful failure if token not set (warning only)
- Doesn't block PRs if coverage upload fails
- Independent from other checks

### Workflow Execution Matrix

| Change Type | docs-guard | deepseek-reviewer | codacy-coverage |
|-------------|------------|-------------------|-----------------|
| `docs/*.md` | ✅ Runs     | ✅ Runs            | ❌ Skipped      |
| `autoapply/*.py` | ❌ Skipped | ✅ Runs            | ✅ Runs         |
| `tests/*.py` | ❌ Skipped | ✅ Runs            | ✅ Runs         |
| `README.md` | ❌ Skipped | ✅ Runs            | ❌ Skipped      |
| `pyproject.toml` | ❌ Skipped | ✅ Runs            | ✅ Runs         |

## Codacy Dashboard Usage

### Viewing Coverage

1. **Repository Dashboard**
   - Overall coverage percentage
   - Coverage trend over time
   - Files with low coverage

2. **Pull Request View**
   - Coverage Delta (change from base branch)
   - Diff Coverage (new lines covered percentage)
   - Files affected with coverage changes

3. **Commit View**
   - Coverage for specific commit
   - Line-by-line coverage in file view
   - Untested lines highlighted

### Setting Coverage Goals

In Codacy dashboard → Settings → Coverage:
- **Coverage Goal**: Set target percentage (e.g., 70%)
- **Coverage Change Threshold**: Maximum allowed decrease (e.g., -2%)
- **Diff Coverage Threshold**: Minimum coverage for new code (e.g., 80%)

### Coverage Integration Status

Check: Repository Settings → Coverage → "Test your integration"

**Status meanings:**
- ✅ **Processed**: Coverage successfully received and processed
- ⏳ **Pending**: Waiting for file path validation
- ❌ **Commit not found**: Codacy hasn't received webhook yet (wait 5-10 min)
- ❌ **Branch not enabled**: Enable branch on Codacy
- ❌ **Commit not analyzed**: Wait for static analysis to complete

## Best Practices

### Writing Testable Code
1. Keep functions small and focused
2. Avoid deeply nested logic
3. Use dependency injection for testability
4. Separate I/O from business logic

### Improving Coverage
1. **Focus on critical paths first**
   - Domain models and validators (highest priority)
   - Business logic in services
   - Orchestration workflows

2. **Add tests incrementally**
   - One module at a time
   - Monitor coverage delta in PRs
   - Set realistic goals

3. **Use coverage gaps as guide**
   - Review Codacy file coverage list
   - Target files below threshold
   - Add tests for uncovered branches

### Coverage Reports
- **Local development**: `pytest --cov=autoapply --cov-report=html`
  - Opens htmlcov/index.html for detailed interactive report
- **CI pipeline**: Automatic XML generation and upload
- **Artifact download**: Available for 30 days from workflow runs

## Maintenance

### Updating pytest-cov
```bash
pip install --upgrade pytest-cov
# Update pyproject.toml if needed
```

### Updating Codacy Reporter
No action needed - workflow uses `curl -Ls https://coverage.codacy.com/get.sh` which always fetches the latest version.

### Troubleshooting Token Issues
If token needs rotation:
1. Generate new token in Codacy dashboard
2. Update `CODACY_PROJECT_TOKEN` in GitHub Secrets
3. No code changes required

## Support

### Codacy Documentation
- Coverage Setup: https://docs.codacy.com/coverage-reporter/
- Troubleshooting: https://docs.codacy.com/coverage-reporter/troubleshooting/
- Advanced Scenarios: https://docs.codacy.com/coverage-reporter/advanced/

### GitHub Actions Documentation
- Workflow Syntax: https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions
- Upload Artifact Action: https://github.com/actions/upload-artifact

### Contact
- Codacy Support: support@codacy.com
- Include: repository URL, workflow run URL, commit SHA, coverage.xml

---

## Quick Reference

### Run Coverage Locally
```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests with coverage
pytest --cov=autoapply --cov-report=term --cov-report=html

# View HTML report
open htmlcov/index.html  # Mac/Linux
start htmlcov/index.html # Windows
```

### Check Workflow Status
```bash
# Using GitHub CLI
gh workflow view "Codacy Coverage Reporter"
gh run list --workflow="Codacy Coverage Reporter"
gh run view <run-id>
```

### Verify Token Set
```bash
# Using GitHub CLI
gh secret list | grep CODACY
# Should show: CODACY_PROJECT_TOKEN
```

---

**Last Updated**: November 3, 2025  
**Workflow Version**: 1.0  
**Status**: ✅ Active

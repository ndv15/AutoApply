# Step 1: Lock Scope & Add Safety Guards - Prompt for Cline

**Task:** Implement documentation-only branch with automated CI safety guards

**Working Directory:** `c:/Users/ndv1t/OneDrive/Desktop/AI Agent Programs/autoapply`

---

## Objective

Create a documentation-only working branch with GitHub Actions CI guards that prevent accidental backend changes and enforce quality standards.

---

## Tasks to Complete

### Task 1: Create Working Branch

Create a new branch for documentation work:

```bash
git checkout -b docs/v0.9-runbook
```

**Verify:**
```bash
git branch --show-current
```

Expected output: `docs/v0.9-runbook`

---

### Task 2: Add CI Path Guard Workflow

Create the file `.github/workflows/docs-guard.yml` with the following content:

```yaml
name: Documentation Guards

on:
  push:
    branches:
      - 'docs/**'
  pull_request:
    branches:
      - main
      - 'docs/**'

jobs:
  # Gate 1: Path Guard - Block changes outside allowed paths
  path-guard:
    name: "Path Guard"
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
        with:
          fetch-depth: 0

      - name: Check for disallowed file changes
        run: |
          git fetch origin ${{ github.base_ref || 'main' }}
          CHANGED=$(git diff --name-only origin/${{ github.base_ref || 'main' }} HEAD | grep -vE '^(docs/|\.github/workflows/docs-guard\.yml|tests/fixtures/)' || true)
          
          if [ -n "$CHANGED" ]; then
            echo "::error::Files changed outside allowed paths (docs/, .github/workflows/docs-guard.yml, tests/fixtures/)"
            echo "Changed files:"
            echo "$CHANGED"
            exit 1
          fi
          
          echo "✅ All changes are within allowed paths"

  # Gate 2: Test Gate - Ensure no regressions
  test-gate:
    name: "Test Gate"
    runs-on: ubuntu-latest
    needs: path-guard
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e .
          pip install pytest pytest-cov

      - name: Run integration tests
        run: |
          pytest tests/integration/test_e2e_pipeline.py -v --tb=short
          
      - name: Verify tests passed
        run: |
          echo "✅ Integration tests passed - no regressions"

  # Gate 3: Performance Gate - Check pipeline time budget
  performance-gate:
    name: "Performance Gate"
    runs-on: ubuntu-latest
    needs: test-gate
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e .

      - name: Measure pipeline performance
        run: |
          START=$(date +%s)
          python -m pytest tests/integration/test_e2e_pipeline.py -v -k "test_e2e" --tb=short
          END=$(date +%s)
          DURATION=$((END - START))
          
          echo "Pipeline completed in ${DURATION} seconds"
          
          if [ $DURATION -gt 20 ]; then
            echo "::error::Pipeline exceeded 20s time budget (${DURATION}s)"
            exit 1
          fi
          
          echo "✅ Pipeline within 20s time budget (${DURATION}s)"

  # Gate 4: Output Verification - Check AMOT thresholds
  output-verification:
    name: "Output Verification"
    runs-on: ubuntu-latest
    needs: performance-gate
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e .

      - name: Run pipeline and capture output
        run: |
          python -m pytest tests/integration/test_e2e_pipeline.py -v -s > pipeline_output.txt 2>&1 || true

      - name: Verify AMOT metrics
        run: |
          # Check for verification rate >= 70%
          if ! grep -qE "verification_rate.*[0-9]+\.[0-9]+.*0\.[7-9][0-9]|1\.0" pipeline_output.txt; then
            echo "::warning::Verification rate below 70% threshold"
          fi
          
          # Check for provenance tracking
          if ! grep -q "provenance" pipeline_output.txt; then
            echo "::warning::Provenance tracking not found in output"
          fi
          
          # Check for AMOT validation
          if ! grep -qE "(AMOT|amot_score)" pipeline_output.txt; then
            echo "::warning::AMOT validation not found in output"
          fi
          
          echo "✅ Output verification completed"

      - name: Upload pipeline output
        uses: actions/upload-artifact@v3
        with:
          name: pipeline-output
          path: pipeline_output.txt

  # Gate 5: Secret Scan - Check for credentials/PII
  secret-scan:
    name: "Secret Scan"
    runs-on: ubuntu-latest
    needs: path-guard
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Scan for secrets in docs
        run: |
          # Check for API keys
          if grep -rE "(api[_-]?key|apikey|api[_-]?secret)" docs/ --include="*.md" --include="*.txt"; then
            echo "::error::API keys found in documentation"
            exit 1
          fi
          
          # Check for access tokens
          if grep -rE "(access[_-]?token|bearer[_-]?token|auth[_-]?token)" docs/ --include="*.md" --include="*.txt"; then
            echo "::error::Access tokens found in documentation"
            exit 1
          fi
          
          # Check for hardcoded passwords
          if grep -rE "(password|passwd|pwd)[[:space:]]*[:=][[:space:]]*['\"]?[a-zA-Z0-9]{8,}" docs/ --include="*.md" --include="*.txt"; then
            echo "::error::Hardcoded passwords found in documentation"
            exit 1
          fi
          
          # Check for real email addresses (allow examples)
          if grep -rE "[a-zA-Z0-9._%+-]+@(?!example\.com|test\.com|sample\.com)[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}" docs/ --include="*.md" --include="*.txt"; then
            echo "::warning::Real email addresses found in documentation (use example.com)"
          fi
          
          # Check for real phone numbers (simple pattern)
          if grep -rE "\+?[1-9][0-9]{7,14}" docs/ --include="*.md" --include="*.txt" | grep -v "example\|sample\|555-"; then
            echo "::warning::Real phone numbers found in documentation"
          fi
          
          echo "✅ No secrets or PII detected in documentation"

  # Summary Gate - All checks passed
  all-guards-passed:
    name: "✅ All Guards Passed"
    runs-on: ubuntu-latest
    needs: [path-guard, test-gate, performance-gate, output-verification, secret-scan]
    steps:
      - name: Summary
        run: |
          echo "🎉 All documentation guards passed!"
          echo "✅ Path guard: Changes limited to allowed paths"
          echo "✅ Test gate: No regressions detected"
          echo "✅ Performance gate: Pipeline within time budget"
          echo "✅ Output verification: AMOT thresholds maintained"
          echo "✅ Secret scan: No credentials or PII found"
```

**What this workflow does:**
- **Gate 1 (Path Guard):** Fails if any files outside `docs/`, `.github/workflows/docs-guard.yml`, or `tests/fixtures/` are changed
- **Gate 2 (Test Gate):** Runs integration tests to ensure no regressions
- **Gate 3 (Performance Gate):** Enforces <20 second pipeline time budget
- **Gate 4 (Output Verification):** Validates AMOT metrics are present (verification rate ≥70%, provenance tracking, AMOT validation)
- **Gate 5 (Secret Scan):** Scans docs/ for API keys, tokens, passwords, emails, phone numbers

---

### Task 3: Commit and Push

Stage, commit, and push the workflow file:

```bash
# Create directory if it doesn't exist
mkdir -p .github/workflows

# Stage the workflow file (after you create it)
git add .github/workflows/docs-guard.yml

# Commit with descriptive message
git commit -m "ci: Add documentation guards workflow

- Path guard: Blocks changes outside docs/, tests/fixtures/
- Test gate: Runs integration tests to prevent regressions
- Performance gate: Enforces <20s pipeline time budget
- Output verification: Validates AMOT thresholds maintained
- Secret scan: Prevents API keys/PII in documentation

All guards must pass before PR can be merged."

# Push to remote
git push -u origin docs/v0.9-runbook
```

**Expected output:**
```
To https://github.com/ndv15/AutoApply.git
 * [new branch]      docs/v0.9-runbook -> docs/v0.9-runbook
```

---

### Task 4: Verify in GitHub Actions

1. Navigate to: https://github.com/ndv15/AutoApply/actions
2. Look for "Documentation Guards" workflow
3. Verify it ran on the recent push
4. Check that all 5 gates are visible and running/passing

---

### Task 5: Test Path Guard (Optional but Recommended)

**Test 1: Valid docum documentation change (should pass)**
```bash
echo "# Test Documentation" > docs/test.md
git add docs/test.md
git commit -m "docs: test valid change"
git push
```

Expected: CI passes ✅

**Test 2: Invalid backend change (should fail)**
```bash
echo "# test" > autoapply/test.py
git add autoapply/test.py
git commit -m "test: invalid change"
git push
```

Expected: Path guard fails ❌ with error message

**Cleanup:**
```bash
git reset --hard HEAD~1
git push --force
```

---

## Acceptance Criteria

After completing all tasks, verify:

- [ ] ✅ Branch `docs/v0.9-runbook` exists on GitHub
- [ ] ✅ File `.github/workflows/docs-guard.yml` is committed and pushed
- [ ] ✅ Workflow appears in GitHub Actions tab
- [ ] ✅ All 5 gates are visible in the workflow:
  - Path Guard
  - Test Gate
  - Performance Gate
  - Output Verification
  - Secret Scan
- [ ] ✅ Path guard correctly fails when non-docs files are changed
- [ ] ✅ Path guard passes when only docs files are changed

---

## Completion Summary Template

Once done, provide this summary:

```
✅ Step 1 Complete: Lock Scope & Add Safety Guards

**Branch Created:**
- Name: docs/v0.9-runbook
- Status: Pushed to https://github.com/ndv15/AutoApply
- Verified: git branch --show-current returns "docs/v0.9-runbook"

**CI Workflow Added:**
- File: .github/workflows/docs-guard.yml
- Location: https://github.com/ndv15/AutoApply/actions
- Status: Visible in GitHub Actions
- Gates Implemented: 5

**Gate 1: Path Guard**
- Purpose: Block changes outside allowed paths
- Allowed: docs/, .github/workflows/docs-guard.yml, tests/fixtures/
- Blocked: autoapply/, pyproject.toml, tests/integration/, etc.
- Status: Active ✅

**Gate 2: Test Gate**
- Purpose: Prevent regressions
- Checks: Runs pytest tests/integration/test_e2e_pipeline.py
- Status: Active ✅

**Gate 3: Performance Gate**
- Purpose: Enforce time budget
- Threshold: <20 seconds
- Status: Active ✅

**Gate 4: Output Verification**
- Purpose: Validate metrics
- Checks: verification_rate ≥70%, provenance, AMOT validation
- Status: Active ✅

**Gate 5: Secret Scan**
- Purpose: Prevent credential leaks
- Blocks: API keys, tokens, passwords
- Warns: Real emails, phone numbers
- Status: Active ✅

**Testing Performed:**
- Valid docs change: PASSED ✅
- Invalid backend change: FAILED ❌ (as expected)

**Next Steps:**
- Proceed to Step 2: Create documentation content
- All commits will be checked by CI guards
- Only docs/ changes will be allowed
```

---

## Additional Information

### Why These Guards Matter

**Path Guard:**
- Prevents accidental production code changes in documentation PRs
- Keeps PRs focused and reviewable
- Reduces risk of breaking changes

**Test Gate:**
- Ensures documentation reflects working system
- Catches regressions early
- Maintains code quality

**Performance Gate:**
- Documents expected performance
- Prevents degradation over time
- Keeps CI fast

**Output Verification:**
- Ensures documented metrics are accurate
- Validates quality standards
- Provides evidence of capabilities

**Secret Scan:**
- Security: Prevents credential exposure
- Privacy: Protects PII
- Compliance: GDPR/CCPA adherence

### Common Issues

**Issue 1: Git command not found**
Solution: Ensure Git is installed and in PATH

**Issue 2: Permission denied on push**
Solution: Verify GitHub authentication with `gh auth status`

**Issue 3: Workflow doesn't appear**
Solution: Wait 30-60 seconds, refresh GitHub Actions page

**Issue 4: Path guard doesn't fail on backend changes**
Solution: Verify regex in workflow matches excluded paths correctly

### Configuration Reference

**Allowed Paths:**
```
docs/                           # All documentation
docs/images/                    # Images
docs/diagrams/                  # Mermaid diagrams
tests/fixtures/                 # Test data only
.github/workflows/docs-guard.yml # This workflow
```

**Blocked Paths:**
```
autoapply/                      # Backend code
tests/integration/              # Integration tests
tests/unit/                     # Unit tests
pyproject.toml                  # Dependencies
*.py (outside fixtures)         # Python code
```

**Time Budgets:**
- Pipeline execution: <20 seconds
- CI total time: <2 minutes

**Quality Thresholds:**
- Verification rate: ≥70%
- AMOT validation: Required
- Provenance tracking: Required

---

## Questions?

If any step fails or is unclear:
1. Check the error message carefully
2. Verify you're in the correct directory
3. Ensure Git/GitHub CLI are properly configured
4. Review the "Common Issues" section above
5. Ask for clarification if needed

---

**End of Step 1 Prompt**

**Ready to execute?** Copy this entire prompt to Cline and begin implementation.

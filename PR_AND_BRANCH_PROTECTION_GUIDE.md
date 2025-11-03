# Step-by-Step Instructions for PR Creation and Branch Protection

**Repository:** AutoApply  
**Branch:** `docs/v0.9-runbook`  
**Commit:** `1c0e8a7`  
**Status:** Ready for PR creation

---

## Prerequisites Checklist

Before starting, verify:

- [x] ✅ Changes committed to `docs/v0.9-runbook`
- [x] ✅ Branch pushed to remote
- [x] ✅ `pr_body.txt` file exists in project root
- [x] ✅ All documentation files created
- [x] ✅ CI workflow file in place
- [ ] ⏳ GitHub authentication (check with `gh auth status`)

---

## 1. Prepare to Create the Pull Request

### Check GitHub CLI Authentication

```bash
gh auth status
```

**If not authenticated:**
```bash
gh auth login
# Follow prompts:
# - Select: GitHub.com
# - Protocol: HTTPS
# - Authenticate: Login with a web browser
```

### Verify Your Branch Status

```bash
git branch --show-current
# Should show: docs/v0.9-runbook

git log -1 --oneline
# Should show: 1c0e8a7 "docs: add product explainer and CI workflow"

git status
# Should show: nothing to commit, working tree clean
```

---

## 2. Create the Pull Request

### Option A: Using the Web Interface (Recommended)

**Step 1:** Open your browser and navigate to:
```
https://github.com/ndv15/AutoApply/pull/new/docs/v0.9-runbook
```

**Step 2:** Fill in PR details:
- **Title:** `Documentation Sprint v0.9 - Implementation Runbook and Product Explainer`
- **Description:** 
  1. Open `pr_body.txt` in your project root folder
  2. Copy the entire contents (Ctrl+A, Ctrl+C)
  3. Paste into the "Description" field on GitHub

**Step 3:** Review the PR preview:
- Check that "base" is `main`
- Check that "compare" is `docs/v0.9-runbook`
- Review "Files changed" tab (should show 9 files)
- Confirm changes are only in `docs/` and `.github/workflows/`

**Step 4:** Click "Create pull request" button

---

### Option B: Using GitHub CLI (If Authenticated)

```bash
gh pr create \
  -B main \
  -H docs/v0.9-runbook \
  -t "Documentation Sprint v0.9 - Implementation Runbook and Product Explainer" \
  -F pr_body.txt
```

**Expected output:**
```
https://github.com/ndv15/AutoApply/pull/[NUMBER]
```

---

## 3. Assign Reviewers

### Via Web Interface

**Step 1:** On the PR page, locate the "Reviewers" section in the right sidebar

**Step 2:** Click the gear icon (⚙️) next to "Reviewers"

**Step 3:** Assign reviewers:

**Technical Reviewer (Required):**
- Should understand: AMOT format, CI/CD workflows, Python, Git
- Reviews: Code quality, technical accuracy, CI configuration
- Example role: Senior Developer, Tech Lead, DevOps Engineer

**Non-Technical Reviewer (Required):**
- Should understand: Product documentation, user experience, clarity
- Reviews: Grammar, readability, completeness, user-friendliness
- Example role: Product Manager, Technical Writer, UX Designer

**Step 4:** Optionally assign yourself as the "Assignee" to track ownership

---

### Via GitHub CLI

```bash
# Get PR number from output above or from GitHub
PR_NUMBER=<PR_NUMBER>

# Assign technical reviewer
gh pr edit $PR_NUMBER --add-reviewer <tech-reviewer-username>

# Assign non-technical reviewer
gh pr edit $PR_NUMBER --add-reviewer <nontech-reviewer-username>

# Assign yourself
gh pr edit $PR_NUMBER --add-assignee @me
```

**Example:**
```bash
gh pr edit 42 --add-reviewer john-doe --add-reviewer jane-smith --add-assignee @me
```

---

## 4. Monitor and Address CI Checks

### Watch CI Checks Run

**Expected CI Jobs (4 gates):**
1. ✅ **Path Guard** (~30 seconds)
   - Verifies changes only in allowed paths
   - Blocks if backend code modified
   
2. ✅ **Secret Scan** (~30 seconds)
   - Checks for API keys, tokens, passwords
   - Warns on real email addresses
   
3. ✅ **Output Verification** (~20 seconds)
   - Validates AMOT and metrics terminology present
   
4. ✅ **Performance Gate** (~45 seconds)
   - Tests Pandoc export performance
   - Fails if export takes >60 seconds

**Total CI runtime:** ~2-3 minutes

---

### Monitor Status

**Via Web Interface:**
- PR page → "Checks" tab
- Watch for green checkmarks ✅
- Red X ❌ indicates failure

**Via GitHub CLI:**
```bash
gh pr checks $PR_NUMBER
```

---

### If CI Checks Fail

**Identify the failure:**
```bash
gh pr checks $PR_NUMBER --watch
```

**Common fixes:**

**Path Guard fails:**
- Check if files outside `docs/`, `.github/workflows/`, `tests/fixtures/` were modified
- Remove unauthorized changes
- Push corrected commit

**Secret Scan fails:**
- Search for API keys, tokens, or passwords in documentation
- Remove sensitive data
- Push corrected commit

**Output Verification fails:**
- Ensure `docs/product_explainer_v1.md` contains "AMOT" and "metrics"
- Add missing terminology
- Push corrected commit

**Performance Gate fails:**
- Check for extremely large files or malformed Markdown
- Optimize content
- Push corrected commit

**Push fix:**
```bash
# Make corrections in your files
git add docs/
git commit -m "fix: address CI check failure"
git push
# CI will automatically re-run
```

---

### Notify Reviewers

Once all checks are green ✅:

**Via PR comment:**
```markdown
@tech-reviewer @nontech-reviewer 

All CI checks have passed ✅. The PR is ready for review:

- ✅ Path Guard: Only docs/ and workflows/ modified
- ✅ Secret Scan: No credentials or PII found
- ✅ Output Verification: AMOT and metrics present
- ✅ Performance Gate: Export completed in <60s

Please review when convenient. Thank you!
```

---

## 5. Set Up Branch Protection for `main`

### Navigate to Settings

**Step 1:** Go to repository settings:
```
https://github.com/ndv15/AutoApply/settings/branches
```

**Step 2:** Click "Add rule" button

---

### Configure Branch Protection Rule

**Branch name pattern:**
```
main
```

**Enable these settings:**

#### Protect matching branches
- ☑️ **Require a pull request before merging**
  - ☑️ Require approvals: **1**
  - ☐ Dismiss stale pull request approvals when new commits are pushed (optional)
  - ☐ Require review from Code Owners (if CODEOWNERS file exists)

#### Status checks
- ☑️ **Require status checks to pass before merging**
  - ☑️ Require branches to be up to date before merging
  - **Status checks required:** (Search and select all 4)
    - `Path Guard`
    - `Secret Scan`
    - `Output Verification`
    - `Performance Gate`

#### Additional settings
- ☑️ **Require conversation resolution before merging** (optional, recommended)
- ☑️ **Require signed commits** (optional, for enhanced security)
- ☑️ **Do not allow bypassing the above settings**
- ☑️ **Restrict who can push to matching branches**
  - Add authorized users/teams (optional)
- ☑️ **Include administrators** (makes rules apply to admins too)

**Step 3:** Click "Create" or "Save changes"

---

### Verify Protection Rules

**Via Web Interface:**
- Refresh branch settings page
- Confirm `main` shows protection badge 🛡️

**Via GitHub CLI:**
```bash
gh api repos/ndv15/AutoApply/branches/main/protection | grep -A 10 required_status_checks
```

---

## 6. Merge and Clean Up

### Prerequisites for Merging

Before merging, confirm:

- [x] ✅ All CI checks passed
- [x] ✅ At least 1 reviewer approved
- [x] ✅ No merge conflicts
- [x] ✅ Branch is up to date with main
- [x] ✅ All conversations resolved (if required)

---

### Merge the PR

**Step 1:** Go to PR page

**Step 2:** Review final checklist:
- Files changed tab → Confirm only documentation modified
- Conversation tab → All reviewer comments addressed
- Checks tab → All green ✅

**Step 3:** Add merge summary comment (optional):

```markdown
## Merge Summary

### What Changed
- ✅ Added product explainer v1.0 (800+ lines, 12 sections)
- ✅ Created 4 Mermaid diagram sources
- ✅ Exported DOCX with TOC and numbered sections
- ✅ Added CI guards workflow (4 gates)
- ✅ Documented diagram rendering and export options

### Verification
- No secrets in documentation ✓
- Glossary terms match usage ✓
- DOCX opens with clickable TOC ✓
- CI gates configured and passing ✓
- All reviewers approved ✓

### Files Modified
- 9 files changed
- 935 insertions
- 180 deletions
- Commit: 1c0e8a7

### Next Steps
- Install Node.js to render diagram SVGs/PNGs
- Install LaTeX to generate PDF export
- Consider adding more case studies as product evolves
```

**Step 4:** Choose merge method:

**Option A: Squash and merge** (Recommended)
- Combines all commits into one clean commit
- Keeps main branch history clean
- Click "Squash and merge"
- Edit commit message if needed
- Click "Confirm squash and merge"

**Option B: Merge commit**
- Preserves all individual commits
- Shows full development history
- Click "Merge pull request"
- Click "Confirm merge"

**Option C: Rebase and merge**
- Replays commits on top of main
- Linear history without merge commit
- Click "Rebase and merge"
- Click "Confirm rebase and merge"

---

### Delete Feature Branch

**Step 5:** After successful merge:

**Via Web Interface:**
- GitHub will prompt: "Delete branch"
- Click "Delete branch" button
- Confirms cleanup of remote branch

**Via GitHub CLI:**
```bash
# Delete remote branch
git push origin --delete docs/v0.9-runbook

# Delete local branch (switch to main first)
git checkout main
git branch -D docs/v0.9-runbook
```

---

### Pull Latest Changes

**Step 6:** Update your local `main` branch:

```bash
git checkout main
git pull origin main
```

---

### Verify Merge

**Confirm files are on main:**
```bash
ls docs/
# Should see: product_explainer_v1.md, product_explainer_v1.docx, DIAGRAMS_README.md, EXPORT_NOTES.md, diagrams/

ls .github/workflows/
# Should see: docs-guard.yml
```

**Check commit history:**
```bash
git log --oneline -5
# Should show merge commit at top
```

---

## Post-Merge Verification Checklist

After merge is complete:

- [ ] ✅ PR merged successfully
- [ ] ✅ Feature branch deleted (remote and local)
- [ ] ✅ Local `main` updated with `git pull`
- [ ] ✅ All documentation files present on `main`
- [ ] ✅ CI workflow file present and active
- [ ] ✅ Branch protection rules active on `main`
- [ ] ✅ No merge conflicts or issues
- [ ] ✅ README or changelog updated (if applicable)

---

## Troubleshooting Common Issues

### Issue: Cannot create PR (no permission)

**Solution:**
- Verify you have write access to the repository
- Check with repository admin for permissions
- Fork the repo if you're an external contributor

---

### Issue: CI checks not running

**Solution:**
- Ensure `.github/workflows/docs-guard.yml` is present
- Check workflow syntax: https://github.com/ndv15/AutoApply/actions
- Verify GitHub Actions are enabled in repository settings

---

### Issue: Cannot merge (conflicts with main)

**Solution:**
```bash
# Update your branch with latest main
git checkout docs/v0.9-runbook
git fetch origin main
git merge origin/main
# Resolve any conflicts
git add .
git commit -m "fix: merge main into feature branch"
git push
```

---

### Issue: Reviewer requests changes

**Solution:**
- Address feedback in new commits on the feature branch
- Push changes: `git push`
- CI will automatically re-run
- Request re-review when ready

---

### Issue: Forgot to include something in PR

**Solution:**
```bash
# Make additional changes on the feature branch
git checkout docs/v0.9-runbook
# Edit files as needed
git add .
git commit -m "docs: add missing section"
git push
# PR will automatically update
```

---

## Quick Reference Commands

### Check Status
```bash
# Current branch
git branch --show-current

# Latest commit
git log -1 --oneline

# Files changed
git diff --name-only origin/main

# CI check status
gh pr checks $PR_NUMBER
```

### Create PR
```bash
# Via CLI (if authenticated)
gh pr create -B main -H docs/v0.9-runbook -t "Title Here" -F pr_body.txt

# Via web
# Visit: https://github.com/ndv15/AutoApply/pull/new/docs/v0.9-runbook
```

### Assign Reviewers
```bash
gh pr edit $PR_NUMBER --add-reviewer username1 --add-reviewer username2
```

### Check Protection Rules
```bash
gh api repos/ndv15/AutoApply/branches/main/protection
```

### Merge and Clean Up
```bash
# Via CLI (after approval and checks pass)
gh pr merge $PR_NUMBER --squash --delete-branch

# Update local main
git checkout main
git pull origin main
```

---

## Success Criteria

Your PR is ready to merge when:

1. ✅ **All CI checks green** (4 gates passed)
2. ✅ **Required approvals received** (minimum 1)
3. ✅ **No merge conflicts** with main
4. ✅ **All conversations resolved** (if required)
5. ✅ **Branch is up to date** with main
6. ✅ **Branch protection rules configured** on main
7. ✅ **Documentation reviewed** for accuracy and clarity

---

## Contact and Support

**Questions about this PR:**
- Review this guide: `PR_AND_BRANCH_PROTECTION_GUIDE.md`
- Check completion summary: `COMPLETION_SUMMARY.md`
- Review PR body: `pr_body.txt`

**Technical issues:**
- CI workflow: `.github/workflows/docs-guard.yml`
- Diagram rendering: `docs/DIAGRAMS_README.md`
- Export issues: `docs/EXPORT_NOTES.md`

**Repository maintainers:**
- Check GitHub repository settings for admin contacts
- Review CODEOWNERS file (if exists)

---

**Document Version:** 1.0  
**Last Updated:** November 2, 2025  
**For Repository:** https://github.com/ndv15/AutoApply

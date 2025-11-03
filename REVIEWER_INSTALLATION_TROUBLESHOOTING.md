# Reviewer Installation Troubleshooting

## 🚨 Issue: Codacy MCP Server Error

**Error Message:**
```
Connection state: Error spawn node ENOENT
```

**Root Cause:** Node.js is not installed or not in system PATH

---

## ✅ Recommended Approach: Use GitHub Apps (Not VS Code Extensions)

**Important:** The reviewers should be installed as **GitHub Apps**, not VS Code extensions.

### Why GitHub Apps > VS Code Extensions?

1. **No local dependencies** - Runs on GitHub's servers
2. **Automatic on every PR** - No manual triggering needed
3. **Team accessible** - Everyone can see results
4. **No setup errors** - GitHub handles execution
5. **Free for public repos** - No cost

---

## 🚀 Correct Installation Method

### For Codacy, CodeFactor, and Qlty

**DO THIS** ✅ - Install as GitHub App:
1. Go to GitHub Marketplace URL (in browser)
2. Click "Install" button
3. Select your repository
4. Grant permissions
5. Done - app automatically reviews PRs

**DON'T DO THIS** ❌ - Install as VS Code extension:
- Requires local Node.js
- Manual triggering needed
- Only works on your machine
- More complex setup

---

## 📝 Step-by-Step: Install Codacy (Correct Way)

### Option 1: Via GitHub Marketplace (Recommended)

1. **Open browser** (not VS Code)
2. **Navigate to:** https://github.com/marketplace/codacy
3. **Click:** "Set up a plan" or "Install it for free"
4. **Select:** "Free" plan (if available) or trial
5. **Click:** "Complete order and begin installation"
6. **Choose:** Install on "Only select repositories"
7. **Select:** `ndv15/AutoApply`
8. **Click:** "Install"
9. **Authorize:** Grant requested permissions
10. **Done!** Codacy will automatically analyze PR #1

### Option 2: Via Repository Settings

1. Go to: https://github.com/ndv15/AutoApply/settings/installations
2. Click "Configure" next to any existing apps (if any)
3. Or click "Add" to search for new apps
4. Search "Codacy"
5. Follow installation prompts

---

## 🔧 If You Still Want VS Code Extension (Not Recommended)

### Fix Node.js Error

**Step 1: Check if Node.js is installed**
```powershell
node --version
```

**If not installed:**
1. Download from: https://nodejs.org/
2. Install LTS version (20.x or later)
3. Restart VS Code
4. Try again

**Step 2: Verify Node.js in PATH**
```powershell
where node
```

Should output: `C:\Program Files\nodejs\node.exe`

**If not in PATH:**
1. Open System Environment Variables
2. Edit PATH variable
3. Add: `C:\Program Files\nodejs`
4. Restart VS Code

---

## ✅ Recommended Installation Order

### 1. GitHub Apps (Install These)

**A. Codacy** (5 minutes)
- URL: https://github.com/marketplace/codacy
- Method: Browser → Marketplace → Install
- Cost: Free for public repos (with limits)

**B. CodeFactor** (3 minutes)
- URL: https://github.com/marketplace/codefactor
- Method: Browser → Marketplace → Install
- Cost: Free for public repos

**C. Qlty** (5 minutes)  
- URL: https://github.com/marketplace/qlty
- Method: Browser → Marketplace → Install
- Cost: Free tier available

### 2. DeepSeek (Run Manually)

**Method:** Python script (already created)
```bash
# Set tokens
$env:GITHUB_TOKEN="your_token"
$env:DEEPSEEK_TOKEN="your_token"

# Run review
python scripts/deepseek_reviewer.py
```

---

## 🎯 How to Verify Installation

### For GitHub Apps (Codacy, CodeFactor, Qlty)

**Check 1: Repository Settings**
1. Go to: https://github.com/ndv15/AutoApply/settings/installations
2. Verify apps are listed with green checkmark
3. Click "Configure" to verify repositories

**Check 2: PR Checks**
1. Go to: https://github.com/ndv15/AutoApply/pull/1
2. Scroll to bottom, look for "Checks" section
3. Should see new check runs for each app
4. Click "Details" to see results

**Check 3: PR Comments**
1. Go to "Files changed" tab on PR
2. Look for automated comments from bots
3. Apps may comment on specific lines with issues

### For DeepSeek (Manual Script)

**Check 1: Script Execution**
```bash
python scripts/deepseek_reviewer.py
# Should output:
# ================================================================================
# Reviewing: .github/workflows/docs-guard.yml
# Length: XXXX characters
# ================================================================================
```

**Check 2: PR Comments**
1. Go to: https://github.com/ndv15/AutoApply/pull/1
2. Look for comments with "🤖 DeepSeek Technical Review" header

---

## 📊 What Success Looks Like

### After Installing All Apps

**PR #1 will show:**
```
Checks
  ✅ docs-guard / Secret Scan
  ✅ docs-guard / Path Guard  
  ✅ docs-guard / Output Verification
  ✅ docs-guard / Performance Gate
  🔄 Codacy / Code Quality (running...)
  🔄 CodeFactor / Code Review (running...)
  🔄 Qlty / Quality Analysis (running...)
```

**After Apps Complete (5-10 min):**
```
Conversation with Cline:
  🤖 DeepSeek Technical Review - docs/product_explainer_v1.md
  🤖 DeepSeek Technical Review - docs/DIAGRAMS_README.md
  ... (9 files total)

Comments from bots:
  🔒 Codacy: 3 security issues found on line 45, 67, 102
  📏 CodeFactor: Code grade: B+ (some style issues)
  📊 Qlty: Quality score 85% (maintainability: Good)
```

---

## 🆘 Common Issues & Solutions

### Issue 1: "Error spawn node ENOENT" (Your current issue)

**Cause:** Trying to run Codacy as VS Code extension without Node.js

**Solution:** 
1. ❌ Uninstall Codacy from VS Code extensions
2. ✅ Install Codacy as GitHub App instead (via browser)
3. URL: https://github.com/marketplace/codacy

### Issue 2: App not appearing in PR checks

**Cause:** App not authorized for repository

**Solution:**
1. Go to: https://github.com/settings/installations
2. Find the app
3. Click "Configure"
4. Ensure `AutoApply` is selected in repository list

### Issue 3: App shows "Queued" forever

**Cause:** GitHub's queue backlog

**Solution:**
- Wait 5-10 minutes
- Refresh PR page
- Or push a dummy commit to re-trigger

### Issue 4: "Permission denied" errors

**Cause:** App doesn't have required permissions

**Solution:**
1. Go to app configuration
2. Grant additional permissions:
   - Contents: Read
   - Pull requests: Write
   - Checks: Write
3. Save and re-authorize

### Issue 5: DeepSeek script fails with auth error

**Cause:** Token not set or invalid

**Solution:**
```powershell
# Check token is set
echo $env:GITHUB_TOKEN
echo $env:DEEPSEEK_TOKEN

# If empty, set them:
$env:GITHUB_TOKEN="your_github_pat_here"
$env:DEEPSEEK_TOKEN="your_github_pat_here"

# Run again
python scripts/deepseek_reviewer.py
```

---

## 📚 Quick Reference Links

### GitHub App Installation
- **Codacy:** https://github.com/marketplace/codacy
- **CodeFactor:** https://github.com/marketplace/codefactor
- **Qlty:** https://github.com/marketplace/qlty

### Your Repository
- **Settings:** https://github.com/ndv15/AutoApply/settings
- **Installations:** https://github.com/ndv15/AutoApply/settings/installations
- **PR #1:** https://github.com/ndv15/AutoApply/pull/1

### Documentation
- **Setup Guide:** `REVIEWER_RECOMMENDATIONS.md`
- **Review Protocol:** `REVIEWER_PROTOCOL.md`
- **DeepSeek Setup:** `DEEPSEEK_REVIEWER_SETUP.md`

---

## ✅ Recommended Next Steps

1. **Close VS Code** (if Codacy extension installed there)

2. **Open browser**

3. **Install GitHub Apps:**
   - Codacy → https://github.com/marketplace/codacy
   - CodeFactor → https://github.com/marketplace/codefactor
   - Qlty → https://github.com/marketplace/qlty

4. **Verify installation:**
   - Check: https://github.com/ndv15/AutoApply/settings/installations
   - Should see all 3 apps listed

5. **View PR #1:**
   - Go to: https://github.com/ndv15/AutoApply/pull/1
   - Wait 2-3 minutes
   - Refresh page
   - Check "Checks" section at bottom
   - Look for new check runs

6. **Run DeepSeek** (after GitHub apps finish):
   ```powershell
   $env:GITHUB_TOKEN="your_token"
   $env:DEEPSEEK_TOKEN="your_token"
   python scripts/deepseek_reviewer.py
   ```

---

## 🎯 Success Criteria

You'll know everything is working when:

- [ ] No errors in VS Code (removed Codacy extension)
- [ ] 3 GitHub Apps visible in repository settings
- [ ] PR #1 shows new check runs for each app
- [ ] Automated comments appear on PR
- [ ] DeepSeek script runs without errors
- [ ] DeepSeek comments posted to PR
- [ ] All checks eventually show green ✅

---

**Current Status:** ❌ Node.js error (using wrong installation method)  
**Next Action:** Install as GitHub Apps via browser (not VS Code)  
**Time Required:** 15 minutes for all 3 apps  

**Fix:** Don't use VS Code extensions - use GitHub Marketplace in your browser! 🌐

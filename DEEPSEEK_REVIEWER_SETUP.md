# DeepSeek AI Reviewer Setup Guide

## Overview

This guide will help you set up DeepSeek AI as an automated technical reviewer for PR #1 using GitHub Models API.

---

## Step 1: Create GitHub Personal Access Token

You've already started this process. Complete it by:

1. **Go to:** https://github.com/settings/tokens?type=beta
2. **Fill in the form:**
   - **Token name:** `GitHub Models DeepSeek Access`
   - **Description:** `Used to call GitHub Models APIs for PR reviews`
   - **Resource owner:** `ndv15`
   - **Expiration:** 30 days (or longer if needed)
   - **Repository access:** Select "All repositories" or specific repos including `AutoApply`

3. **Set Permissions:**
   - **Models:** Read-only ✅ (Required for API access)
   - **Contents:** Read-only ✅ (To read PR files)
   - **Pull requests:** Read and write ✅ (To post review comments)
   - **Issues:** Read and write ✅ (PR comments use Issues API)

4. **Click "Generate token"**

5. **IMPORTANT:** Copy the token immediately - you won't see it again!
   - Format: `github_pat_...`

---

## Step 2: Add Token to Repository Secrets

1. **Go to your AutoApply repository settings:**
   https://github.com/ndv15/AutoApply/settings/secrets/actions

2. **Click "New repository secret"**

3. **Create secret:**
   - **Name:** `DEEPSEEK_TOKEN`
   - **Value:** Paste the token you just generated
   - **Click "Add secret"**

---

## Step 3: Verify Workflow File

The DeepSeek reviewer workflow has been created at:
`.github/workflows/deepseek-reviewer.yml`

However, it was truncated. Here's what you need to do:

**Option A: Use the simplified version I'll create**
- I'll create a complete, working version

**Option B: Manual completion**
- The workflow needs the Python script completed
- It should fetch PR files and send them to DeepSeek for review

---

## Step 4: Test the Reviewer

Once set up, the DeepSeek reviewer will:

1. **Trigger automatically** when:
   - PR is opened
   - New commits pushed to PR
   - PR is reopened

2. **Review these file types:**
   - Documentation (`.md` files)
   - Python code (`.py` files)
   - Workflows (`.yml`, `.yaml` files)
   - Files in `docs/` directory

3. **Post review comments** with:
   - Issues categorized by severity (CRITICAL/MAJOR/MINOR)
   - Specific line numbers
   - Clear recommendations
   - Impact assessments

---

## Alternative: Manual DeepSeek Review

If the automated workflow is complex, you can run DeepSeek reviews manually:

### Using GitHub Models Playground

1. **Visit:** https://github.com/marketplace/models
2. **Select DeepSeek-R1**
3. **Use this prompt for each file:**

```
You are a senior technical reviewer for a Resume Builder application (AutoApply v0.9).

Review the following file line by line and identify:
- CRITICAL issues (must fix before merge)
- MAJOR issues (should fix before merge)  
- MINOR issues (nice to fix)
- SUGGESTIONS (optional improvements)
- CONFIRMATIONS (correct patterns)

For each finding, provide:
- Line number
- Issue description
- Impact
- Specific recommendation
- Reference to best practice

File to review:
[PASTE FILE CONTENT HERE]
```

4. **Copy the review and post as PR comment**

---

## Step 5: Monitor and Iterate

After setup:

1. **Check Actions tab:**
   https://github.com/ndv15/AutoApply/actions

2. **Verify DeepSeek review runs:**
   - Should see "DeepSeek Technical Reviewer" workflow
   - Check for any errors in logs

3. **Review posted comments:**
   - Go to PR #1: https://github.com/ndv15/AutoApply/pull/1
   - Look for DeepSeek

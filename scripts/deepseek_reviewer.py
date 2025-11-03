#!/usr/bin/env python3
"""
DeepSeek AI Technical Reviewer for AutoApply PR #1
Performs exhaustive line-by-line technical review using DeepSeek-R1 model
"""

import os
import sys
import requests
import json
from openai import OpenAI

# Configuration
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')  # Your GitHub PAT
DEEPSEEK_TOKEN = os.getenv('DEEPSEEK_TOKEN')  # GitHub Models token
REPO = "ndv15/AutoApply"
PR_NUMBER = 1

# Files to review
FILES_TO_REVIEW = [
    ".github/workflows/docs-guard.yml",
    "docs/product_explainer_v1.md",
    "docs/DIAGRAMS_README.md",
    "docs/EXPORT_NOTES.md",
    "docs/runbook_v0_9.md",
    "docs/diagrams/architecture_overview.mmd",
    "docs/diagrams/provenance_card.mmd",
    "docs/diagrams/preview_approve_storyboard.mmd",
    "docs/diagrams/before_after_snippet.mmd"
]

REVIEW_PROMPT_TEMPLATE = """You are a senior technical reviewer performing an exhaustive code and documentation review for a Resume Builder application (AutoApply v0.9).

**Your Role:** Technical Reviewer - Engineering rigor, architecture, AMOT alignment, maintainability

**Review Protocol:**
1. Review EVERY line of the provided file sequentially
2. For EVERY issue, suggestion, or confirmation, provide detailed feedback
3. Be specific with line numbers and actionable recommendations

**Focus Areas:**
- Code technical soundness and best practices
- AMOT format validation (Action-Metric-Outcome-Tool)  
- Architecture and design patterns
- Maintainability and scalability
- Type safety and error handling
- CI/CD workflow configuration
- Performance considerations
- Edge case handling
- Documentation clarity and completeness

**File to Review:**
```
{file_content}
```

**Instructions:**
Provide your review with the following structure:

1. **Overall Assessment** (2-3 sentences)

2. **Critical Issues** (must fix before merge)
   - Line X: [Issue description] → [Specific recommendation]

3. **Major Issues** (should fix before merge)
   - Line X: [Issue description] → [Specific recommendation]

4. **Minor Issues** (nice to fix)
   - Line X: [Issue description] → [Specific recommendation]

5. **Suggestions** (optional improvements)
   - Line X: [Suggestion description]

6. **Confirmations** (correct patterns observed)
   - Line X: [What was done well]

7. **Summary Statistics**
   - Total lines reviewed: X
   - Critical: X, Major: X, Minor: X, Suggestions: X, Confirmations: X

Be specific, actionable, and cite best practices where relevant."""


def get_pr_file_content(file_path):
    """Fetch file content from PR branch."""
    url = f"https://api.github.com/repos/{REPO}/contents/{file_path}?ref=docs/v0.9-runbook"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3.raw"
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.text
    else:
        print(f"Error fetching {file_path}: {response.status_code}")
        return None


def review_with_deepseek(file_path, content):
    """Send file to DeepSeek for review via GitHub Models."""
    try:
        # Initialize OpenAI client pointing to GitHub Models
        client = OpenAI(
            base_url="https://models.inference.ai.azure.com",
            api_key=DEEPSEEK_TOKEN,
        )
        
        # Truncate content if too long (model has context limits)
        max_content_length = 8000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "\n\n[... content truncated ...]"
        
        prompt = REVIEW_PROMPT_TEMPLATE.format(
            file_path=file_path,
            file_content=content
        )
        
        print(f"\n{'='*80}")
        print(f"Reviewing: {file_path}")
        print(f"Length: {len(content)} characters")
        print(f"{'='*80}\n")
        
        response = client.chat.completions.create(
            model="deepseek-r1",
            messages=[
                {
                    "role": "system", 
                    "content": "You are an expert technical code reviewer specializing in Python, documentation, and CI/CD workflows."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=4000
        )
        
        review_text = response.choices[0].message.content
        return review_text
        
    except Exception as e:
        print(f"Error reviewing {file_path}: {str(e)}")
        return None


def post_review_to_pr(file_path, review_text):
    """Post review as PR comment."""
    url = f"https://api.github.com/repos/{REPO}/issues/{PR_NUMBER}/comments"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    comment_body = f"""## 🤖 DeepSeek Technical Review

**File:** `{file_path}`

{review_text}

---
*Automated review by DeepSeek-R1 via GitHub Models API*
*Review date: {os.popen('date').read().strip()}*
"""
    
    payload = {"body": comment_body}
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 201:
        print(f"✅ Posted review for {file_path}")
        return True
    else:
        print(f"❌ Failed to post review for {file_path}: {response.status_code}")
        print(f"Response: {response.text}")
        return False


def main():
    """Main review process."""
    # Validate environment variables
    if not GITHUB_TOKEN:
        print("ERROR: GITHUB_TOKEN environment variable not set")
        print("Set it with: export GITHUB_TOKEN=your_github_pat")
        sys.exit(1)
    
    if not DEEPSEEK_TOKEN:
        print("ERROR: DEEPSEEK_TOKEN environment variable not set")
        print("Set it with: export DEEPSEEK_TOKEN=your_github_models_token")
        sys.exit(1)
    
    print(f"Starting DeepSeek review for PR #{PR_NUMBER}")
    print(f"Repository: {REPO}")
    print(f"Files to review: {len(FILES_TO_REVIEW)}")
    print()
    
    results = []
    
    for file_path in FILES_TO_REVIEW:
        # Fetch file content
        content = get_pr_file_content(file_path)
        if not content:
            print(f"⚠️  Skipping {file_path} - could not fetch content")
            continue
        
        # Review with DeepSeek
        review = review_with_deepseek(file_path, content)
        if not review:
            print(f"⚠️  Skipping {file_path} - review failed")
            continue
        
        # Post to PR
        success = post_review_to_pr(file_path, review)
        results.append({
            "file": file_path,
            "success": success
        })
        
        print()  # Add spacing between files
    
    # Summary
    print("\n" + "="*80)
    print("REVIEW SUMMARY")
    print("="*80)
    successful = sum(1 for r in results if r["success"])
    print(f"Total files: {len(FILES_TO_REVIEW)}")
    print(f"Reviewed: {len(results)}")
    print(f"Posted to PR: {successful}")
    print(f"Failed: {len(results) - successful}")
    print("\nView reviews at: https://github.com/ndv15/AutoApply/pull/1")


if __name__ == "__main__":
    main()

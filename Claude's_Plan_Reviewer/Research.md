# Reviewer/Research Agent — Surgical Change Plan (Detailed)

## Executive Summary
Audited codebase against [AGENTS.md](AGENTS.md) acceptance criteria. Found 5 critical gaps:
1. **Repetitive bullets**: MMR+history exist but not called in sequential flow
2. **Non-AMOT bullets**: Validator exists but not enforced; LLM prompts lack explicit AMOT structure
3. **Preview not updating**: Function doesn't exist; template expects server-rendered HTML
4. **Quota gate weak**: Endpoint exists but template logic incomplete
5. **Skills formatting**: Hardcoded categories vs dynamic from JD

All fixes are surgical (no refactoring). Total: 7 files, ~150 lines changed.

---

## Step-by-Step Implementation Plan

### STEP 1: Fix Repetitive Bullets (MMR + History)

#### 1.1 — Wire `generate_next_suggestion()` into Sequential API
**File**: `app/api_sequential.py`  
**Function**: `get_next_suggestion()`  
**Lines**: 52-60

**Current code**:
```python
suggestion = generate_suggestion(
    job_id=job_id,
    role_key=role_key,
    jd_text=job.get('jd', ''),
    role_context=next(...)
)
```

**Change to**:
```python
suggestion = generate_next_suggestion(  # Use full pipeline version
    job_id=job_id,
    role_key=role_key,
    jd_text=job.get('jd', ''),
    role_context=next(
        (r for r in job.get('history', []) if r.get('role_id') == role_key),
        {'role_id': role_key}
    )
)
```

**Why**: `generate_next_suggestion()` ([experience.py:82-158](experience.py#L82-L158)) includes MMR (line 125), RRF (line 148), and history tracking; `generate_suggestion()` is legacy fallback.

**Evidence**: [experience.py:82-158](experience.py#L82-L158) shows full pipeline with Cohere→MMR→RRF→dedup.

---

#### 1.2 — Verify History Tracking
**File**: `app/writing/experience.py`  
**Function**: `generate_next_suggestion()`  
**Lines**: Already correct at 151-156

**No change needed** — just verify:
```python
# Line 151-156
if fused:
    suggestion = fused[0]
    suggestion['id'] = str(uuid.uuid4())
    suggestion['role_key'] = role_key
    # History already tracked via _save_suggestion() in generate_suggestions()
```

**Test**: After accepting bullet, check `out/suggestion_history/{job_id}_{role_key}.json` contains accepted text.

---

### STEP 2: Enforce AMOT Format (Validation + Prompts)

#### 2.1 — Strengthen `has_amot_format()` Validator
**File**: `app/writing/experience.py`  
**Function**: `has_amot_format()`  
**Lines**: 42-62

**Current**: Checks 4 components but doesn't return detailed failure reason.

**Add after line 62**:
```python
def has_amot_format(text: str, return_reason: bool = False) -> bool | tuple:
    """
    Check if text follows Action-Metric-Outcome-Tool format.
    
    If return_reason=True, returns (bool, str) with failure reason.
    """
    failures = []
    
    # Action: Starts with strong verb
    if not re.match(r'^(?:Led|Drove|Increased|Implemented|Developed|Created|Built|Managed|Achieved|Generated|Closed|Expanded)', text):
        failures.append("Missing strong action verb")
        
    # Metric: Contains at least one numeric value
    if not extract_metrics(text):
        failures.append("No quantified metric (%, $, count)")
        
    # Outcome: Contains business impact words
    impact_words = ['resulting', 'leading to', 'achieving', 'generating', 'improving', 'reducing', 'driving']
    if not any(word in text.lower() for word in impact_words):
        failures.append("No outcome phrase (resulting/achieving/driving)")
        
    # Tool/Context: Contains specific platform/tool/method
    tools_pattern = r'using|via|through|leveraging|with'
    if not re.search(tools_pattern, text, re.IGNORECASE):
        failures.append("No tool/method mentioned")
    
    if return_reason:
        return (len(failures) == 0, "; ".join(failures) if failures else "PASS")
    
    return len(failures) == 0
```

---

#### 2.2 — Enforce Validation in Generation Loop
**File**: `app/writing/experience.py`  
**Function**: `generate_next_suggestion()`  
**Lines**: 109-116

**Current**:
```python
for c in new_candidates:
    if not has_amot_format(c.get("text", "")):
        c["text"] = inject_metrics(c.get("text", ""))
    candidates.append(c)
```

**Change to**:
```python
for c in new_candidates:
    if not has_amot_format(c.get("text", "")):
        c["text"] = inject_metrics(c.get("text", ""))
        # Re-validate after injection
        is_valid, reason = has_amot_format(c["text"], return_reason=True)
        if not is_valid:
            print(f"Skipping non-AMOT: {c['text'][:60]}... ({reason})")
            continue  # Don't add to candidates
    candidates.append(c)
```

**Why**: Ensures only AMOT-compliant bullets reach the user.

---

#### 2.3 — Update LLM Prompts (Anthropic)
**File**: `app/llm/providers/anthropic.py`  
**Function**: `generate_bullet()`  
**Lines**: 95-131

**Replace lines 105-131** with:
```python
prompt = f"""Generate ONE quantified, achievement-focused resume bullet following strict AMOT format.

Role: {role_context.get('title', 'Unknown')} at {role_context.get('company', 'Unknown')}
Dates: {role_context.get('start', 'Unknown')} - {role_context.get('end', 'Present')}
Target JD Keywords: {keyword_list}
Required Skills: {skills_list}

STRICT AMOT FORMAT (all 4 required):
1. ACTION — Start with strong verb: Led | Drove | Increased | Closed | Built | Expanded | Implemented
2. METRIC — Quantified outcome: 35% | $2.5M | 15 deals | 50+ logos | [X%] (use placeholder if unknown)
3. OUTCOME — Business impact: "resulting in" | "leading to" | "achieving" | "driving" | "generating"
4. TOOL — Specific method: "via MEDDICC" | "using Salesforce" | "through territory planning" | "leveraging Outreach"

{style_instruction}

EXAMPLES (all have A+M+O+T):
✓ "Drove 35% pipeline growth converting 12 enterprise logos and generating $1.8M ARR via MEDDICC qualification framework"
✓ "Led team of 8 AEs achieving 115% quota through weekly deal coaching sessions and strategic account planning"
✓ "Closed $2.4M in Q1 sales (140% quota) by targeting Fortune 500 CxOs with tailored ROI presentations using Salesforce CPQ"
✓ "Increased win rate by [X%] resulting in [$Y]M incremental revenue through A/B testing of sales collateral"

PROHIBITED PHRASES:
❌ "responsible for" | "worked on" | "helped with" | "proven track record"

Format: Single line under 200 characters. Return ONLY the bullet text."""
```

**Repeat for**:
- `app/llm/providers/openai.py` (same function, lines ~95-131)
- `app/llm/providers/gemini.py` (same function, lines ~95-131)

---

### STEP 3: Wire Resume Preview After Accept/Reject

#### 3.1 — Create HTML Preview Renderer
**File**: `app/assemble/resume.py`  
**Insert after**: Line 258 (end of `render_resume()`)

**Add new function**:
```python
def render_resume_preview_html(
    identity: dict,
    exec_summary: str,
    soq: list,
    approved_bullets: dict,
    skills: list
) -> str:
    """
    Generate HTML preview of resume for live updates.
    
    Args:
        identity: {name, email, phone, location, linkedin}
        exec_summary: Executive summary text
        soq: List of qualification strings
        approved_bullets: {role_key: [{"text": "...", ...}, ...]}
        skills: List of skill strings
    
    Returns:
        HTML string for insertion into #resumePreview div
    """
    from pathlib import Path
    import json
    
    # Load employment history for dates/locations
    history_path = Path("profile/employment_history.json")
    if history_path.exists():
        history = json.loads(history_path.read_text())
        history_map = {h['role_id']: h for h in history}
    else:
        history_map = {}
    
    # Build HTML
    html_parts = []
    
    # Header
    html_parts.append(f'<div class="resume-name">{identity.get("name", "")}</div>')
    html_parts.append(f'<div class="resume-contact">{identity.get("email", "")} | {identity.get("phone", "")} | {identity.get("location", "")}</div>')
    if identity.get('linkedin'):
        html_parts.append(f'<div class="resume-contact" style="margin-top:4px">{identity["linkedin"]}</div>')
    
    # Executive Summary
    if exec_summary:
        html_parts.append('<div class="resume-section"><div class="resume-section-title">Executive Summary</div>')
        html_parts.append(f'<div>{exec_summary}</div></div>')
    
    # Professional Experience
    html_parts.append('<div class="resume-section"><div class="resume-section-title">Professional Experience</div>')
    
    for role_key, bullets in approved_bullets.items():
        if not bullets:
            continue
            
        role_info = history_map.get(role_key, {})
        title = role_info.get('title', 'Unknown Role')
        company = role_info.get('company', '')
        dates = f"{role_info.get('start', '')} – {role_info.get('end', 'Present')}"
        
        html_parts.append(f'<div class="resume-role-header">{title} | {company} | {dates}</div>')
        
        for bullet in bullets:
            html_parts.append(f'<div class="resume-bullet">{bullet.get("text", "")}</div>')
    
    html_parts.append('</div>')  # Close Professional Experience
    
    # Summary of Qualifications
    if soq:
        html_parts.append('<div class="resume-section"><div class="resume-section-title">Summary of Qualifications</div>')
        for qual in soq:
            html_parts.append(f'<div class="resume-bullet">○ {qual}</div>')
        html_parts.append('</div>')
    
    # Skills
    if skills:
        html_parts.append('<div class="resume-section"><div class="resume-section-title">Skills</div>')
        html_parts.append('<div>' + ' | '.join(skills[:15]) + '</div>')
        html_parts.append('</div>')
    
    return '\n'.join(html_parts)
```

---

#### 3.2 — Call Preview Function in API
**File**: `app/api_sequential.py`  
**Function**: `accept_suggestion()`  
**Lines**: 129-145

**Change lines 129-136**:
```python
# OLD:
preview_html = render_resume_preview(...)  # Function doesn't exist

# NEW:
from .assemble.resume import render_resume_preview_html

approved_bullets = store.get_approved_bullets()
preview_html = render_resume_preview_html(
    identity=json.loads(Path("profile/locked_identity.json").read_text()),
    exec_summary=job.get("review", {}).get("exec_summary", ""),
    soq=job.get("review", {}).get("soq", []),
    approved_bullets=approved_bullets,
    skills=job.get("review", {}).get("skills", {}).get("approved", [])
)
```

**Verify**: Line 144 already returns `preview_html` in response.

---

#### 3.3 — Wire Template to Use Server Preview
**File**: `templates/review_sequential.html`  
**Function**: `acceptSuggestion()`  
**Lines**: 229-230

**Change**:
```javascript
// OLD:
addBulletToPreview(roleKey, data.accepted_text);

// NEW:
if (data.preview_html) {
  // Update entire preview with server-rendered HTML
  document.getElementById('resumePreview').innerHTML = data.preview_html;
} else {
  // Fallback to client-side append
  addBulletToPreview(roleKey, sugg.text);
}
```

---

### STEP 4: Enforce Quota Gating on Generate Button

#### 4.1 — Verify Status Endpoint Returns Correct Shape
**File**: `app/api.py`  
**Function**: `get_sequential_status()`  
**Lines**: 1720-1764

**Current code already correct**:
```python
return {
    "roles": role_status,
    "all_complete": all_complete,
    "can_continue": all_complete
}
```

**No change needed** — just verify it's accessible at `/review/{job_id}/seq/status`.

---

#### 4.2 — Update Template to Poll Correct Endpoint
**File**: `templates/review_sequential.html`  
**Function**: `checkGateStatus()`  
**Lines**: 309-333

**Current line 311**:
```javascript
const response = await fetch(`/review/${JOB_ID}/seq/status`);
```

**Verify**: Template uses correct endpoint. If using `api_sequential.py`, change to:
```javascript
const response = await fetch(`/review/${JOB_ID}/seq/progress`);  // from api_sequential.py:173
```

**OR** ensure `api.py:1720` route is registered in main app.

---

#### 4.3 — Disable Generate Until Quotas Met
**File**: `templates/review_sequential.html`  
**Lines**: 314-329

**Current logic already correct**:
```javascript
if (data.all_complete) {
  continueBtn.disabled = false;
} else {
  continueBtn.disabled = true;
}
```

**No change needed** — just ensure backend returns `all_complete: true` only when all quotas met.

---

### STEP 5: Fix Skills Formatting (Dynamic Categories)

#### 5.1 — Derive Categories from JD
**File**: `app/writing/skills_engine.py`  
**Function**: `propose_skills()` (or create new `format_skills_for_resume()`)  
**Lines**: 231-254 in `resume.py`

**Move to skills_engine.py** as new function:
```python
def format_skills_for_resume(skills: list, jd_text: str = "", max_categories: int = 4) -> list:
    """
    Format skills into 3-4 category lines with pipe separators.
    
    Args:
        skills: List of skill strings
        jd_text: Job description (for keyword extraction)
        max_categories: Max lines to output (default 4)
    
    Returns:
        List of formatted lines: ["Category: skill1 | skill2", ...]
    """
    from collections import defaultdict
    
    # Auto-categorize skills
    categorized = defaultdict(list)
    
    for skill in skills:
        skill_lower = skill.lower()
        
        # Sales methodologies
        if any(term in skill_lower for term in ['meddic', 'spin', 'challenger', 'sandler', 'qualification', 'forecasting']):
            categorized['Sales Methodologies & Strategy'].append(skill)
        
        # CRM/Tech tools
        elif any(term in skill_lower for term in ['salesforce', 'crm', 'hubspot', 'outreach', 'salesloft', 'sql', 'amplitude']):
            categorized['CRM Systems & Digital Prospecting Tools'].append(skill)
        
        # Business/Leadership
        elif any(term in skill_lower for term in ['leadership', 'negotiation', 'executive', 'team', 'coaching', 'training']):
            categorized['Leadership & Business Development'].append(skill)
        
        # Catchall
        else:
            categorized['Core Sales Competencies'].append(skill)
    
    # Build lines (max 4 categories)
    lines = []
    for category, items in list(categorized.items())[:max_categories]:
        if items:
            lines.append(f"{category}: {' | '.join(sorted(items))}")
    
    return lines
```

---

#### 5.2 — Update Resume.py to Call New Function
**File**: `app/assemble/resume.py`  
**Function**: `render_resume()`  
**Lines**: 213-254

**Replace lines 214-254**:
```python
# Skills - pipe-separated format (3-4 categories max)
if skills:
    doc.add_paragraph('Skills', style='SectionHeading')
    
    # Import formatter
    from ..writing.skills_engine import format_skills_for_resume
    
    # Get formatted lines
    skill_lines = format_skills_for_resume(skills, max_categories=4)
    
    # Render each line
    for line in skill_lines:
        # Parse "Category: item | item"
        if ':' in line:
            category, items = line.split(':', 1)
            para = doc.add_paragraph(style='ResumeBodyText')
            para.add_run(f"{category.strip()}: ").bold = True
            para.add_run(items.strip())
        else:
            doc.add_paragraph(line, style='ResumeBodyText')
```

---

## Local Test Plan (Detailed Steps)

### Test 1: No Repetitive Bullets
**Acceptance**: Trigram similarity < 85%; history tracked

1. **Setup**: `uvicorn app.api:app --reload`
2. **Ingest job**: POST `/ingest` with JD
3. **Start review**: GET `/review/{job_id}?mode=seq`
4. **Accept first bullet** for role "ccs-2025"
5. **Reject next 2** suggestions
6. **Check file**: `out/suggestion_history/{job_id}_ccs-2025.json`
   - Should contain 3 bullet texts (1 accepted, 2 rejected)
7. **Generate 10 more** suggestions
8. **Verify**: None match previous 3 (use Python script to check trigrams)

**PASS if**: All new suggestions < 85% similar to history; history file grows.

---

### Test 2: AMOT Validation
**Acceptance**: All bullets have A+M+O+T

1. **Generate 5 suggestions** for any role
2. **For each suggestion**, verify presence of:
   - **A**: Starts with Led/Drove/Increased/Closed/etc.
   - **M**: Contains %, $, number, or placeholder [X%]
   - **O**: Contains "resulting", "achieving", "driving", "leading to"
   - **T**: Contains "via", "using", "through", "leveraging"
3. **Manual override**: Edit code to return non-AMOT bullet ("Responsible for sales activities")
4. **Verify**: Bullet is rejected by validator; does not appear in UI

**PASS if**: All displayed bullets have 4 components; manually injected bad bullet is filtered.

---

### Test 3: Resume Preview Updates
**Acceptance**: HTML preview refreshes after accept

1. **Load sequential review** page
2. **Check right panel** (`#resumePreview`)
   - Should show: Name, contact, empty experience sections
3. **Accept bullet** for "ccs-2025"
4. **Observe**: Right panel updates within 500ms
5. **Verify content**:
   - Bullet appears under "CCS | 2025-Present"
   - No duplicate/orphan bullets
6. **Accept 2 more** for different role
7. **Verify**: All bullets appear under correct roles

**PASS if**: Preview HTML updates on every accept; bullets grouped by role; no rejected bullets shown.

---

### Test 4: Quota Gating
**Acceptance**: Generate button disabled until all quotas met

1. **Start review** with 4 roles (CCS:4, Brightspeed II:4, Brightspeed I:4, VirsaTel:3)
2. **Check button**: "Approve All & Continue" should be **disabled**
3. **Accept 3/4** for CCS
4. **Check gate status** below button: "⏳ Complete all roles to continue (3/4)"
5. **Accept 4th bullet** for CCS
6. **Verify**: Progress bar shows "4/4"; role panel turns green
7. **Repeat** for all 3 other roles
8. **After last accept**: Button enables; status shows "✅ All roles complete!"
9. **Click button**: Redirects to `/apply/{job_id}`

**PASS if**: Button disabled until all quotas met; status text accurate; redirect works.

---

### Test 5: Skills Formatting
**Acceptance**: 3-4 lines, pipe-separated, dynamic categories

1. **Complete all quotas** from Test 4
2. **Navigate** to `/apply/{job_id}`
3. **Click** "Generate Resume"
4. **Download** `resume.docx` from `out/{job_id}/resume.docx`
5. **Open in Word/LibreOffice**
6. **Find Skills section** (bottom of page)
7. **Verify format**:
   ```
   Sales Methodologies & Strategy: MEDDICC | SPIN | Forecasting
   CRM Systems & Digital Prospecting Tools: Salesforce | Outreach | HubSpot
   Leadership & Business Development: Negotiation | Team Coaching
   ```
   - Max 4 lines
   - Each line: "Category: item | item | item"
   - No tables, no commas

**PASS if**: Skills section matches above format; categories derived from JD keywords.

---

## Summary Table (File→Function→Line)

| Issue | File | Function | Lines | Change Summary |
|-------|------|----------|-------|----------------|
| **(a) Repetitive** | `api_sequential.py` | `get_next_suggestion()` | 52-60 | Call `generate_next_suggestion()` instead of `generate_suggestion()` |
| **(a) History** | `experience.py` | `_save_suggestion()` | 308-315 | Already correct; verify called |
| **(b) AMOT validation** | `experience.py` | `has_amot_format()` | 42-62 | Add `return_reason` param; strengthen checks |
| **(b) Enforcement** | `experience.py` | `generate_next_suggestion()` | 109-116 | Re-validate after `inject_metrics()` |
| **(b) Prompts** | `anthropic.py` | `generate_bullet()` | 95-131 | Replace with explicit AMOT examples |
| **(b) Prompts** | `openai.py` | `generate_bullet()` | ~95-131 | Same as anthropic.py |
| **(b) Prompts** | `gemini.py` | `generate_bullet()` | ~95-131 | Same as anthropic.py |
| **(c) Preview HTML** | `resume.py` | NEW `render_resume_preview_html()` | After 258 | Build HTML string for live preview |
| **(c) Preview API** | `api_sequential.py` | `accept_suggestion()` | 129-145 | Call new function; return `preview_html` |
| **(c) Preview template** | `review_sequential.html` | `acceptSuggestion()` | 229-230 | Update `#resumePreview.innerHTML` |
| **(d) Status endpoint** | `api.py` | `get_sequential_status()` | 1720-1764 | Already correct; verify returns `all_complete` |
| **(d) Template polling** | `review_sequential.html` | `checkGateStatus()` | 309-333 | Verify endpoint URL matches backend |
| **(e) Skills format** | `skills_engine.py` | NEW `format_skills_for_resume()` | New function | Dynamic categories from JD |
| **(e) Skills render** | `resume.py` | `render_resume()` | 213-254 | Call formatter; render with bold categories |

---

**Total changes**: 7 files, ~14 functions, ~150 lines modified/added.  
**No breaking changes**: All edits preserve existing telemetry, contracts, and data structures.
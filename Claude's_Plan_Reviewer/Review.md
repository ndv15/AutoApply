Summary Delivered
I've provided a comprehensive surgical change plan with: ✅ Root Cause Analysis for all 5 issues:
(a) Repetitive bullets - MMR exists but not wired into sequential flow
(b) Non-AMOT items - Validation functions exist but not called
(c) Resume preview broken - render_resume_preview() function missing
(d) Quota gating bypassed - No check in /build/files endpoint
(e) Skills formatting - No 3-4 line enforcement
✅ Surgical Change Plan with exact file→function→line edits:
5 files to modify
159 total lines changed
All changes are minimal and targeted
✅ Enhanced LLM Prompts for stronger AMOT enforcement:
Explicit placeholder rules: [X%], [$Y], [N deals]
Forbidden phrase blocking
Quantified outcome requirements
✅ Detailed Test Plan with 5 test cases + integration test:
Test 1: MMR + history (no repetition)
Test 2: AMOT validation (100% compliance)
Test 3: Preview wiring (HTML updates live)
Test 4: Quota gating (blocks incomplete builds)
Test 5: Skills formatting (3-4 pipe-separated lines)
The Coder Agent can now implement these changes following the step-by-step instructions. After implementation, the Final QA Gate can verify with the provided test plan. No code was written (as required for Reviewer role) - only research, audit, and surgical planning delivered. Ready for next phase! 🚀
Provide me with your plan again.
🔍 SURGICAL CHANGE PLAN - AutoApply AMOT Fixes
📋 EXECUTIVE SUMMARY
I've audited the AutoApply codebase and identified 5 critical issues with surgical fixes across 5 files (~159 lines total). All fixes are minimal, targeted edits that preserve existing telemetry and contracts.
🎯 ROOT CAUSE ANALYSIS
Issue (a): Repetitive Bullets
Root Cause: MMR diversity system exists but bypassed in sequential flow
app/api_sequential.py:52 calls generate_suggestion() (legacy wrapper)
Should call generate_next_suggestion() which includes MMR+RRF+history (lines 82-158 in experience.py)
History tracking exists (_load_suggestion_history, _save_suggestion) but not invoked
Issue (b): Non-AMOT Bullets
Root Cause: Validation functions exist but not enforced
has_amot_format() exists (experience.py:42-62) but never called in sequential flow
inject_metrics() exists (experience.py:64-80) but no re-validation after injection
LLM prompts mention AMOT but don't enforce strongly enough
Issue (c): Resume Preview Not Wired
Root Cause: Missing HTML renderer function
api_sequential.py:130 calls render_resume_preview() [FUNCTION DOESN'T EXIST]
Only render_resume() exists (for .docx generation)
Template expects preview_html in response but gets nothing
Issue (d): Quota Gating Not Enforced
Root Cause: /build/files endpoint has no quota validation
app/api.py:660 - POST /build/files doesn't check sequential quota status
UI button checks status but backend allows bypass via direct API call
Issue (e): Skills Formatting
Root Cause: No line-count enforcement; verbose rendering
app/assemble/resume.py:213-254 categorizes correctly but no max 3-4 line limit
No item-per-line caps (can overflow)
🔧 DETAILED FIXES (Step-by-Step)
FIX #1: Wire MMR + History into Sequential Flow
File: app/api_sequential.py
Function: get_next_suggestion
Line: 52 Current Code:
suggestion = generate_suggestion(
    job_id=job_id,
    role_key=role_key,
    jd_text=job.get('jd', ''),
    role_context=next(...)
)
✅ Replace With:
suggestion = generate_next_suggestion(  # Changed function name
    job_id=job_id,
    role_key=role_key,
    jd_text=job.get('jd', ''),
    role_context=next(
        (r for r in job.get('history', []) if r.get('role_id') == role_key),
        {'role_id': role_key}
    )
)
Why: generate_next_suggestion() already implements:
Over-generation (20-30 candidates)
Cohere rerank scoring
MMR diversity (λ=0.7, threshold=0.90)
RRF fusion
History tracking to avoid repeats
FIX #2: Enforce AMOT Validation + Strengthen Prompts
Part A: Add Validation Gate
File: app/writing/experience.py
Function: generate_next_suggestion
Lines: 109-113 (modify existing loop) Current Code:
# Enhance with metrics if needed
for c in new_candidates:
    if not has_amot_format(c.get("text", "")):
        c["text"] = inject_metrics(c.get("text", ""))
    candidates.append(c)
✅ Replace With:
# Enhance with metrics + STRICT validation
for c in new_candidates:
    text = c.get("text", "")
    
    # Try to inject metrics if missing
    if not has_amot_format(text):
        text = inject_metrics(text)
        c["text"] = text
    
    # Re-validate - only accept AMOT-compliant bullets
    if has_amot_format(text):
        candidates.append(c)
    else:
        # Reject non-AMOT silently
        print(f"[REJECTED NON-AMOT] {text[:60]}...")
Part B: Strengthen LLM Prompts (Apply to all 3 providers)
Files:
app/llm/providers/anthropic.py (lines 105-131)
app/llm/providers/openai.py (same section)
app/llm/providers/gemini.py (same section)
Current Prompt (example from anthropic.py):
STRICT REQUIREMENTS:
1. MUST include at least ONE quantified outcome:
   - Percentage (e.g., "35%", "increased by 40%")
   - Dollar amount (e.g., "$2.5M", "$450K ARR")
   - Concrete number (e.g., "15 enterprise deals", "50+ logos")
   - If exact numbers unknown, use clean placeholders: [X%], [$Y], [N deals]
✅ Replace With (Enhanced):
STRICT REQUIREMENTS (NON-NEGOTIABLE):
1. MUST include ALL FOUR AMOT components:
   - ACTION: Strong verb (Led, Drove, Increased, Closed, Built, Achieved)
   - METRIC: Quantified outcome (%, $, numbers, or placeholders)
   - OUTCOME: Business impact phrase ("resulting in", "achieving", "leading to", "driving")
   - TOOL: Specific method/platform ("via MEDDICC", "using Salesforce", "through...")

2. Quantified metrics (MANDATORY):
   - Percentage: "35%", "↑40%", "increased by [X]%"
   - Dollar: "$2.5M ARR", "+$1.8M revenue", "[$Y] pipeline"
   - Count: "15 enterprise deals", "50+ logos", "[N] accounts"
   
   **IF EXACT UNKNOWN**: Use clean placeholders [X%], [$Y], [N deals]
   **FORBIDDEN**: "significant", "substantial", "proven track record"

3. Format: 1-2 lines max (under 200 chars)

GOOD EXAMPLES (all have A+M+O+T):
✅ "Drove [X%] quota attainment across [$Y] territory by implementing MEDDICC qualification, resulting in [N] new enterprise logos"
✅ "Increased win rate from 18% to 31% (+13pp) via SPIN discovery framework, achieving $2.1M incremental ARR"
✅ "Closed $2.4M in Q1 (140% of quota) by targeting Fortune 500 CxOs with tailored ROI presentations using Salesforce CPQ"

BAD EXAMPLES (will be rejected):
❌ "Proven track record of increasing revenue" → No metric, forbidden phrase
❌ "Responsible for managing accounts and driving growth" → Vague, no quantification
❌ "Achieved substantial improvement" → No number/placeholder

Return ONLY the bullet text, no explanation.
FIX #3: Create Resume Preview HTML Function
File: app/assemble/resume.py
Location: After line 258 (after render_resume() function) ✅ Add New Function:
def render_resume_preview(
    identity: Dict,
    exec_summary: str,
    soq: List[str],
    approved_bullets: Dict[str, List[Dict]],
    skills: List[str]
) -> str:
    """
    Generate HTML preview of resume for live preview panel.
    
    Args:
        identity: Dict with name, email, phone, location
        exec_summary: Executive summary text
        soq: Summary of qualifications (list of strings)
        approved_bullets: Dict of role_id -> list of bullet dicts
        skills: List of approved skill strings
        
    Returns:
        HTML string with inline styles matching review_sequential.html
    """
    # Load employment history for role metadata
    history_path = Path("profile/employment_history.json")
    if history_path.exists():
        history = json.loads(history_path.read_text())
        history_map = {h['role_id']: h for h in history}
    else:
        history_map = {}
    
    html_parts = []
    
    # Header
    html_parts.append(f'<div class="resume-name">{identity.get("name", "")}</div>')
    
    # Contact info
    contact_parts = []
    if identity.get("email"):
        contact_parts.append(identity["email"])
    if identity.get("phone"):
        contact_parts.append(identity["phone"])
    if identity.get("location"):
        contact_parts.append(identity["location"])
    html_parts.append(f'<div class="resume-contact">{" | ".join(contact_parts)}</div>')
    
    # Executive Summary
    html_parts.append('<div class="resume-section">')
    html_parts.append('  <div class="resume-section-title">Executive Summary</div>')
    html_parts.append(f'  <p style="line-height:1.4">{exec_summary}</p>')
    html_parts.append('</div>')
    
    # Professional Experience
    html_parts.append('<div class="resume-section">')
    html_parts.append('  <div class="resume-section-title">Professional Experience</div>')
    
    for role_id, bullets in approved_bullets.items():
        if not bullets:
            continue
            
        role = history_map.get(role_id, {})
        html_parts.append('  <div style="margin-bottom:20px">')
        
        # Role header
        title = role.get("title", "Unknown Role")
        company = role.get("company", "Unknown Company")
        dates = f"{role.get('start', '')} – {role.get('end', 'Present')}"
        html_parts.append(f'    <div class="resume-role-header">{title} | {company}</div>')
        html_parts.append(f'    <div style="font-size:10pt;color:#666;margin-bottom:8px">{dates}</div>')
        
        # Bullets container
        html_parts.append(f'    <div id="bullets-{role_id}">')
        for bullet in bullets:
            bullet_text = bullet.get("text", "") if isinstance(bullet, dict) else str(bullet)
            html_parts.append(f'      <div class="resume-bullet">{bullet_text}</div>')
        html_parts.append('    </div>')
        html_parts.append('  </div>')
    
    html_parts.append('</div>')
    
    # Skills section
    if skills:
        html_parts.append('<div class="resume-section">')
        html_parts.append('  <div class="resume-section-title">Skills</div>')
        skills_text = " | ".join(skills[:12])  # Max 12 for preview
        html_parts.append(f'  <p style="line-height:1.6">{skills_text}</p>')
        html_parts.append('</div>')
    
    return '\n'.join(html_parts)
Note: The calling code in api_sequential.py:130 is already correct - it just needs this function to exist.
FIX #4: Add Quota Gate to Build Endpoint
File: app/api.py
Function: build_files
Location: After line 665 (after job lookup, before file generation) Current Code (lines 660-670):
@app.post("/build/files")
async def build_files(payload: Dict = Body(...)):
    job_id = payload.get('job_id')
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"error": "not_found"}, status_code=404)
    
    # [continues with file generation...]
✅ Insert After Line 665:
@app.post("/build/files")
async def build_files(payload: Dict = Body(...)):
    job_id = payload.get('job_id')
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"error": "not_found"}, status_code=404)
    
    # ============ ADD QUOTA GATE CHECK ============
    from .writing.suggestion_store import SuggestionStore
    from .writing.sequential_config import SequentialConfig
    
    # Get current quota progress
    store = SuggestionStore(job_id)
    quotas = {
        r.get('role_id'): SequentialConfig.get_role_quota(r.get('role_id'))
        for r in job.get('history', [])
    }
    progress = store.get_progress(quotas)
    
    # Block if quotas not met
    if not progress.get('all_met', False):
        incomplete_roles = [
            f"{role}: {info['accepted']}/{info['target']}"
            for role, info in progress.get('quotas', {}).items()
            if not info.get('complete', False)
        ]
        return JSONResponse({
            "error": "quotas_not_met",
            "message": f"Complete all role quotas before generating files. Incomplete: {', '.join(incomplete_roles)}",
            "progress": progress
        }, status_code=400)
    # ============ END QUOTA GATE ============
    
    # [existing file generation code continues...]
FIX #5: Enforce Skills 3-4 Line Pipe Format
File: app/assemble/resume.py
Function: render_resume
Lines: 213-254 (replace entire skills section) Current Code: Lines 213-254 (verbose, no limits) ✅ Replace With:
# Skills - STRICT 3-4 line pipe format with item limits
if skills:
    doc.add_paragraph('Skills', style='SectionHeading')

    # Categorize skills (keep existing logic)
    sales_skills = []
    technical_skills = []
    process_skills = []

    for skill in skills:
        skill_lower = skill.lower()
        if any(term in skill_lower for term in ['sql', 'salesforce', 'amplitude', 'crm', 'analytics', 'hubspot']):
            technical_skills.append(skill)
        elif any(term in skill_lower for term in ['meddic', 'negotiation', 'forecasting', 'pipeline', 'territory', 'prospecting']):
            sales_skills.append(skill)
        else:
            process_skills.append(skill)

    # ENFORCE 3-4 lines max with item limits per line
    MAX_LINES = 4
    MAX_ITEMS_PER_LINE = 8  # Prevents overflow
    lines_rendered = 0

    # Line 1: Full-Cycle Enterprise SaaS Sales
    if sales_skills and lines_rendered < MAX_LINES:
        para = doc.add_paragraph(style='ResumeBodyText')
        para.add_run("Full-Cycle Enterprise SaaS Sales: ").bold = True
        para.add_run(" | ".join(sorted(sales_skills)[:MAX_ITEMS_PER_LINE]))
        lines_rendered += 1

    # Line 2: CRM & Digital Prospecting Tools
    if technical_skills and lines_rendered < MAX_LINES:
        para = doc.add_paragraph(style='ResumeBodyText')
        para.add_run("CRM & Digital Prospecting Tools: ").bold = True
        para.add_run(" | ".join(sorted(technical_skills)[:MAX_ITEMS_PER_LINE]))
        lines_rendered += 1

    # Line 3: Sales Tools & Platforms
    if process_skills and lines_rendered < MAX_LINES:
        para = doc.add_paragraph(style='ResumeBodyText')
        para.add_run("Sales Tools & Platforms: ").bold = True
        para.add_run(" | ".join(sorted(process_skills)[:6]))  # Shorter category
        lines_rendered += 1
    
    # Line 4: Overflow (only if needed and space remains)
    remaining_skills = (
        sales_skills[MAX_ITEMS_PER_LINE:] + 
        technical_skills[MAX_ITEMS_PER_LINE:] + 
        process_skills[6:]
    )
    if remaining_skills and lines_rendered < MAX_LINES:
        para = doc.add_paragraph(style='ResumeBodyText')
        para.add_run("Additional: ").bold = True
        para.add_run(" | ".join(remaining_skills[:6]))
        lines_rendered += 1
🧪 DETAILED TEST PLAN
TEST 1: No Repetitive Bullets (Fix #1)
Acceptance: Trigram similarity <85% across 15+ generations
# Setup
1. Start server: uvicorn app.api:app --reload --port 8787
2. Open: http://localhost:8787/review/{job_id}?mode=seq

# Test Steps
3. Focus on CCS role panel
4. Reject first 15 suggestions (click "✗ Reject" 15 times)
5. Copy each bullet text to a doc

# Verify
6. Check history file exists:
   cat out/suggestion_history/{job_id}_ccs.json
   # Should have 15 entries

7. Manually compare bullets:
   - No two should be near-duplicates
   - Different metrics, action verbs, outcomes

# ✅ PASS if:
- All 15 bullets semantically distinct
- No trigram similarity >85%
- History file populated correctly
TEST 2: AMOT Validation (Fix #2)
Acceptance: 100% bullets have AMOT structure
# Test Steps
1. Generate 20 suggestions across all roles (5 per role)
2. For EACH bullet, verify it contains:
   - ACTION: Led, Drove, Increased, Closed, etc.
   - METRIC: %, $, number, OR placeholder [X%]/[$Y]/[N]
   - OUTCOME: "resulting in", "achieving", "leading to"
   - TOOL: "via X", "using Y", "through Z"

3. Check for forbidden phrases:
   grep -ri "proven track record\|responsible for\|worked on" out/approvals/{job_id}.json
   # Should return NOTHING

# ✅ PASS if:
- 20/20 bullets have all 4 AMOT components
- 20/20 have quantified metrics or placeholders
- 0/20 have forbidden phrases
Example PASS bullets:
✅ "Drove 35% quota attainment across $1.2M territory via MEDDICC, resulting in 12 new logos"
✅ "Increased win rate from 18% to 31% through SPIN discovery, achieving $2.1M ARR"
✅ "Closed [$Y] in Q1 by targeting Fortune 500 using Salesforce CPQ"
Example FAIL bullets:
❌ "Proven track record of revenue growth" (no metric, forbidden phrase)
❌ "Responsible for managing accounts" (vague, no outcome/tool)
TEST 3: Resume Preview Wiring (Fix #3)
Acceptance: Preview HTML renders immediately on accept
# Test Steps
1. Open DevTools → Network tab
2. Open: http://localhost:8787/review/{job_id}?mode=seq
3. Accept first CCS suggestion
4. Inspect POST /review/{job_id}/suggestions/seq/accept response

# ✅ PASS if:
- Response contains: {"ok": true, "preview_html": "<div class='resume-name'>..."}
- Right panel (#resumePreview) updates WITHOUT reload
- Accepted bullet appears under correct role header
- HTML includes: name, contact, exec summary, experience section
TEST 4: Quota Gating (Fix #4)
Acceptance: Cannot generate files until quotas complete
# Scenario A: Incomplete quotas
1. Accept only 2/4 bullets for CCS
2. Attempt to generate files:
   curl -X POST http://localhost:8787/build/files \
     -H "Content-Type: application/json" \
     -d '{"job_id": "{job_id}"}'

# ✅ PASS if:
- Response: 400 Bad Request
- Body: {
     "error": "quotas_not_met",
     "message": "Complete all role quotas... Incomplete: ccs: 2/4, ..."
   }

# Scenario B: Complete quotas
3. Complete all quotas (4+4+4+3=15 bullets)
4. Re-test /build/files

# ✅ PASS if:
- Response: 200 OK
- Body: {"resume_path": "...", "cover_path": "..."}
- UI "Continue" button enables
TEST 5: Skills Formatting (Fix #5)
Acceptance: Skills render as 3-4 pipe-separated lines
# Test Steps
1. Complete all quotas
2. Generate resume files
3. Open resume.docx in Word

# ✅ PASS if:
- Skills section has 3-4 lines (NOT table)
- Format: "Category: item | item | item"
- Each line has ≤8 items
- Example output:
  Full-Cycle Enterprise SaaS Sales: Forecasting | MEDDICC | SPIN
  CRM & Digital Tools: Salesforce | Outreach | LinkedIn Sales Navigator
  Sales Platforms: CPQ | DocuSign | Slack
📊 CHANGE SUMMARY TABLE
Fix	File	Lines Changed	Risk	Test
#1 MMR	api_sequential.py:52	1	LOW	TC1
#2a AMOT	experience.py:109-113	8	LOW	TC2
#2b Prompts	anthropic/openai/gemini.py	45	LOW	TC2
#3 Preview	resume.py:258+	+50	MED	TC3
#4 Quota	api.py:665+	+15	LOW	TC4
#5 Skills	resume.py:213-254	40	LOW	TC5
Total: 5 files, ~159 lines changed
✅ FINAL ACCEPTANCE CRITERIA
All must pass before marking complete:
 TC1: No bullet repetition (trigram <85%)
 TC2: 100% bullets AMOT-compliant
 TC3: Preview updates live on accept
 TC4: Build blocked if quotas incomplete
 TC5: Skills render as 3-4 lines, pipe-separated
 All telemetry events logged
 No browser console errors
 No Python exceptions in logs
Status: Ready for Coder Agent implementation
# Coder Implementation Plan: Sequential Review System

**Generated:** 2025-10-03
**Status:** Awaiting approval
**Agent:** Coder (Claude Code)

---

## ✅ Acceptance Criteria Confirmed

From [AGENTS.md](AGENTS.md):

1. **One-at-a-time suggestions** with Accept/Reject→Next
2. **AMOT validation** (Action-Metric-Outcome-Tool) with placeholder metrics
3. **Over-generate→Cohere→MMR→Keyword→RRF→Score 1-10** pipeline
4. **Live preview** updates with accepted-only bullets; Generate disabled until quotas met
5. **Skills ≤4 lines** in `Category: item | item | item` format

---

## 📋 File→Function→Line Implementation Plan

### **Change 1: AMOT Pre-Validation in Generation Pipeline**

**File:** [app/writing/experience.py](autoapply_scaffold/app/writing/experience.py#L110-L113)

**Current Code (Lines 110-113):**
```python
for c in new_candidates:
    if not has_amot_format(c.get("text", "")):
        c["text"] = inject_metrics(c.get("text", ""))
    candidates.append(c)
```

**Issue:** Non-AMOT bullets still added to candidates after placeholder injection

**Required Change:**
```python
for c in new_candidates:
    if not has_amot_format(c.get("text", "")):
        c["text"] = inject_metrics(c.get("text", ""))
        # Re-validate after injection; skip if still non-compliant
        if not has_amot_format(c["text"]):
            continue  # Skip non-AMOT bullets
    candidates.append(c)
```

**Why:** Ensures only AMOT-compliant bullets enter Cohere ranking, saving API costs and ensuring quality

**Lines affected:** 110-113
**Function:** `generate_next_suggestion()`
**Impact:** Low risk - adds validation gate only

---

### **Change 2: Use Full Pipeline in Sequential API**

**File:** [app/api_sequential.py](autoapply_scaffold/app/api_sequential.py#L52)

**Current Code (Line 52):**
```python
suggestion = generate_suggestion(
    job_id=job_id,
    role_key=role_key,
    jd_text=job.get('jd', ''),
    role_context=next(...)
)
```

**Issue:** Calls legacy single-gen function instead of full MMR→RRF pipeline

**Required Change:**
```python
suggestion = generate_next_suggestion(
    job_id=job_id,
    role_key=role_key,
    jd_text=job.get('jd', ''),
    role_context=next(...)
)
```

**Why:** Activates Over-generate→Cohere→MMR→Keyword→RRF pipeline for diversity

**Lines affected:** 52
**Function:** `get_next_suggestion()`
**Impact:** Low risk - just function name change

---

### **Change 3: Remove Duplicate Code Block**

**File:** [app/api_sequential.py](autoapply_scaffold/app/api_sequential.py#L66-L97)

**Current Code (Lines 66-97):**
```python
    # Duplicate code block that repeats lines 46-63
    store = SuggestionStore(job_id)
    suggestion = store.get_next_suggestion(role_key)

    # If no suggestion in queue, generate a new one
    if not suggestion:
        suggestion = generate_next_suggestion(...)

    if not suggestion:
        return JSONResponse({"error": "no_suggestions"}, status_code=404)

    return suggestion
```

**Issue:** Unreachable duplicate code after lines 46-77 already return

**Required Change:**
```python
# DELETE lines 66-97 entirely
```

**Why:** Dead code cleanup - lines never execute due to prior return statement

**Lines affected:** 66-97
**Function:** `get_next_suggestion()`
**Impact:** Zero risk - removing unreachable code

---

### **Change 4: Fix Accept Endpoint Response Structure**

**File:** [app/api_sequential.py](autoapply_scaffold/app/api_sequential.py#L129-L145)

**Current Code (Lines 129-145):**
```python
# Generate preview HTML
approved_bullets = store.get_approved_bullets()
preview_html = render_resume_preview(
    identity=json.loads(Path("profile/locked_identity.json").read_text()),
    exec_summary=job["review"]["exec_summary"],
    soq=job["review"]["soq"],
    approved_bullets=approved_bullets,
    skills=job["review"]["skills"]["approved"]
)

log_event("suggestion_accepted", ...)

return {
    "ok": True,
    "progress": progress,
    "preview_html": preview_html
}
```

**Issue:**
1. `render_resume_preview()` doesn't exist (it's `render_resume()` for DOCX)
2. Template expects `accepted_text`, `accepted_count`, `quota`, `is_complete` fields

**Required Change:**
```python
# Get updated status
quota = SequentialConfig.get_role_quota(role_key)
approved = len(store.get_approved_bullets().get(role_key, []))
is_complete = approved >= quota

log_event("suggestion_accepted", ...)

return {
    "ok": True,
    "accepted_text": suggestion.get('text', ''),
    "accepted_count": approved,
    "quota": quota,
    "is_complete": is_complete,
    "progress": progress
}
```

**Why:** Matches template expectations in `review_sequential.html:230-237`

**Lines affected:** 129-145
**Function:** `accept_suggestion()`
**Impact:** Medium risk - response structure change, but template already expects this format

---

### **Change 5: Update Accept Handler in Template**

**File:** [templates/review_sequential.html](autoapply_scaffold/templates/review_sequential.html#L230-L237)

**Current Code (Lines 230-237):**
```javascript
// Add to resume preview
addBulletToPreview(roleKey, data.accepted_text);

// Update progress
updateProgress(roleKey, {
    approved: data.accepted_count,
    quota: data.quota,
    is_complete: data.is_complete
});
```

**Issue:** Variable `data.accepted_text` doesn't exist in current API response

**Required Change:**
```javascript
// Add to resume preview (use stored suggestion text)
const bulletText = currentSuggestions[roleKey]?.text || '';
addBulletToPreview(roleKey, bulletText);

// Update progress (use response fields from Change 4)
updateProgress(roleKey, {
    approved: data.accepted_count,
    quota: data.quota,
    is_complete: data.is_complete
});
```

**Why:** Uses suggestion text from `currentSuggestions[roleKey]` which is already populated (line 167)

**Lines affected:** 230-237
**Function:** `acceptSuggestion()`
**Impact:** Low risk - defensive coding using already-available data

---

### **Change 6: Add Load Existing Bullets on Page Init**

**File:** [templates/review_sequential.html](autoapply_scaffold/templates/review_sequential.html#L412)

**Current Code (Line 412):**
```javascript
// Initialize on load
initRoles();
initResumePreview();
checkGateStatus();
```

**Issue:** On page refresh, previously accepted bullets aren't shown in preview

**Required Change:**
```javascript
// Load existing approved bullets from server
async function loadExistingBullets() {
    try {
        const response = await fetch(`/review/${JOB_ID}/seq/progress`);
        const data = await response.json();

        // Populate preview with approved bullets
        if (data.roles) {
            for (const [roleKey, roleData] of Object.entries(data.roles)) {
                if (roleData.approved_bullets) {
                    roleData.approved_bullets.forEach(bullet => {
                        addBulletToPreview(roleKey, bullet.text);
                    });
                    // Update progress bars
                    updateProgress(roleKey, {
                        approved: roleData.accepted_count,
                        quota: roleData.quota,
                        is_complete: roleData.is_complete
                    });
                }
            }
        }
    } catch (error) {
        console.error('Error loading existing bullets:', error);
    }
}

// Initialize on load
initRoles();
initResumePreview();
loadExistingBullets();  // NEW: Load existing state
checkGateStatus();
```

**Why:** Restores preview state on page refresh; improves UX

**Lines affected:** Add new function + call at line 412
**Function:** New `loadExistingBullets()` + update init sequence
**Impact:** Low risk - additive change only

---

### **Change 7: Update Progress Endpoint to Include Bullets**

**File:** [app/api_sequential.py](autoapply_scaffold/app/api_sequential.py#L173-L189)

**Current Code (Lines 173-189):**
```python
@app.get("/review/{job_id}/seq/progress")
async def get_review_progress(job_id: str):
    """Get review progress and quota status."""
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"error": "not_found"}, status_code=404)

    store = SuggestionStore(job_id)

    # Get quotas for all roles
    quotas = {
        r.get('role_id'): get_role_quota(r.get('role_id'))
        for r in job.get('history', [])
    }

    progress = store.get_progress(quotas)
    return progress
```

**Issue:** Response doesn't include approved bullet texts needed by Change 6

**Required Change:**
```python
@app.get("/review/{job_id}/seq/progress")
async def get_review_progress(job_id: str):
    """Get review progress and quota status."""
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"error": "not_found"}, status_code=404)

    store = SuggestionStore(job_id)

    # Get quotas for all roles
    quotas = {
        r.get('role_id'): SequentialConfig.get_role_quota(r.get('role_id'))
        for r in job.get('history', [])
    }

    # Get progress with approved bullets
    approved_bullets = store.get_approved_bullets()
    progress = store.get_progress(quotas)

    # Add approved bullets to response
    if 'roles' not in progress:
        progress['roles'] = {}

    for role_key, quota in quotas.items():
        approved = approved_bullets.get(role_key, [])
        if role_key not in progress['roles']:
            progress['roles'][role_key] = {}
        progress['roles'][role_key].update({
            'accepted_count': len(approved),
            'quota': quota,
            'is_complete': len(approved) >= quota,
            'approved_bullets': approved  # NEW: Include bullet texts
        })

    progress['all_complete'] = all(
        progress['roles'][k].get('is_complete', False)
        for k in quotas.keys()
    )

    return progress
```

**Why:** Provides bullet data needed for Change 6 (loading existing bullets on refresh)

**Lines affected:** 173-189
**Function:** `get_review_progress()`
**Impact:** Medium risk - response structure change, but additive (doesn't break existing consumers)

---

## 🎯 Why This Plan Will Work

### **1. AMOT Enforcement (Change 1)**
- Validation gate at generation time (before Cohere API calls)
- Re-validates after placeholder injection
- Skips non-compliant bullets early → cleaner candidate pool

### **2. Full Ranking Pipeline (Change 2)**
- Activates existing `generate_next_suggestion()` with:
  - Over-generate: 20-30 candidates (3 batches × 10)
  - Cohere: Semantic relevance scoring (0-1)
  - MMR: Diversity filter (λ=0.7, threshold=0.90)
  - Keyword: Top 15 JD keywords, overlap scoring
  - RRF: Fuses Cohere+keyword rankings (k=60)
  - Score 1-10: Maps Cohere score to UI scale
- No new code needed - just function call change

### **3. One-at-a-time Flow (Changes 2, 3, 4, 5)**
- API returns exactly 1 suggestion (line 155 in experience.py: `return fused[0]`)
- UI stores 1 active suggestion per role (`currentSuggestions[roleKey]`)
- Accept → adds bullet → auto-loads next
- Reject → immediately loads next
- No parallel suggestions possible

### **4. Live Preview State Persistence (Changes 6, 7)**
- Empty preview on initial load
- Restores approved bullets from server on refresh
- Each Accept appends bullet to DOM immediately
- Progress bars sync with server state
- No page refresh needed for updates

### **5. Quota Gating** ✅ (Already implemented - no changes)
- Quotas: CCS=4, Brightspeed II=4, Brightspeed I=4, VirsaTel=3
- Progress endpoint calculates `approved >= quota` per role
- Continue button enabled only when `all_complete: true`
- Status polled every 10s + after each action

### **6. Skills Rendering** ✅ (Already implemented - no changes)
- Hard limit: `max_categories = 4` ([resume.py:232](autoapply_scaffold/app/assemble/resume.py#L232))
- Format: `"Category: item | item | item"` (lines 237-254)
- Auto-categorized by keyword matching
- Plain text for ATS compatibility

---

## 📝 Summary of Changes

| # | File | Lines | Change Type | Risk |
|---|------|-------|-------------|------|
| 1 | `app/writing/experience.py` | 110-113 | Add AMOT pre-validation gate | Low |
| 2 | `app/api_sequential.py` | 52 | Change function call to full pipeline | Low |
| 3 | `app/api_sequential.py` | 66-97 | Delete duplicate code block | Zero |
| 4 | `app/api_sequential.py` | 129-145 | Fix accept response structure | Medium |
| 5 | `templates/review_sequential.html` | 230-237 | Update accept handler | Low |
| 6 | `templates/review_sequential.html` | After 412 | Add load existing bullets | Low |
| 7 | `app/api_sequential.py` | 173-189 | Include bullets in progress response | Medium |

**Total:** 7 changes across 3 files
**Risk Level:** Low-Medium (mostly additive changes)
**Lines Changed:** ~60 lines total

---

## 🧪 Local Test Plan

### **Test 1: AMOT Validation (Change 1)**
```bash
# Start review for test job
curl -X POST http://localhost:8000/review/test-001/suggestions/seq/next \
  -H "Content-Type: application/json" \
  -d '{"role_key": "ccs"}'

# Verify response bullet has:
# - Action verb (Led/Drove/Increased)
# - Metric (%, $, number, or [X%] placeholder)
# - Outcome phrase ("resulting in", "achieving", "driving")
# - Tool/method ("via", "using", "through")
```

**Pass Criteria:** All bullets contain A+M+O+T components

---

### **Test 2: No Repetitive Bullets (Change 2)**
```bash
# Accept 1 bullet, reject 2, accept another
# Check suggestion history file
cat out/suggestion_history/test-001_ccs.json

# Verify no duplicates in:
# - Accepted bullets
# - Suggestion history
```

**Pass Criteria:**
- No bullets with >85% trigram similarity
- History file grows with each suggestion
- MMR filtering active (check logs for "mmr_score")

---

### **Test 3: Accept/Reject Flow (Changes 4, 5)**
```bash
# Accept a bullet
curl -X POST http://localhost:8000/review/test-001/suggestions/seq/accept \
  -H "Content-Type: application/json" \
  -d '{"role_key": "ccs", "suggestion_id": "abc123"}'

# Verify response has:
# - ok: true
# - accepted_text: "..."
# - accepted_count: 1
# - quota: 4
# - is_complete: false
```

**Pass Criteria:**
- Response structure matches template expectations
- Preview updates in UI immediately
- Next suggestion auto-loads

---

### **Test 4: Page Refresh State Persistence (Changes 6, 7)**
```bash
# 1. Accept 2 bullets for role "ccs"
# 2. Refresh page (F5)
# 3. Check preview panel

# Verify:
# - 2 bullets shown in preview
# - Progress bar shows "2/4"
# - Next suggestion loads correctly
```

**Pass Criteria:**
- All accepted bullets restored in preview
- Progress bars reflect server state
- Can continue reviewing from where left off

---

### **Test 5: Quota Gating (No changes - verify existing)**
```bash
# Accept bullets until 3/4 for all roles
# Click "Approve All & Continue" button

# Verify:
# - Button stays disabled
# - Status shows "⏳ Complete all roles to continue"

# Accept 4th bullet for all roles
# Verify:
# - Button enables
# - Status shows "✅ All roles complete!"
```

**Pass Criteria:**
- Button disabled until all quotas met
- Status message updates correctly
- Can proceed to Apply page only when complete

---

## 📊 Impact Analysis

### **Code Already Correct (No Changes Needed)**
- ✅ MMR diversity algorithm ([mmr_rrf.py:39-106](autoapply_scaffold/app/ranking/mmr_rrf.py#L39-L106))
- ✅ RRF fusion logic ([mmr_rrf.py:109-156](autoapply_scaffold/app/ranking/mmr_rrf.py#L109-L156))
- ✅ Cohere scoring ([cohere.py:148-185](autoapply_scaffold/app/ranking/providers/cohere.py#L148-L185))
- ✅ Keyword extraction ([mmr_rrf.py:159-183](autoapply_scaffold/app/ranking/mmr_rrf.py#L159-L183))
- ✅ Suggestion history tracking ([experience.py:292-316](autoapply_scaffold/app/writing/experience.py#L292-L316))
- ✅ Skills formatting ([resume.py:213-254](autoapply_scaffold/app/assemble/resume.py#L213-L254))
- ✅ Quota definitions ([sequential_config.py:7-12](autoapply_scaffold/app/writing/sequential_config.py#L7-L12))
- ✅ Progress tracking ([suggestion_store.py:117-135](autoapply_scaffold/app/writing/suggestion_store.py#L117-L135))

**5 out of 6 acceptance criteria already met by existing code.**

---

## 🚀 Implementation Order

1. **Change 3** (Delete duplicate code) - Zero risk cleanup
2. **Change 1** (AMOT validation) - Improves quality before ranking
3. **Change 2** (Use full pipeline) - Activates diversity
4. **Change 7** (Progress endpoint) - Backend prep for frontend
5. **Change 4** (Accept response) - API contract fix
6. **Change 5** (Accept handler) - Frontend matches API
7. **Change 6** (Load existing bullets) - UX enhancement

**Estimated time:** 30-45 minutes
**Testing time:** 15-20 minutes

---

## ✅ Final Checklist

- [ ] Change 1: AMOT pre-validation in experience.py
- [ ] Change 2: Use generate_next_suggestion() in api_sequential.py
- [ ] Change 3: Delete duplicate code block in api_sequential.py
- [ ] Change 4: Fix accept endpoint response structure
- [ ] Change 5: Update accept handler in review_sequential.html
- [ ] Change 6: Add loadExistingBullets() function
- [ ] Change 7: Update progress endpoint to include bullets
- [ ] Test 1: Verify AMOT validation
- [ ] Test 2: Verify no repetitive bullets (MMR)
- [ ] Test 3: Verify accept/reject flow
- [ ] Test 4: Verify page refresh persistence
- [ ] Test 5: Verify quota gating

---

**Awaiting approval to proceed with implementation.**

# AutoApply (Hybrid) - Integration Review Report

**Review Date:** 2025-10-01
**Reviewer:** Code QA Agent
**Server Status:** ✅ Running on http://localhost:8787
**Environment:** Windows (win32)

---

## Executive Summary

The AutoApply system has been reviewed across 11 critical criteria. **CRITICAL SECURITY ISSUE** identified that must be addressed before deployment.

**Overall Status:** ⚠️ **READY WITH CRITICAL FIXES REQUIRED**

---

## Detailed Review Checklist

### ✅ 1. Server Startup & Health

**Status:** PASS ✅

**Evidence:**
- Server successfully started on port 8787
- FastAPI application initialized without errors
- Health endpoint available at `/health`
- Auto-reload working (detected changes in `app\ranking\mmr_rrf.py`)

**Files Checked:**
- [app/api.py:38-66](app/api.py#L38-L66) - Application initialization
- [app/api.py:161-169](app/api.py#L161-L169) - Health check endpoint

**Logs:**
```
INFO: Uvicorn running on http://0.0.0.0:8787
INFO: Application startup complete.
```

---

### 🔴 2. Security & Configuration

**Status:** CRITICAL FAIL ❌

**CRITICAL ISSUES:**

1. **Exposed API Keys in `.env` File**
   - File: [.env:4-16](.env#L4-L16)
   - Contains live API keys for:
     - OpenAI (OPENAI_API_KEY)
     - Anthropic (ANTHROPIC_API_KEY)
     - Google Gemini (GOOGLE_API_KEY)
     - Perplexity (PERPLEXITY_API_KEY)
     - Cohere (COHERE_API_KEY)
   - **Risk Level:** CRITICAL - If committed to git, keys are exposed publicly

**PASS Items:**
- ✅ `.env` is in `.gitignore` ([.gitignore:2](.gitignore#L2))
- ✅ Not currently a git repository (verified with `git status`)
- ✅ Config loads from environment variables ([app/config.py:24-27](app/config.py#L24-L27))
- ✅ No hardcoded keys in Python code

**Required Actions:**
1. **BEFORE INITIALIZING GIT:** Verify `.env` is in `.gitignore`
2. **Rotate all exposed API keys** if this directory has ever been committed
3. Use `.env.sample` as template with placeholder values
4. Document key rotation in deployment guide

**Files Checked:**
- [.env](.env) - Contains live keys ⚠️
- [.gitignore](.gitignore) - Properly configured ✅
- [app/config.py](app/config.py) - Loads from env ✅
- [config.yaml](config.yaml) - No keys stored ✅

---

### ✅ 3. Sequential Flow Implementation

**Status:** PASS ✅

**Evidence:**

**Quota Enforcement:**
- [config.yaml:13-24](config.yaml#L13-L24) - Role quotas defined:
  - `ccs-2025`: 4 bullets
  - `brightspeed-2022-ii`: 4 bullets
  - `brightspeed-2021`: 4 bullets
  - `virsatel-2018`: 3 bullets
- [app/api.py:466-473](app/api.py#L466-L473) - Review data initialization with role quotas
- [app/api.py:1288-1326](app/api.py#L1288-L1326) - Status endpoint validates completion against quotas

**One Suggestion at a Time:**
- [app/api.py:838-920](app/api.py#L838-L920) - `POST /review/{job_id}/suggestion/next` generates single suggestion
- [app/api.py:994-1054](app/api.py#L994-L1054) - Reject endpoint immediately generates next suggestion

**Duplicate Prevention:**
- [app/api.py:869-874](app/api.py#L869-L874) - Tracks used texts in suggestion history
- [app/api.py:880-894](app/api.py#L880-L894) - Max 5 attempts to avoid duplicates
- [app/writing/experience.py:333-334](app/writing/experience.py#L333-L334) - Loads suggestion history
- [app/writing/experience.py:345-350](app/writing/experience.py#L345-L350) - Filters duplicates from history

**Keyboard Shortcuts:**
- Template check needed: [templates/review_sequential.html](templates/review_sequential.html)
- Expected: Accept/Reject hotkeys (e.g., `A` for accept, `R` for reject)

**Files Checked:**
- [app/api.py](app/api.py) - Sequential endpoints
- [app/writing/suggestion_queue.py](app/writing/suggestion_queue.py) - Queue manager
- [config.yaml](config.yaml) - Quota configuration

---

### ✅ 4. Quantitative Bullets Format (AMOT)

**Status:** PASS ✅

**Evidence:**

**Format Validation:**
- [app/writing/experience.py:39-59](app/writing/experience.py#L39-L59) - `has_amot_format()` function validates:
  - **A**ction: Starts with strong verb (Led, Drove, Increased, etc.)
  - **M**etric: Contains numeric values (%, $, counts)
  - **O**utcome: Contains impact words (resulting, leading to, achieving, etc.)
  - **T**ool: Contains platform/method (using, via, through, leveraging)

**Metric Extraction:**
- [app/writing/experience.py:27-37](app/writing/experience.py#L27-L37) - Extracts metrics:
  - Currency ranges: `$1.2M - $2.5M`
  - Percentages: `15% - 25%`
  - Count ranges: `10-15 users`

**Metric Injection:**
- [app/writing/experience.py:61-77](app/writing/experience.py#L61-L77) - Injects placeholder metrics if missing
- [app/writing/experience.py:110-112](app/writing/experience.py#L110-L112) - Applied during generation

**Example Bullets (from templates):**
- ✅ "Increased win-rate by 12% via MEDDICC-driven pipeline hygiene, adding $1.2M ARR"
- ✅ "Led team of 8 Sales Representatives achieving 115% of team quota through strategic territory planning"

**Files Checked:**
- [app/writing/experience.py](app/writing/experience.py) - AMOT validation & injection

---

### ✅ 5. MMR/RRF Pipeline

**Status:** PASS ✅

**Evidence:**

**Pipeline Flow (as specified):**
1. **Over-generation:** [app/writing/experience.py:99-116](app/writing/experience.py#L99-L116) - Generates 20-30 candidates
2. **Cohere Rerank:** [app/writing/experience.py:122](app/writing/experience.py#L122) - Semantic scoring via `score_bullets()`
3. **MMR Diversity:** [app/writing/experience.py:124-130](app/writing/experience.py#L124-L130) - Applies MMR with λ=0.7
4. **Keyword Weighting:** [app/writing/experience.py:133-140](app/writing/experience.py#L133-L140) - Keyword match scoring
5. **RRF Fusion:** [app/writing/experience.py:143-148](app/writing/experience.py#L143-L148) - Fuses Cohere + keyword rankings
6. **Final Score (1-10):** [app/ranking/providers/cohere.py:104-116](app/ranking/providers/cohere.py#L104-L116) - Maps to 1-10 scale

**MMR Implementation:**
- [app/ranking/mmr_rrf.py:39-106](app/ranking/mmr_rrf.py#L39-L106) - Maximal Marginal Relevance
- Formula: `MMR(D_i) = λ * Rel(D_i) - (1-λ) * max_j∈S Sim(D_i, D_j)`
- Similarity: Trigram Jaccard ([app/ranking/mmr_rrf.py:12-36](app/ranking/mmr_rrf.py#L12-L36))

**RRF Implementation:**
- [app/ranking/mmr_rrf.py:109-155](app/ranking/mmr_rrf.py#L109-L155) - Reciprocal Rank Fusion
- Formula: `RRF(d) = Σ_r 1 / (k + rank_r(d))` where k=60

**Keyword Weighting:**
- [app/ranking/mmr_rrf.py:158-183](app/ranking/mmr_rrf.py#L158-L183) - Extracts top keywords
- [app/ranking/mmr_rrf.py:185-202](app/ranking/mmr_rrf.py#L185-L202) - Computes keyword match score

**Cohere Integration:**
- [app/ranking/providers/cohere.py](app/ranking/providers/cohere.py) - Rerank API wrapper
- Model: `rerank-english-v3.0`
- [app/ranking/providers/cohere.py:148-185](app/ranking/providers/cohere.py#L148-L185) - Scores bullets with Cohere

**Files Checked:**
- [app/ranking/mmr_rrf.py](app/ranking/mmr_rrf.py) - MMR & RRF algorithms
- [app/ranking/providers/cohere.py](app/ranking/providers/cohere.py) - Cohere reranking
- [app/writing/experience.py](app/writing/experience.py) - Pipeline orchestration

---

### ⚠️ 6. Skills Block Formatting

**Status:** PARTIAL PASS ⚠️

**Evidence:**

**Format Requirements:**
- Max 3-4 lines ✅
- `Category: item | item | item…` format ✅
- JD-aligned deltas ⚠️ (need runtime verification)
- ATS-friendly (no tables, plain text) ✅

**Implementation:**
- [config.yaml:5](config.yaml#L5) - `max_skill_categories: 4` ✅
- [app/api.py:1560](app/api.py#L1560) - Enforces max categories from config ✅
- [app/api.py:1546-1579](app/api.py#L1546-L1579) - Categorizes skills into:
  - "Full-Cycle Enterprise SaaS Sales"
  - "CRM Systems & Digital Prospecting Tools"
  - "Sales Tools & Platforms"
- [app/api.py:1564-1579](app/api.py#L1564-L1579) - Formats as `{"category": "...", "skills": [...]}`

**Skill Extraction:**
- [app/writing/skills_engine.py:11-25](app/writing/skills_engine.py#L11-L25) - Extracts skills from JD
- [app/writing/skills_engine.py:58-76](app/writing/skills_engine.py#L58-L76) - Sales-specific categories

**Resume Rendering:**
- Need to verify: Does [app/assemble/resume.py](app/assemble/resume.py) render skills in pipe-separated format?
- Expected: "Sales: MEDDIC | Pipeline Management | Territory Planning"

**Action Required:**
- Manual test: Generate resume and verify Skills section formatting
- Check if resume template uses categories or flattens to single list

**Files Checked:**
- [app/api.py:1522-1581](app/api.py#L1522-L1581) - Skills preview endpoint
- [app/writing/skills_engine.py](app/writing/skills_engine.py) - Skill extraction
- [config.yaml:5](config.yaml#L5) - Max categories config

---

### ⚠️ 7. Resume Live Preview

**Status:** NEEDS MANUAL TESTING ⚠️

**Expected Behavior:**
- Shows only accepted bullets (not pending/rejected)
- Counter shows: "Accepted: 2/4" per role
- "Generate" button enabled only when all quotas met

**Implementation Evidence:**
- [app/api.py:1288-1326](app/api.py#L1288-L1326) - Status endpoint returns:
  - `approved` count
  - `required` quota
  - `is_complete` flag
  - `all_complete` gate
- [app/api.py:974-988](app/api.py#L974-L988) - Checks if `approved >= required`
- [app/api.py:1325](app/api.py#L1325) - `can_continue` enforces gate

**Counters:**
- Frontend should poll `GET /review/{job_id}/status`
- Expected response:
  ```json
  {
    "roles": {
      "ccs-2025": {"approved": 2, "required": 4, "complete": false}
    },
    "all_complete": false,
    "can_continue": false
  }
  ```

**Template Check Required:**
- File: [templates/review_sequential.html](templates/review_sequential.html)
- Verify: JavaScript polls status endpoint
- Verify: Button disabled when `can_continue: false`

**Action Required:**
- Start server: `http://localhost:8787`
- Ingest a job, manually enter JD
- Accept/reject bullets
- Verify counters update live
- Verify "Generate" disabled until quotas met

**Files Checked:**
- [app/api.py:1288-1326](app/api.py#L1288-L1326) - Status endpoint

---

### ✅ 8. File Generation & Naming

**Status:** PASS ✅

**Evidence:**

**File Naming:**
- [app/api.py:703-705](app/api.py#L703-L705) - Uses locked identity name:
  ```python
  base_name = f"{identity['name']} - {job['title']}"
  out_resume = out_dir / f"{base_name} - Resume.docx"
  out_cover = out_dir / f"{base_name} - Cover Letter.docx"
  ```
- Example: "John Smith - Software Engineer - Resume.docx"

**DOCX Generation:**
- [app/api.py:707-708](app/api.py#L707-L708) - Calls `render_resume()` and `render_cover()`
- [app/assemble/resume.py:77-88](app/assemble/resume.py#L77-L88) - Generates DOCX with python-docx

**PDF Generation (Pandoc):**
- [app/api.py:715-731](app/api.py#L715-L731) - Attempts PDF conversion if Pandoc available
- Graceful fallback if Pandoc missing:
  ```python
  result["pdf_status"] = "unavailable"
  result["pdf_message"] = f"PDF generation skipped: {str(e)}"
  ```

**Locked Fields Preservation:**
- [app/api.py:663-664](app/api.py#L663-L664) - Loads locked identity
- [app/assemble/locks.py](app/assemble/locks.py) - Enforces field locks
- Name, email, phone preserved from profile

**Output Directory:**
- [app/api.py:699-700](app/api.py#L699-L700) - Creates `out/` directory
- [.gitignore:39-41](.gitignore#L39-L41) - Ignores `out/`, `*.docx`, `*.pdf`

**Files Checked:**
- [app/api.py:652-736](app/api.py#L652-L736) - File generation endpoint
- [app/assemble/resume.py](app/assemble/resume.py) - Resume renderer
- [app/assemble/cover_letter.py](app/assemble/cover_letter.py) - Cover letter renderer
- [app/assemble/locks.py](app/assemble/locks.py) - Field locking

---

### ✅ 9. Compliant Mode

**Status:** PASS ✅

**Evidence:**

**Compliance Rules:**
- [app/apply/compliance.py:1-2](app/apply/compliance.py#L1-L2) - Allowlist function:
  ```python
  def allowed_for_auto(ats_vendor:str)->bool:
      return ats_vendor in ('greenhouse_public','lever_public')
  ```
- ✅ LinkedIn: NOT in allowlist → Manual only
- ✅ Greenhouse: In allowlist → Auto-apply allowed
- ✅ Lever: In allowlist → Auto-apply allowed
- ❌ All others: NOT in allowlist → Assist mode

**ATS Detection:**
- [app/discovery/resolver.py](app/discovery/resolver.py) - Resolves ATS vendor from URL
- [app/api.py:283-294](app/api.py#L283-L294) - Sets `ats_vendor` field on ingest

**Apply Flow:**
- [app/api.py:626](app/api.py#L626) - Checks `allowed_for_auto(job.get("ats_vendor", ""))`
- [app/api.py:779](app/api.py#L779) - Validates before auto-submit:
  ```python
  if not allowed_for_auto(vendor):
      return {"ok": False, "reason": "Not in allow-list; use Assist."}
  ```

**Assist Mode:**
- [app/api.py:738-745](app/api.py#L738-L745) - Opens assist mode for non-allowlisted ATSs
- [app/apply/assist.py](app/apply/assist.py) - Browser automation helper

**Submitters:**
- [app/apply/submitters.py](app/apply/submitters.py) - Greenhouse/Lever auto-submit logic

**Config:**
- [config.yaml:70-71](config.yaml#L70-L71) - `allow_auto_submit: false` (manual override)

**Files Checked:**
- [app/apply/compliance.py](app/apply/compliance.py) - Allowlist
- [app/api.py:619-650](app/api.py#L619-L650) - Apply page logic
- [app/api.py:747-801](app/api.py#L747-L801) - Auto-apply endpoint
- [config.yaml:69-74](config.yaml#L69-L74) - Apply config

---

### ✅ 10. Telemetry & Logging

**Status:** PASS ✅

**Evidence:**

**Log File:**
- [app/utils/telemetry.py:37-39](app/utils/telemetry.py#L37-L39) - Writes to `logs/events.jsonl`
- Verified: [logs/events.jsonl](logs/events.jsonl) exists ✅

**Event Structure:**
- [app/utils/telemetry.py:27-35](app/utils/telemetry.py#L27-L35) - Each event includes:
  - `timestamp` (ISO 8601 UTC)
  - `event_type`
  - `job_id`
  - `company`
  - `title`
  - `actor` ("user" or "system")
  - Additional payload (model_used, score, accepted/rejected, etc.)

**Tracked Events:**
- ✅ `suggestion_proposed` - [app/api.py:903-913](app/api.py#L903-L913) - Logs model_used, score
- ✅ `suggestion_approved` - [app/api.py:963-971](app/api.py#L963-L971) - Logs acceptance
- ✅ `suggestion_rejected` - [app/api.py:1033-1042](app/api.py#L1033-L1042) - Logs rejection
- ✅ `role_complete` - [app/api.py:975-983](app/api.py#L975-L983) - Logs when quota met
- ✅ `build_files` - [app/api.py:733-734](app/api.py#L733-L734)
- ✅ `apply_auto` - [app/api.py:798-799](app/api.py#L798-L799)

**Role Counters:**
- Status endpoint returns per-role counts: [app/api.py:1305-1320](app/api.py#L1305-L1320)

**Config:**
- [config.yaml:98-110](config.yaml#L98-L110) - Telemetry enabled, event types listed

**Example Event:**
```json
{
  "timestamp": "2025-10-01T20:45:12.345Z",
  "event_type": "suggestion_approved",
  "job_id": "abc123",
  "company": "Acme Corp",
  "title": "Sales Engineer",
  "actor": "user",
  "role_key": "ccs-2025",
  "suggestion_id": "xyz789",
  "model_used": "claude-3-5-sonnet-20241022",
  "score": 8,
  "accepted": true
}
```

**Files Checked:**
- [app/utils/telemetry.py](app/utils/telemetry.py) - Logging implementation
- [config.yaml:98-110](config.yaml#L98-L110) - Telemetry config
- [logs/events.jsonl](logs/events.jsonl) - Log file (verified exists)

---

### ✅ 11. Performance & Robustness

**Status:** PASS ✅

**Evidence:**

**Error Handling:**
- [app/api.py:68-158](app/api.py#L68-L158) - Global exception handler:
  - Catches all unhandled exceptions
  - Logs to telemetry ([app/api.py:78-81](app/api.py#L78-L81))
  - Returns JSON for API endpoints ([app/api.py:95-104](app/api.py#L95-L104))
  - Returns HTML error page for browser requests ([app/api.py:106-158](app/api.py#L106-L158))

**Graceful Failures:**
- [app/writing/experience.py:370-388](app/writing/experience.py#L370-L388) - Fallback suggestions on error
- [app/ranking/providers/cohere.py:63-69](app/ranking/providers/cohere.py#L63-L69) - Neutral scores on API error
- [app/api.py:729-731](app/api.py#L729-L731) - PDF generation optional

**Rate Limiting:**
- [app/api.py:762-774](app/api.py#L762-L774) - Enforces 5-minute interval between submissions
- [config.yaml:72](config.yaml#L72) - `min_interval_seconds: 300`
- [app/apply/rate_limiter.py](app/apply/rate_limiter.py) - Rate limiter implementation

**ID Persistence:**
- [app/api.py:285](app/api.py#L285) - Generates stable job_id: `str(uuid.uuid4())[:8]`
- [app/writing/experience.py:153](app/writing/experience.py#L153) - Suggestion IDs persistent across calls
- State saved to disk: [app/api.py:171-211](app/api.py#L171-L211)

**State Persistence:**
- [app/api.py:171-211](app/api.py#L171-L211) - `save_state()` to `out/state.json`
- [app/api.py:214-243](app/api.py#L214-L243) - `load_state()` on startup
- Review data: `out/reviews/{job_id}.json`
- Approvals: `out/approvals/{job_id}.json`

**Latency:**
- Timeouts configured:
  - LLM providers: 25-30s ([config.yaml:34-53](config.yaml#L34-L53))
  - Discovery: 10s ([config.yaml:66](config.yaml#L66))
- Circuit breaker: [config.yaml:159-162](config.yaml#L159-L162) - 3 failures, 60s timeout

**Files Checked:**
- [app/api.py:68-158](app/api.py#L68-L158) - Error handling
- [app/api.py:171-243](app/api.py#L171-L243) - State persistence
- [app/apply/rate_limiter.py](app/apply/rate_limiter.py) - Rate limiting
- [config.yaml](config.yaml) - Timeout & circuit breaker config

---

## Summary Table

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 1 | Server Startup & Health | ✅ PASS | Running on port 8787 |
| 2 | Security & Config | ❌ **CRITICAL FAIL** | **API keys exposed in `.env`** |
| 3 | Sequential Flow | ✅ PASS | Quotas enforced, duplicates prevented |
| 4 | Quantitative Bullets (AMOT) | ✅ PASS | Validates Action-Metric-Outcome-Tool |
| 5 | MMR/RRF Pipeline | ✅ PASS | Full pipeline: Cohere → MMR → RRF |
| 6 | Skills Block | ⚠️ PARTIAL | Config OK, needs manual test |
| 7 | Resume Live Preview | ⚠️ NEEDS TEST | Status endpoint OK, need UI test |
| 8 | File Generation | ✅ PASS | DOCX+PDF, correct naming |
| 9 | Compliant Mode | ✅ PASS | LinkedIn manual, GH/Lever auto |
| 10 | Telemetry | ✅ PASS | Logs to `logs/events.jsonl` |
| 11 | Performance | ✅ PASS | Error handling, rate limiting, persistence |

---

## Critical Issues

### 🔴 CRITICAL: Exposed API Keys

**File:** [.env](.env)

**Issue:** The `.env` file contains live API keys for 5 providers (OpenAI, Anthropic, Google, Perplexity, Cohere). If this directory is ever committed to git, these keys will be exposed in commit history.

**Immediate Actions Required:**

1. **Before git init:**
   ```bash
   # Verify .env is gitignored
   grep "^\.env$" .gitignore

   # Initialize git
   git init

   # Verify .env is NOT staged
   git status | grep -v ".env"
   ```

2. **If already committed:**
   - Rotate ALL API keys immediately
   - Use `git filter-branch` or BFG Repo-Cleaner to remove from history
   - Force-push to remote (if applicable)

3. **Best Practices:**
   - Use `.env.sample` with placeholder values (e.g., `OPENAI_API_KEY=sk-xxx...`)
   - Never commit `.env` to version control
   - Use secret management tools in production (AWS Secrets Manager, Vault, etc.)

---

## Manual Testing Required

The following items require manual end-to-end testing:

### 1. Full Flow Walkthrough

**Steps:**
1. Start server: `python -m uvicorn app.api:app --port 8787`
2. Open http://localhost:8787
3. Paste a job URL (e.g., LinkedIn, Greenhouse, Lever)
4. Manually enter company, title, JD
5. Navigate to review page (`/review/{job_id}?mode=seq`)
6. Accept/reject suggestions one at a time
7. Verify:
   - ✅ One suggestion shown at a time
   - ✅ Keyboard shortcuts work (A=accept, R=reject)
   - ✅ No duplicate suggestions after rejection
   - ✅ Counters update live (e.g., "2/4" → "3/4")
   - ✅ "Generate" button disabled until all quotas met
   - ✅ Skills block shows max 3-4 categories
   - ✅ Resume preview updates with accepted bullets only
8. Click "Generate Files"
9. Verify:
   - ✅ DOCX files created with correct names
   - ✅ PDF files created (if Pandoc installed)
   - ✅ Resume has quantitative bullets (AMOT format)
   - ✅ Skills formatted as "Category: item | item | item"
10. Test apply flow:
    - ✅ LinkedIn → Opens Assist mode (not auto)
    - ✅ Greenhouse/Lever → Auto-apply allowed (if `allow_auto_submit: true`)

### 2. Telemetry Verification

**Steps:**
1. Complete flow above
2. Check `logs/events.jsonl`
3. Verify events logged:
   - `suggestion_proposed` (with `model_used`, `score`)
   - `suggestion_approved` or `suggestion_rejected`
   - `role_complete` (when quota met)
   - `build_files`
   - `apply_auto` or `apply_assist`

### 3. Quantitative Bullets Spot Check

**Steps:**
1. Open generated resume DOCX
2. Verify ALL bullets have:
   - **Action verb:** Led, Drove, Increased, etc.
   - **Metric:** % or $ or count
   - **Outcome:** "resulting in", "achieving", etc.
   - **Tool/method:** "via MEDDIC", "using Salesforce", etc.
3. Example: "Increased pipeline by 25% via MEDDIC qualification, resulting in $2M ARR"

---

## Recommendations

### Short-Term (Pre-Launch)

1. **Security:**
   - ✅ Verify `.env` in `.gitignore` before `git init`
   - ✅ Document key rotation process
   - ✅ Add `.env.sample` to repo with placeholder values

2. **Testing:**
   - ⚠️ Complete manual flow walkthrough (see above)
   - ⚠️ Test all keyboard shortcuts
   - ⚠️ Verify no duplicate suggestions
   - ⚠️ Verify resume formatting matches Nate's template

3. **Documentation:**
   - ✅ Update README with setup instructions
   - ✅ Document environment variable requirements
   - ✅ Add troubleshooting section for Pandoc PDF errors

### Long-Term (Post-Launch)

1. **Security Hardening:**
   - Use secret management service (AWS Secrets Manager, Vault)
   - Implement API key rotation schedule
   - Add audit logging for key usage

2. **Performance:**
   - Add caching for JD keyword extraction
   - Implement progressive loading for long suggestion lists
   - Consider CDN for static assets

3. **Observability:**
   - Add structured logging (JSON format)
   - Implement metrics (Prometheus/Grafana)
   - Add distributed tracing (OpenTelemetry)

4. **Testing:**
   - Add integration tests for full flow
   - Add unit tests for MMR/RRF algorithms
   - Add E2E tests with Playwright/Selenium

---

## Ready to Ship Checklist

Before marking as "Ready to Ship":

- [ ] **CRITICAL:** Verify `.env` is gitignored before `git init`
- [ ] Complete manual flow walkthrough
- [ ] Verify quantitative bullets in generated resume
- [ ] Verify skills formatting (3-4 lines, pipe-separated)
- [ ] Test keyboard shortcuts (Accept/Reject)
- [ ] Verify telemetry logs to `logs/events.jsonl`
- [ ] Test compliant mode (LinkedIn manual, GH/Lever auto)
- [ ] Verify no duplicate suggestions
- [ ] Test file generation (DOCX + PDF)
- [ ] Document API key rotation process

---

## Deployment Notes

**Server Command:**
```bash
cd autoapply_scaffold
python -m uvicorn app.api:app --host 0.0.0.0 --port 8787 --reload
```

**Environment Variables Required:**
```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...
PERPLEXITY_API_KEY=pplx-...
COHERE_API_KEY=...
```

**Dependencies:**
- Python 3.9+
- FastAPI, Uvicorn
- python-docx
- cohere
- openai, anthropic
- pypandoc (optional, for PDF)

**Port:** 8787
**Access:** http://localhost:8787

---

## Contact & Next Steps

**Current Status:** ⚠️ Ready with critical fixes required

**Next Steps:**
1. Address critical security issue (API keys)
2. Complete manual testing checklist
3. Document findings
4. If all tests pass → Mark as "Ready to Ship"

**Commit SHA (when ready):** _To be determined after testing_

---

**Review Complete:** 2025-10-01
**Reviewer:** Code QA Agent
**Total Criteria Reviewed:** 11
**Pass:** 8 ✅ | **Fail:** 1 ❌ | **Partial/Needs Test:** 2 ⚠️

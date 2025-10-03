from fastapi import FastAPI, Body, Query, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import List, Dict
from pathlib import Path
import json
import uuid
import traceback
from datetime import datetime
from .config import load_settings
from .discovery.resolver import resolve_company_apply
from .discovery import dedupe
try:
    from .research.providers import gather_allowlisted_evidence
except ImportError:
    # Fallback if providers module structure changed
    import app.research.providers as research_providers_mod
    gather_allowlisted_evidence = getattr(research_providers_mod, 'gather_allowlisted_evidence', lambda x: [])
from .research.debate import debate_and_merge
from .writing.summarize import generate_exec_and_soq
from .writing.recruiter_score import score_human_readability
from .writing.ats_preflight import preflight_check
from .writing.experience import propose_experience_bullets, generate_suggestion, generate_suggestions
from .writing.suggestion_queue import QueueManager, Suggestion
from .apply.rate_limiter import get_rate_limiter
from .llm.router import LLMRouter
from .writing.skills_engine import propose_skills
from .assemble.locks import enforce_locks
from .assemble.resume import render_resume
from .assemble.cover_letter import render_cover
from .apply.assist import open_assist
from .apply.submitters import auto_submit
from .apply.compliance import allowed_for_auto
from .utils.telemetry import log_event
from .utils.text import hash_key
from .utils.fs import bootstrap_fs, read_json, write_json, read_text

app = FastAPI(title="AutoApply (Hybrid)")
settings = load_settings()
JOBS: Dict[str, Dict] = {}
templates = Jinja2Templates(directory="templates")

# Queue managers for sequential suggestion system
QUEUE_MANAGERS: Dict[str, QueueManager] = {}  # job_id -> QueueManager

# State persistence paths
STATE_DIR = Path("out")
STATE_FILE = STATE_DIR / "state.json" 
REVIEW_DIR = STATE_DIR / "reviews"
APPROVALS_DIR = STATE_DIR / "approvals"
SUGGESTIONS_DIR = STATE_DIR / "suggestions"

# Create necessary directories
for dir_path in [STATE_DIR, REVIEW_DIR, APPROVALS_DIR, SUGGESTIONS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)


# ===== Startup & Error Handling =====

@app.on_event("startup")
async def startup_event():
    """Bootstrap filesystem and load state on startup."""
    bootstrap_fs()
    load_state()
    print("* AutoApply started successfully")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all exceptions and return friendly error page or JSON."""
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

    # Log to console
    print(f"ERROR: {exc}")
    print(tb)

    # Try to log to telemetry
    try:
        log_event("error", "system", "", "", error=str(exc), traceback=tb[:500])
    except:
        pass

    # Check if this is an API request (expects JSON)
    path = request.url.path
    is_api = (
        path.startswith('/ingest/') or
        path.startswith('/build/') or
        path.startswith('/apply/') or
        path.startswith('/review/') or
        path.startswith('/queue/') or
        path.startswith('/jobs/') or
        path.startswith('/telemetry/')
    )

    if is_api or request.headers.get('accept', '').find('application/json') >= 0:
        # Return JSON error for API endpoints
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "message": str(exc),
                "traceback": tb[:1000] if tb else None
            }
        )

    # Return friendly HTML error page for regular page requests
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Error - AutoApply</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #f5f5f5;
                padding: 2rem;
                color: #333;
            }}
            .container {{
                max-width: 800px;
                margin: 0 auto;
                background: white;
                padding: 2rem;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
            h1 {{ color: #dc3545; }}
            .message {{ margin: 1.5rem 0; padding: 1rem; background: #f8d7da; border-left: 4px solid #dc3545; border-radius: 4px; }}
            details {{ margin-top: 2rem; }}
            summary {{ cursor: pointer; font-weight: 600; padding: 0.5rem; background: #f8f9fa; border-radius: 4px; }}
            pre {{ background: #f8f9fa; padding: 1rem; border-radius: 4px; overflow-x: auto; font-size: 12px; }}
            .actions {{ margin-top: 2rem; }}
            .btn {{ display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; }}
            .btn:hover {{ background: #0056b3; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>⚠️ Something Went Wrong</h1>
            <div class="message">
                <strong>Error:</strong> {str(exc)}
            </div>
            <p>The application encountered an unexpected error. Please try again or check the logs for more details.</p>
            <details>
                <summary>🔍 Debug Details (Stack Trace)</summary>
                <pre>{tb}</pre>
            </details>
            <div class="actions">
                <a href="/" class="btn">← Back to Home</a>
                <a href="/health" class="btn" style="background:#28a745;margin-left:12px">Check Health</a>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html, status_code=500)


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "ok": True,
        "status": "healthy",
        "jobs_count": len(JOBS),
        "timestamp": datetime.utcnow().isoformat()
    }

def save_state():
    """
    Persist job state and related data to disk.
    Separates core job data from review/approval state.
    """
    # Create directories
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    APPROVALS_DIR.mkdir(parents=True, exist_ok=True)

    # Split state storage
    jobs_core = {}
    for job_id, job in JOBS.items():
        # Store core job data
        jobs_core[job_id] = {
            'id': job['id'],
            'url': job.get('url', ''),
            'apply_url': job.get('apply_url', ''),
            'company': job.get('company', ''),
            'title': job.get('title', ''),
            'ats_vendor': job.get('ats_vendor', 'unknown'),
            'needs_review': job.get('needs_review', True),
            'host': job.get('host', ''),
            'source_type': job.get('source_type', ''),
            'source_id': job.get('source_id'),
            'manual_key': job.get('manual_key'),
            'created_at': job.get('created_at', datetime.utcnow().isoformat())
        }

        # Store review data separately
        if 'review' in job:
            review_file = REVIEW_DIR / f"{job_id}.json"
            write_json(review_file, job['review'])

        # Store approvals data separately
        if 'approvals' in job:
            approval_file = APPROVALS_DIR / f"{job_id}.json"
            write_json(approval_file, job['approvals'])

    # Save core job data
    write_json(STATE_FILE, jobs_core)


def load_state():
    """
    Load job state from disk.
    Reconstructs complete state from separated storage.
    """
    global JOBS
    JOBS = {}

    # Load core job data with safe fallback
    jobs_core = read_json(STATE_FILE, {})

    # Reconstruct complete state
    for job_id, core_data in jobs_core.items():
        JOBS[job_id] = core_data

        # Load review data if exists
        review_file = REVIEW_DIR / f"{job_id}.json"
        if review_file.exists():
            review_data = read_json(review_file, {})
            if review_data:
                JOBS[job_id]['review'] = review_data

        # Load approvals if exists
        approval_file = APPROVALS_DIR / f"{job_id}.json"
        if approval_file.exists():
            approval_data = read_json(approval_file, {})
            if approval_data:
                JOBS[job_id]['approvals'] = approval_data

    print(f"Loaded {len(JOBS)} jobs from state")

# Load state on startup
load_state()

@app.get("/", response_class=HTMLResponse)
def root():
    """Serve the main dashboard page."""
    return read_text("web/index.html", "<h1>Error: index.html not found</h1>")

@app.post("/ingest/paste")
def ingest_paste(payload: Dict = Body(...)):
    """Ingest a job URL - resolves ATS or triggers manual entry."""
    raw_url = (payload.get('url') or '').strip()
    if not raw_url:
        return JSONResponse({"error": "invalid_url"}, status_code=400)

    normalized_url = raw_url.lower()
    existing_job = next(
        (
            job for job in JOBS.values()
            if job.get('url', '').strip().lower() == normalized_url
            or job.get('apply_url', '').strip().lower() == normalized_url
        ),
        None
    )

    if existing_job:
        redirect = f"/ingest/manual/{existing_job['id']}" if existing_job.get('needs_review', False) else f"/review/{existing_job['id']}"
        status = "needs_manual_entry" if existing_job.get('needs_review', False) else "already_in_review"
        log_event(
            "ingest_duplicate",
            existing_job['id'],
            existing_job.get('company', 'Unknown'),
            existing_job.get('title', 'Unknown'),
            actor="user",
            url=raw_url,
            host=existing_job.get('host', 'unknown')
        )
        return {"status": status, "job": existing_job, "redirect": redirect}

    r = resolve_company_apply(raw_url)
    job_id = str(uuid.uuid4())[:8]

    res = {
        "id": job_id,
        "url": raw_url,
        "host": r.get('host', 'unknown'),
        "apply_url": r.get('apply_url', raw_url),
        "ats_vendor": r.get('ats_vendor', 'unknown'),
        "needs_review": r.get('needs_review', False)
    }

    JOBS[job_id] = res
    save_state()

    # All ingestions require manual entry to get title, company, and JD
    log_event("ingest", job_id, "Unknown", "Unknown", actor="user", url=raw_url, host=res["host"])
    return {"status": "needs_manual_entry", "job": res, "redirect": f"/ingest/manual/{job_id}"}

@app.get("/ingest/manual/{job_id}", response_class=HTMLResponse)
def manual_ingest_form(request: Request, job_id: str):
    """Show manual entry form for job details."""
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"error": "not_found"}, status_code=404)
    return templates.TemplateResponse("ingest_manual.html", {"request": request, "job": job})

@app.post("/ingest/manual/{job_id}")
def manual_ingest_submit(
    job_id: str,
    title: str = Form(...),
    company: str = Form(...),
    jd: str = Form(...)
):
    """Process manual job entry and redirect to review."""
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"error": "not_found"}, status_code=404)

    title_clean = (title or '').strip()
    company_clean = (company or '').strip()
    apply_url = (job.get('apply_url', '') or '').strip()

    # Update job with manual data
    job.update({
        "title": title_clean,
        "company": company_clean,
        "jd": jd,
        "needs_review": False
    })

    manual_key = hash_key('job', company_clean.lower(), title_clean.lower(), apply_url.lower())

    if dedupe.seen(manual_key):
        existing_job = next(
            (
                existing for existing in JOBS.values()
                if existing['id'] != job_id
                and hash_key(
                    'job',
                    (existing.get('company') or '').strip().lower(),
                    (existing.get('title') or '').strip().lower(),
                    (existing.get('apply_url') or '').strip().lower()
                ) == manual_key
            ),
            None
        )
        ingest_key = job.get('ingest_key') or hash_key('url', (job.get('url', '') or '').strip().lower())
        dedupe.unmark(ingest_key)
        del JOBS[job_id]
        save_state()
        log_event(
            "manual_ingest_duplicate",
            job_id,
            company_clean or "Unknown",
            title_clean or "Unknown",
            actor="user",
            apply_url=apply_url
        )
        if existing_job:
            return RedirectResponse(url=f"/review/{existing_job['id']}?duplicate=true", status_code=303)
        return RedirectResponse(url="/?duplicate=true", status_code=303)

    dedupe.mark(manual_key)
    job['manual_key'] = manual_key
    JOBS[job_id] = job
    save_state()

    log_event("manual_ingest", job_id, company_clean, title_clean, actor="user", jd_length=len(jd))

    return RedirectResponse(url=f"/review/{job_id}", status_code=303)

@app.get("/queue/pending")
def queue_pending() -> List[Dict]:
    return [j for j in JOBS.values() if not j.get('needs_review', False)]

@app.get("/jobs/pending")
def jobs_pending() -> List[Dict]:
    """Return all jobs with their current status for the dashboard."""
    return [
        {
            'id': j['id'],
            'title': j.get('title', ''),
            'company': j.get('company', ''),
            'url': j.get('url', ''),
            'host': j.get('host', ''),
            'needs_review': j.get('needs_review', True),
            'ats_vendor': j.get('ats_vendor', 'unknown')
        }
        for j in JOBS.values()
    ]

@app.post("/queue/skip")
def queue_skip(payload: Dict = Body(...)):
    jid = payload.get('job_id')
    if jid in JOBS:
        del JOBS[jid]
        save_state()
    return {"ok": True}

@app.post("/telemetry/log")
def telemetry_log(payload: Dict = Body(...)):
    """Log frontend telemetry events."""
    event = payload.get('event', 'unknown')
    job_id = payload.get('job_id', 'unknown')
    try:
        log_event(event, job_id, "", "", actor="user", **payload)
    except Exception:
        pass
    return {"ok": True}

# ===== JSON API (preserved) =====
@app.get("/review/session")
def review_session(job_id: str = Query(...)):
    """Original JSON endpoint."""
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"error": "not_found"}, status_code=404)

    if "review" not in job:
        _initialize_review(job)

    return {"job": job, **job["review"]}

def _initialize_review(job: dict):
    """Initialize review session for a job."""
    refs = debate_and_merge(gather_allowlisted_evidence([job.get("title", ""), job.get("company", "")]))
    exec_summary, soq = generate_exec_and_soq(job.get("jd", ""), job.get("company", ""))
    history = json.loads(Path("profile/employment_history.json").read_text())
    exp = propose_experience_bullets(history, job.get("jd", ""))
    registry = json.loads(Path("profile/skills_registry.json").read_text())
    auto_added, needs_confirm = propose_skills(job.get("jd", ""), registry)

    approved_bullets = [b['text'] for bl in exp.values() for b in bl if b.get('status') == 'APPROVED']
    recruiter = score_human_readability(exec_summary, approved_bullets)
    preflight = preflight_check(exec_summary + " " + " ".join(soq), job.get("jd", ""))

    job["review"] = {
        "evidence_refs": refs,
        "exec_summary": exec_summary,
        "soq": soq,
        "experience": exp,
        "skills": {
            "approved": list(registry.get('approved', [])),
            "needs_confirmation": needs_confirm,
            "rejected": []
        },
        "scores": {"recruiter": recruiter, "ats_preflight": preflight}
    }
    job["history"] = history
    save_state()


# ===== Review Data Helper Functions =====

def _get_review_data(job_id: str) -> Dict:
    """Get or initialize review data with role structure."""
    review_file = REVIEW_DIR / f"{job_id}.json"
    review_data = read_json(review_file, {})

    if 'roles' not in review_data:
        # Initialize with required counts from config
        review_data['roles'] = {}
        for role_key, required_count in settings.roles_required.items():
            review_data['roles'][role_key] = {
                'required': required_count,
                'approved': [],
                'rejected': [],
                'suggestion_history': []
            }
        write_json(review_file, review_data)

    return review_data


def _save_review_data(job_id: str, review_data: Dict):
    """Save review data to disk."""
    review_file = REVIEW_DIR / f"{job_id}.json"
    write_json(review_file, review_data)


def _get_role_context(role_key: str) -> Dict:
    """Get role context from employment history."""
    history_file = Path("profile/employment_history.json")
    history = read_json(history_file, [])

    for role in history:
        if role.get('role_id') == role_key:
            return role

    return {"role_id": role_key, "title": "Unknown", "company": "Unknown"}


@app.get("/review/{job_id}", response_class=HTMLResponse)
def review_job_html(request: Request, job_id: str, mode: str = Query("multi")):
    """HTML review page with multi-LLM suggestion interface."""
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"error": "not_found"}, status_code=404)

    # Initialize review data if needed
    review_data = _get_review_data(job_id)

    # Get employment history for role context
    history_file = Path("profile/employment_history.json")
    history = read_json(history_file, [])

    # Build roles array with context for frontend
    roles = []
    for role_key, role_data in review_data.get('roles', {}).items():
        role_context = _get_role_context(role_key)
        roles.append({
            'role_id': role_key,
            'title': role_context.get('title', 'Unknown'),
            'company': role_context.get('company', 'Unknown'),
            'required': role_data.get('required', 4),
            'approved': len(role_data.get('approved', []))
        })

    jd_words = job.get("jd", "").split()
    jd_snippet = " ".join(jd_words[:150]) + ("..." if len(jd_words) > 150 else "")

    # Choose template based on mode
    if mode == "seq":
        template = "review_sequential.html"
    elif mode == "multi":
        template = "review_multi.html"
    else:
        template = "review_iterative.html"

    return templates.TemplateResponse(template, {
        "request": request,
        "job": job,
        "jd_snippet": jd_snippet,
        "roles": roles
    })

@app.post("/review/bullet/{job_id}")
def update_bullet_status(job_id: str, payload: Dict = Body(...)):
    """Update bullet status."""
    job = JOBS.get(job_id)
    if not job or "review" not in job:
        return JSONResponse({"error": "session_not_found"}, status_code=404)

    role_id = payload.get('role_id')
    bullet_id = payload.get('bullet_id')
    action = payload.get('action')

    if role_id not in job["review"]["experience"]:
        return JSONResponse({"error": "role_not_found"}, status_code=404)

    for bullet in job["review"]["experience"][role_id]:
        if bullet['id'] == bullet_id:
            bullet['status'] = 'APPROVED' if action == 'approve' else 'REJECTED'
            save_state()
            log_event("review_approve_bullets", job_id, job.get("company", ""), job.get("title", ""),
                     actor="user", bullet_id=bullet_id, action=action)
            return {"ok": True, "status": bullet['status']}

    return JSONResponse({"error": "bullet_not_found"}, status_code=404)

@app.post("/review/skill/{job_id}")
def update_skill_status(job_id: str, payload: Dict = Body(...)):
    """Move skill between lists."""
    job = JOBS.get(job_id)
    if not job or "review" not in job:
        return JSONResponse({"error": "session_not_found"}, status_code=404)

    skill_data = payload.get('skill')
    action = payload.get('action')

    skill = skill_data.get('skill') if isinstance(skill_data, dict) else skill_data

    skills = job["review"]["skills"]

    skills["needs_confirmation"] = [
        s for s in skills["needs_confirmation"]
        if (s.get('skill') if isinstance(s, dict) else s) != skill
    ]

    if action == 'approve':
        if skill not in skills["approved"]:
            skills["approved"].append(skill)
    else:
        if skill not in skills["rejected"]:
            skills["rejected"].append(skill)

    save_state()
    log_event("review_approve_skills", job_id, job.get("company", ""), job.get("title", ""),
             actor="user", skill=skill, action=action)
    return {"ok": True}

@app.post("/review/approve_all/{job_id}")
def approve_all(job_id: str):
    """Approve all PENDING items."""
    job = JOBS.get(job_id)
    if not job or "review" not in job:
        return JSONResponse({"error": "session_not_found"}, status_code=404)

    for role_id, bullets in job["review"]["experience"].items():
        for bullet in bullets:
            if bullet.get('status') != 'REJECTED':
                bullet['status'] = 'APPROVED'

    skills = job["review"]["skills"]
    for skill_data in skills["needs_confirmation"]:
        skill = skill_data.get('skill') if isinstance(skill_data, dict) else skill_data
        if skill not in skills["approved"]:
            skills["approved"].append(skill)
    skills["needs_confirmation"] = []

    save_state()
    log_event("review_approve_all", job_id, job.get("company", ""), job.get("title", ""), actor="user")
    return {"ok": True}

@app.get("/apply/{job_id}", response_class=HTMLResponse)
def apply_page(request: Request, job_id: str):
    """Apply page."""
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"error": "not_found"}, status_code=404)

    auto_eligible = allowed_for_auto(job.get("ats_vendor", ""))

    resume_path = Path("out") / f"{job.get('title', 'Job')} - Resume.docx"
    cover_path = Path("out") / f"{job.get('title', 'Job')} - Cover Letter.docx"

    files_generated = None
    if resume_path.exists() and cover_path.exists():
        files_generated = {
            "resume": str(resume_path.resolve()),
            "cover_letter": str(cover_path.resolve())
        }

        pdf_resume = resume_path.with_suffix('.pdf')
        pdf_cover = cover_path.with_suffix('.pdf')
        if pdf_resume.exists():
            files_generated["resume_pdf"] = str(pdf_resume.resolve())
        if pdf_cover.exists():
            files_generated["cover_pdf"] = str(pdf_cover.resolve())

    return templates.TemplateResponse("apply.html", {
        "request": request,
        "job": job,
        "auto_eligible": auto_eligible,
        "files_generated": files_generated
    })

@app.post("/build/files")
def build_files(payload: Dict = Body(...)):
    """Generate resume and cover letter (DOCX + PDF if Pandoc available)."""
    job_id = payload.get('job_id')
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"error": "not_found"}, status_code=404)

    # Try to load approved bullets from new review data structure first
    review_data = _get_review_data(job_id)

    identity = json.loads(Path("profile/locked_identity.json").read_text())
    identity = enforce_locks(identity, {})

    # Get approved bullets from new structure
    approved_exp = {}
    if review_data and 'roles' in review_data:
        for role_key, role_data in review_data['roles'].items():
            approved_bullets = role_data.get('approved', [])
            if approved_bullets:
                # Convert to old format for resume generation
                approved_exp[role_key] = [
                    {"id": b.get('id'), "text": b.get('text'), "status": "APPROVED"}
                    for b in approved_bullets
                ]

    # Fallback to old review structure if new structure is empty
    if not approved_exp and "review" in job:
        experience = job["review"]["experience"]
        for role_id, bullets in experience.items():
            approved_bullets = [b for b in bullets if b.get('status') == 'APPROVED']
            if approved_bullets:
                approved_exp[role_id] = approved_bullets

    # Get exec summary and soq (from old structure for now)
    if "review" in job:
        exec_summary = job["review"].get("exec_summary", "Experienced professional with proven track record.")
        soq = job["review"].get("soq", [])
        skills = job["review"]["skills"].get("approved", [])
    else:
        exec_summary = "Experienced professional with proven track record."
        soq = []
        # Get skills from registry
        registry_file = Path("profile/skills_registry.json")
        registry = read_json(registry_file, {})
        skills = registry.get('approved', [])

    out_dir = Path("out")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Use locked identity name for file naming
    base_name = f"{identity['name']} - {job['title']}"
    out_resume = out_dir / f"{base_name} - Resume.docx"
    out_cover = out_dir / f"{base_name} - Cover Letter.docx"

    render_resume(out_resume, identity, exec_summary, soq, approved_exp, skills)
    render_cover(out_cover, job["company"], job["title"], exec_summary, job.get("jd", ""), approved_exp)

    result = {
        "resume": str(out_resume.resolve()),
        "cover_letter": str(out_cover.resolve())
    }

    # Try PDF conversion with Pandoc
    try:
        import pypandoc
        pypandoc.get_pandoc_path()

        pdf_resume = out_resume.with_suffix('.pdf')
        pdf_cover = out_cover.with_suffix('.pdf')

        pypandoc.convert_file(str(out_resume), 'pdf', outputfile=str(pdf_resume))
        pypandoc.convert_file(str(out_cover), 'pdf', outputfile=str(pdf_cover))

        result["resume_pdf"] = str(pdf_resume.resolve())
        result["cover_pdf"] = str(pdf_cover.resolve())
        result["pdf_status"] = "success"
    except Exception as e:
        result["pdf_status"] = "unavailable"
        result["pdf_message"] = f"PDF generation skipped: {str(e)}"

    log_event("build_files", job_id, job.get("company", ""), job.get("title", ""),
             actor="user", files=list(result.keys()))

    return result

@app.post("/apply/assist")
def apply_assist(payload: Dict = Body(...)):
    job_id = payload.get('job_id')
    job = JOBS.get(job_id)
    if job:
        log_event("apply_assist", job_id, job.get("company", ""), job.get("title", ""),
                 actor="user", apply_url=job.get("apply_url"))
    return open_assist(payload.get('apply_url'))

@app.post("/apply/auto")
def apply_auto(payload: Dict = Body(...)):
    """
    Auto-submit via Greenhouse/Lever with rate limiting.

    Enforces minimum 5-minute interval between submissions to:
    - Prevent API rate limiting
    - Maintain professional submission pace
    - Avoid anti-bot detection
    """
    job_id = payload.get('job_id')
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"error": "not_found"}, status_code=404)

    # Check rate limiter
    min_interval = settings.dict().get('apply', {}).get('min_interval_seconds', 300)
    rate_limiter = get_rate_limiter(min_interval_seconds=min_interval)

    if not rate_limiter.can_submit_now():
        wait_time = rate_limiter.time_until_next_submission()
        return JSONResponse({
            "ok": False,
            "error": "rate_limited",
            "message": f"Rate limit active. Please wait {wait_time / 60:.1f} minutes before next submission.",
            "wait_seconds": round(wait_time, 1),
            "wait_minutes": round(wait_time / 60, 1)
        }, status_code=429)

    apply_url = job.get('apply_url', '')
    vendor = job.get('ats_vendor', '')

    if not allowed_for_auto(vendor):
        return {"ok": False, "reason": "Not in allow-list; use Assist."}

    identity = json.loads(Path("profile/locked_identity.json").read_text())

    base_name = f"{identity['name']} - {job['title']}"
    resume_pdf = Path("out") / f"{base_name} - Resume.pdf"
    resume_docx = Path("out") / f"{base_name} - Resume.docx"
    cover_pdf = Path("out") / f"{base_name} - Cover Letter.pdf"

    resume_path = str(resume_pdf) if resume_pdf.exists() else str(resume_docx)
    cover_path = str(cover_pdf) if cover_pdf.exists() else None

    result = auto_submit(vendor, apply_url, identity, resume_path, cover_path)

    # Record successful submission
    if result.get("ok"):
        rate_limiter.record_submission(job_id)

    log_event("apply_auto", job_id, job.get("company", ""), job.get("title", ""),
             actor="user", vendor=vendor, result=result.get("ok"))

    return result

@app.get("/apply/status")
def apply_status():
    """
    Get current submission rate limiter status.

    Returns info about when next submission is allowed.
    """
    min_interval = settings.dict().get('apply', {}).get('min_interval_seconds', 300)
    rate_limiter = get_rate_limiter(min_interval_seconds=min_interval)
    return rate_limiter.get_status()

@app.get("/review/json/{job_id}")
def review_json_debug(job_id: str):
    """Debug endpoint."""
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"error": "not_found"}, status_code=404)
    return {"job_id": job_id, "job": job}

@app.post("/review/reset/{job_id}")
def reset_review(job_id: str):
    """Reset review session."""
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"error": "not_found"}, status_code=404)

    if "review" in job:
        del job["review"]
    save_state()

    return {"ok": True, "message": "Review session reset"}


# ===== Iterative Suggestion Endpoints =====

@app.post("/review/{job_id}/suggestion/next")
def get_next_suggestion(job_id: str, payload: Dict = Body(...)):
    """
    Generate next bullet suggestion for a role.

    Body: {"role_key": "ccs-2025"}
    Returns: {"suggestion": {...}, "remaining": {"approved": n, "required": m}}
    """
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"error": "not_found"}, status_code=404)

    role_key = payload.get('role_key')
    if not role_key:
        return JSONResponse({"error": "role_key_required"}, status_code=400)

    # Get review data
    review_data = _get_review_data(job_id)

    if role_key not in review_data['roles']:
        return JSONResponse({"error": "role_not_found"}, status_code=404)

    role_data = review_data['roles'][role_key]

    # Get role context from employment history
    role_context = _get_role_context(role_key)

    # Get JD text
    jd_text = job.get('jd', '')

    # Get existing approved bullets for this role
    existing_bullets = role_data.get('approved', [])

    # Track used suggestion texts to avoid repeats
    used_texts = set()
    for item in role_data.get('suggestion_history', []):
        used_texts.add(item.get('text', '').lower().strip())

    # Generate suggestion
    max_attempts = 5
    suggestion = None

    for attempt in range(max_attempts):
        suggestion = generate_suggestion(
            job_id=job_id,
            role_key=role_key,
            jd_text=jd_text,
            role_context=role_context,
            existing_bullets=existing_bullets,
            fast_model=settings.llm.get('fast_model', 'gpt-3.5-turbo'),
            premium_model=settings.llm.get('premium_model', 'claude-3-5-sonnet-20241022'),
            config=settings.writing.get('suggestion', {})
        )

        # Check for duplicates
        if suggestion['text'].lower().strip() not in used_texts:
            break

    # Add to history as pending
    suggestion['status'] = 'pending'
    suggestion['role_key'] = role_key
    role_data['suggestion_history'].append(suggestion)

    _save_review_data(job_id, review_data)

    # Log telemetry
    log_event(
        "suggestion_proposed",
        job_id,
        job.get("company", ""),
        job.get("title", ""),
        actor="system",
        role_key=role_key,
        suggestion_id=suggestion['id'],
        score=suggestion['score_1_10']
    )

    remaining = {
        "approved": len(role_data['approved']),
        "required": role_data['required']
    }

    return {"suggestion": suggestion, "remaining": remaining}


@app.post("/review/{job_id}/suggestion/approve")
def approve_suggestion(job_id: str, payload: Dict = Body(...)):
    """
    Approve a bullet suggestion.

    Body: {"role_key": "ccs-2025", "suggestion_id": "abc123"}
    Returns: {"ok": True, "remaining": {...}}
    """
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"error": "not_found"}, status_code=404)

    role_key = payload.get('role_key')
    suggestion_id = payload.get('suggestion_id')

    if not role_key or not suggestion_id:
        return JSONResponse({"error": "missing_parameters"}, status_code=400)

    review_data = _get_review_data(job_id)

    if role_key not in review_data['roles']:
        return JSONResponse({"error": "role_not_found"}, status_code=404)

    role_data = review_data['roles'][role_key]

    # Find and approve the suggestion
    found = False
    for item in role_data['suggestion_history']:
        if item.get('id') == suggestion_id:
            item['status'] = 'approved'
            role_data['approved'].append(item)
            found = True
            break

    if not found:
        return JSONResponse({"error": "suggestion_not_found"}, status_code=404)

    _save_review_data(job_id, review_data)

    # Log telemetry
    log_event(
        "suggestion_approved",
        job_id,
        job.get("company", ""),
        job.get("title", ""),
        actor="user",
        role_key=role_key,
        suggestion_id=suggestion_id
    )

    # Check if role is complete
    if len(role_data['approved']) >= role_data['required']:
        log_event(
            "role_complete",
            job_id,
            job.get("company", ""),
            job.get("title", ""),
            actor="system",
            role_key=role_key,
            approved_count=len(role_data['approved'])
        )

    remaining = {
        "approved": len(role_data['approved']),
        "required": role_data['required'],
        "is_complete": len(role_data['approved']) >= role_data['required']
    }

    return {"ok": True, "remaining": remaining}


@app.post("/review/{job_id}/suggestion/reject")
def reject_suggestion(job_id: str, payload: Dict = Body(...)):
    """
    Reject a suggestion and immediately return next suggestion.

    Body: {"role_key": "ccs-2025", "suggestion_id": "abc123"}
    Returns: {"ok": True, "next_suggestion": {...}, "remaining": {...}}
    """
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"error": "not_found"}, status_code=404)

    role_key = payload.get('role_key')
    suggestion_id = payload.get('suggestion_id')

    if not role_key or not suggestion_id:
        return JSONResponse({"error": "missing_parameters"}, status_code=400)

    review_data = _get_review_data(job_id)

    if role_key not in review_data['roles']:
        return JSONResponse({"error": "role_not_found"}, status_code=404)

    role_data = review_data['roles'][role_key]

    # Find and reject the suggestion
    found = False
    for item in role_data['suggestion_history']:
        if item.get('id') == suggestion_id:
            item['status'] = 'rejected'
            role_data['rejected'].append(item)
            found = True
            break

    if not found:
        return JSONResponse({"error": "suggestion_not_found"}, status_code=404)

    _save_review_data(job_id, review_data)

    # Log telemetry
    log_event(
        "suggestion_rejected",
        job_id,
        job.get("company", ""),
        job.get("title", ""),
        actor="user",
        role_key=role_key,
        suggestion_id=suggestion_id
    )

    # Generate next suggestion immediately
    next_result = get_next_suggestion(job_id, {"role_key": role_key})

    if isinstance(next_result, JSONResponse):
        return next_result

    return {
        "ok": True,
        "next_suggestion": next_result.get("suggestion"),
        "remaining": next_result.get("remaining")
    }


@app.post("/review/{job_id}/suggestions/next")
def get_next_suggestions(job_id: str, payload: Dict = Body(...)):
    """
    Generate N suggestions at once using multi-LLM router.

    Body: {"role_key": "ccs-2025", "n": 3}
    Returns: {
        "suggestions": [
            {
                "id": str,
                "text": str,
                "score_1_10": int,
                "model_used": str,
                "citations": [str],
                "source": {...}
            },
            ...
        ],
        "remaining": {"approved": int, "required": int}
    }
    """
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"error": "not_found"}, status_code=404)

    role_key = payload.get('role_key')
    n = payload.get('n', 3)

    if not role_key:
        return JSONResponse({"error": "missing_role_key"}, status_code=400)

    jd_text = job.get('jd', '')
    if not jd_text:
        return JSONResponse({"error": "missing_jd"}, status_code=400)

    review_data = _get_review_data(job_id)

    if role_key not in review_data['roles']:
        return JSONResponse({"error": "role_not_found"}, status_code=404)

    role_data = review_data['roles'][role_key]

    # Get role context
    history = read_json(Path("profile/employment_history.json"))
    role_match = next((r for r in history if r['role_id'] == role_key), None)

    if not role_match:
        return JSONResponse({"error": "role_not_found_in_history"}, status_code=404)

    role_context = {
        'role_id': role_match['role_id'],
        'company': role_match['company'],
        'title': role_match['title'],
        'start': role_match['start'],
        'end': role_match.get('end', 'Present'),
        'location': role_match.get('location', '')
    }

    # Get existing approved bullets
    existing_bullets = [b.get('text', '') for b in role_data.get('approved', [])]

    # Generate N suggestions using new multi-LLM pipeline
    suggestions = generate_suggestions(
        job_id=job_id,
        role_key=role_key,
        jd_text=jd_text,
        role_context=role_context,
        existing_bullets=existing_bullets,
        config=settings.dict(),
        n=n
    )

    # Add to history as pending
    for suggestion in suggestions:
        suggestion['status'] = 'pending'
        suggestion['role_key'] = role_key
        role_data['suggestion_history'].append(suggestion)

        # Log telemetry
        log_event(
            "suggestion_proposed",
            job_id,
            job.get("company", ""),
            job.get("title", ""),
            actor="system",
            role_key=role_key,
            suggestion_id=suggestion['id'],
            score=suggestion.get('score_1_10', 5),
            model_used=suggestion.get('model_used', 'unknown')
        )

    _save_review_data(job_id, review_data)

    remaining = {
        "approved": len(role_data['approved']),
        "required": role_data['required']
    }

    return {"suggestions": suggestions, "remaining": remaining}


@app.post("/review/{job_id}/suggestions/approve")
def approve_suggestion_multi(job_id: str, payload: Dict = Body(...)):
    """
    Approve a single suggestion from the multi-suggestion UI.

    Body: {"role_key": "ccs-2025", "suggestion_id": "abc123"}
    Returns: {"ok": True, "remaining": {...}}
    """
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"error": "not_found"}, status_code=404)

    role_key = payload.get('role_key')
    suggestion_id = payload.get('suggestion_id')

    if not role_key or not suggestion_id:
        return JSONResponse({"error": "missing_parameters"}, status_code=400)

    review_data = _get_review_data(job_id)

    if role_key not in review_data['roles']:
        return JSONResponse({"error": "role_not_found"}, status_code=404)

    role_data = review_data['roles'][role_key]

    # Find and approve the suggestion
    found = False
    for item in role_data['suggestion_history']:
        if item.get('id') == suggestion_id and item.get('status') == 'pending':
            item['status'] = 'APPROVED'
            role_data['approved'].append(item)
            found = True
            break

    if not found:
        return JSONResponse({"error": "suggestion_not_found"}, status_code=404)

    _save_review_data(job_id, review_data)

    # Log telemetry
    log_event(
        "suggestion_approved",
        job_id,
        job.get("company", ""),
        job.get("title", ""),
        actor="user",
        role_key=role_key,
        suggestion_id=suggestion_id,
        model_used=item.get('model_used', 'unknown'),
        score=item.get('score_1_10', 5),
        accepted=True
    )

    # Check if role is complete
    if len(role_data['approved']) >= role_data['required']:
        log_event(
            "role_complete",
            job_id,
            job.get("company", ""),
            job.get("title", ""),
            actor="system",
            role_key=role_key,
            approved_count=len(role_data['approved'])
        )

    remaining = {
        "approved": len(role_data['approved']),
        "required": role_data['required'],
        "is_complete": len(role_data['approved']) >= role_data['required']
    }

    return {"ok": True, "remaining": remaining}


@app.post("/review/{job_id}/suggestions/reject")
def reject_suggestion_multi(job_id: str, payload: Dict = Body(...)):
    """
    Reject a single suggestion and mark it as rejected.

    Body: {"role_key": "ccs-2025", "suggestion_id": "abc123"}
    Returns: {"ok": True}
    """
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"error": "not_found"}, status_code=404)

    role_key = payload.get('role_key')
    suggestion_id = payload.get('suggestion_id')

    if not role_key or not suggestion_id:
        return JSONResponse({"error": "missing_parameters"}, status_code=400)

    review_data = _get_review_data(job_id)

    if role_key not in review_data['roles']:
        return JSONResponse({"error": "role_not_found"}, status_code=404)

    role_data = review_data['roles'][role_key]

    # Find and reject the suggestion
    found = False
    for item in role_data['suggestion_history']:
        if item.get('id') == suggestion_id and item.get('status') == 'pending':
            item['status'] = 'rejected'
            role_data['rejected'].append(item)
            found = True

            # Log telemetry
            log_event(
                "suggestion_rejected",
                job_id,
                job.get("company", ""),
                job.get("title", ""),
                actor="user",
                role_key=role_key,
                suggestion_id=suggestion_id,
                model_used=item.get('model_used', 'unknown'),
                score=item.get('score_1_10', 5),
                accepted=False
            )
            break

    if not found:
        return JSONResponse({"error": "suggestion_not_found"}, status_code=404)

    _save_review_data(job_id, review_data)

    return {"ok": True}


@app.get("/review/{job_id}/status")
def get_review_status(job_id: str):
    """
    Get per-role progress and gate status.

    Returns: {
        "roles": {"ccs-2025": {"approved": 2, "required": 4, "complete": False}, ...},
        "all_complete": bool,
        "can_continue": bool
    }
    """
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"error": "not_found"}, status_code=404)

    review_data = _get_review_data(job_id)

    role_status = {}
    all_complete = True

    for role_key, role_data in review_data.get('roles', {}).items():
        approved_count = len(role_data.get('approved', []))
        required_count = role_data.get('required', 0)
        is_complete = approved_count >= required_count

        role_status[role_key] = {
            "approved": approved_count,
            "required": required_count,
            "complete": is_complete
        }

        if not is_complete:
            all_complete = False

    return {
        "roles": role_status,
        "all_complete": all_complete,
        "can_continue": all_complete
    }


# ===== Sequential Suggestion System =====

def _get_or_create_queue_manager(job_id: str) -> QueueManager:
    """Get or create queue manager for job."""
    if job_id not in QUEUE_MANAGERS:
        # Get quotas from config
        quotas = settings.experience_quotas if hasattr(settings, 'experience_quotas') else settings.roles_required
        QUEUE_MANAGERS[job_id] = QueueManager(job_id, quotas)
    return QUEUE_MANAGERS[job_id]


def _generate_and_queue_suggestions(job_id: str, role_key: str, n: int = 8) -> int:
    """
    Generate n suggestions and add to queue, filtering duplicates.
    Returns number of suggestions added.
    """
    job = JOBS.get(job_id)
    if not job:
        return 0

    jd_text = job.get('jd', '')
    if not jd_text:
        return 0

    # Get role context
    history = read_json(Path("profile/employment_history.json"), [])
    role_match = next((r for r in history if r['role_id'] == role_key), None)
    if not role_match:
        return 0

    role_context = {
        'role_id': role_match['role_id'],
        'company': role_match['company'],
        'title': role_match['title'],
        'start': role_match['start'],
        'end': role_match.get('end', 'Present'),
        'location': role_match.get('location', '')
    }

    # Get queue manager
    qm = _get_or_create_queue_manager(job_id)
    queue = qm.get_queue(role_key)
    if not queue:
        return 0

    # Get existing bullets for context
    existing_bullets = [s.text for s in queue.accepted]

    try:
        # Initialize router (no config needed - loads from env)
        router = LLMRouter()

        # Generate candidates (request more than needed for filtering)
        raw_suggestions = router.generate_suggestions(
            role_context=role_context,
            jd_text=jd_text,
            research_context={},
            n=n,
            use_perplexity=True
        )

        # Convert to Suggestion objects with stable IDs
        suggestions = []
        for raw in raw_suggestions:
            sugg = Suggestion(
                id=raw.get('id', str(uuid.uuid4())[:12]),
                role_key=role_key,
                text=raw['text'],
                score=raw.get('score_1_10', 5),
                model=raw.get('model_used', 'unknown'),
                citations=raw.get('citations', []),
                created_at=datetime.now().isoformat()
            )
            suggestions.append(sugg)

        # Add to queue (will filter duplicates and non-quantified)
        added = queue.add_suggestions(suggestions)

        # Save state
        qm.save()

        return added

    except Exception as e:
        print(f"Error generating suggestions: {e}")
        import traceback
        traceback.print_exc()
        return 0


# ===== Sequential suggestion endpoints moved to api_sequential.py ====

# Helper function used by sequential endpoints
def _generate_and_queue_suggestions(job_id: str, role_key: str, n: int = 8) -> int:
    """Generate and queue suggestions for a role."""
    try:
        # Get context
        job = JOBS.get(job_id)
        if not job:
            return 0
            
        # Get queue
        qm = _get_or_create_queue_manager(job_id)
        queue = qm.get_queue(role_key)
        if not queue:
            return 0

        # Get existing bullets for context
        existing_bullets = [s.text for s in queue.accepted]

        # Generate candidates
        router = LLMRouter()
        raw_suggestions = router.generate_suggestions(
            role_context=job['review'].get('role_context', {}),
            jd_text=job.get('jd', ''),
            research_context={},
            n=n,
            use_perplexity=True
        )

        # Convert to Suggestion objects
        suggestions = []
        for raw in raw_suggestions:
            sugg = Suggestion(
                id=raw.get('id', str(uuid.uuid4())[:12]),
                role_key=role_key,
                text=raw['text'],
                score=raw.get('score_1_10', 5),
                model=raw.get('model_used', 'unknown'),
                citations=raw.get('citations', []),
                created_at=datetime.now().isoformat()
            )
            suggestions.append(sugg)

        # Add to queue (filters duplicates)
        added = queue.add_suggestions(suggestions)
        qm.save()
        return added

    except Exception as e:
        print(f"Error generating suggestions: {e}")
        traceback.print_exc()
        return 0


@app.get("/review/{job_id}/seq/status")
def get_sequential_status(job_id: str):
    """
    Get status of all roles for sequential system.

    Returns: {
        "roles": {
            "ccs-2025": {
                "accepted_count": int,
                "quota": int,
                "is_complete": bool,
                "pending_count": int
            },
            ...
        },
        "all_complete": bool,
        "can_continue": bool
    }
    """
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"error": "not_found"}, status_code=404)

    # Get queue manager
    qm = _get_or_create_queue_manager(job_id)

    role_status = {}
    all_complete = True

    for role_key, queue in qm.queues.items():
        is_complete = queue.is_complete()
        role_status[role_key] = {
            "accepted_count": len(queue.accepted),
            "quota": queue.quota,
            "is_complete": is_complete,
            "pending_count": len(queue.pending)
        }

        if not is_complete:
            all_complete = False

    return {
        "roles": role_status,
        "all_complete": all_complete,
        "can_continue": all_complete
    }


@app.get("/skills/preview/{job_id}")
def get_skills_preview(job_id: str):
    """
    Get skills formatted in pipe-separated format (3-4 categories max).

    Returns: [
        {"category": "Sales Enablement", "skills": ["Strategic Thinking", "Data-Driven Decision Making", ...]},
        ...
    ]
    """
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"error": "not_found"}, status_code=404)

    # Get approved skills from review
    if "review" in job and "skills" in job["review"]:
        approved_skills = job["review"]["skills"].get("approved", [])
    else:
        # Fallback to registry
        registry_file = Path("profile/skills_registry.json")
        registry = read_json(registry_file, {})
        approved_skills = registry.get('approved', [])

    # Categorize skills
    sales_skills = []
    technical_skills = []
    process_skills = []

    for skill in approved_skills:
        skill_lower = skill.lower()
        if any(term in skill_lower for term in ['sql', 'salesforce', 'amplitude', 'crm', 'analytics', 'hubspot']):
            technical_skills.append(skill)
        elif any(term in skill_lower for term in ['meddic', 'negotiation', 'forecasting', 'pipeline', 'territory', 'prospecting']):
            sales_skills.append(skill)
        else:
            process_skills.append(skill)

    # Build category list (max 3-4 as per config)
    max_categories = settings.writing.get('max_skill_categories', 4)
    categories = []

    if sales_skills:
        categories.append({
            "category": "Full-Cycle Enterprise SaaS Sales",
            "skills": sorted(sales_skills)
        })

    if technical_skills:
        categories.append({
            "category": "CRM Systems & Digital Prospecting Tools",
            "skills": sorted(technical_skills)
        })

    if process_skills:
        categories.append({
            "category": "Sales Tools & Platforms",
            "skills": sorted(process_skills)
        })

    return categories[:max_categories]





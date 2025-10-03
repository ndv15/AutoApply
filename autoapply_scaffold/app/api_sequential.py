"""Sequential Review API Endpoints"""
from typing import Dict, Optional
from fastapi import Body, Request
from fastapi.responses import JSONResponse, HTMLResponse
from pathlib import Path
import json
import uuid
from datetime import datetime

from .api import app, JOBS, templates
from .writing.sequential_config import SequentialConfig
from .writing.suggestion_store import SuggestionStore
from .writing.experience import generate_suggestion
from .assemble.resume import render_resume_preview
from .utils.telemetry import log_event

@app.get("/review/{job_id}", response_class=HTMLResponse)
async def review_page(request: Request, job_id: str, mode: Optional[str] = None):
    """Render review page."""
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"error": "not_found"}, status_code=404)
        
    if mode == "seq":
        return templates.TemplateResponse(
            "review_sequential.html",
            {"request": request, "job_id": job_id}
        )
    
    return templates.TemplateResponse(
        "review.html", 
        {"request": request, "job_id": job_id}
    )

@app.post("/review/{job_id}/suggestions/seq/next")
async def get_next_suggestion(job_id: str, payload: Dict = Body(...)):
    """Get next suggestion for sequential review."""
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"error": "not_found"}, status_code=404)
        
    role_key = payload.get('role_key')
    if not role_key:
        return JSONResponse({"error": "role_key_required"}, status_code=400)
        
    # Get the next suggestion
    store = SuggestionStore(job_id)
    suggestion = store.get_next_suggestion(role_key)
    
    # If no suggestion in queue, generate a new one
    if not suggestion:
        suggestion = generate_suggestion(
            job_id=job_id,
            role_key=role_key,
            jd_text=job.get('jd', ''),
            role_context=next(
                (r for r in job.get('history', []) if r.get('role_id') == role_key),
                {'role_id': role_key}
            )
        )
        if suggestion:
            suggestion['role_key'] = role_key
            store.add_suggestion(role_key, suggestion)
    
    # Get updated progress
    quota = SequentialConfig.get_role_quota(role_key)
    approved = len(store.get_approved_bullets().get(role_key, []))
    is_complete = approved >= quota

    return {
        "suggestion": suggestion,
        "remaining": {
            "approved": approved,
            "quota": quota,
            "is_complete": is_complete
        }
    }
    store = SuggestionStore(job_id)
    suggestion = store.get_next_suggestion(role_key)
    
    # If no suggestion in queue, generate a new one
    if not suggestion:
        suggestion = generate_next_suggestion(
            job_id=job_id,
            role_key=role_key,
            jd_text=job.get('jd', ''),
            role_context=next(
                (r for r in job.get('history', []) if r.get('role_id') == role_key),
                {'role_id': role_key}
            )
        )
        
    if not suggestion:
        return JSONResponse({"error": "no_suggestions"}, status_code=404)
        
    return suggestion

@app.post("/review/{job_id}/suggestions/seq/accept")
async def accept_suggestion(job_id: str, payload: Dict = Body(...)):
    """Accept a suggestion and update preview."""
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"error": "not_found"}, status_code=404)
        
    role_key = payload.get('role_key')
    suggestion_id = payload.get('suggestion_id')
    
    if not role_key or not suggestion_id:
        return JSONResponse({"error": "invalid_payload"}, status_code=400)
        
    store = SuggestionStore(job_id)
    
    # Get and remove the suggestion from queue
    suggestion = store.pop_suggestion(role_key, suggestion_id)
    if not suggestion:
        # If already processed, return success
        return {"ok": True, "already_processed": True}
        
    # Record the approval
    store.approve_suggestion(role_key, suggestion)
    
    # Get updated progress
    progress = store.get_progress({
        role_key: get_role_quota(role_key)
        for role_key in {r.get('role_id') for r in job.get('history', [])}
    })
    
    # Generate preview HTML
    approved_bullets = store.get_approved_bullets()
    preview_html = render_resume_preview(
        identity=json.loads(Path("profile/locked_identity.json").read_text()),
        exec_summary=job["review"]["exec_summary"],
        soq=job["review"]["soq"],
        approved_bullets=approved_bullets,
        skills=job["review"]["skills"]["approved"]
    )
    
    log_event("suggestion_accepted", job_id, job.get("company", ""), job.get("title", ""),
             actor="user", suggestion_id=suggestion_id, role_key=role_key)
             
    return {
        "ok": True,
        "progress": progress,
        "preview_html": preview_html
    }

@app.post("/review/{job_id}/suggestions/seq/reject")
async def reject_suggestion(job_id: str, payload: Dict = Body(...)):
    """Reject a suggestion."""
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"error": "not_found"}, status_code=404)
        
    role_key = payload.get('role_key')
    suggestion_id = payload.get('suggestion_id')
    
    if not role_key or not suggestion_id:
        return JSONResponse({"error": "invalid_payload"}, status_code=400)
        
    store = SuggestionStore(job_id)
    
    # Remove suggestion from queue
    suggestion = store.pop_suggestion(role_key, suggestion_id)
    if not suggestion:
        # If already processed, return success
        return {"ok": True, "already_processed": True}
    
    log_event("suggestion_rejected", job_id, job.get("company", ""), job.get("title", ""),
             actor="user", suggestion_id=suggestion_id, role_key=role_key)
             
    return {"ok": True}

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
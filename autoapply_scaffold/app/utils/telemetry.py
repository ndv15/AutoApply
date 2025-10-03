"""
Minimal telemetry logger for AutoApply events.
Appends JSONL to logs/events.jsonl
"""
import json
from pathlib import Path
from datetime import datetime


def log_event(event_type: str, job_id: str, company: str, title: str,
              actor: str = "user", **payload):
    """
    Log an event to logs/events.jsonl

    Args:
        event_type: ingest, manual_ingest, review_approve_bullets,
                    review_approve_skills, build_files, apply_auto, apply_assist
        job_id: Job identifier
        company: Company name
        title: Job title
        actor: "user" or "system"
        **payload: Additional event-specific data
    """
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)

    event = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event_type": event_type,
        "job_id": job_id,
        "company": company,
        "title": title,
        "actor": actor,
        **payload
    }

    log_file = logs_dir / "events.jsonl"
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(event) + '\n')

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import asyncio
import json
import markdown as md

from autoapply.orchestration.run import Orchestrator

app = FastAPI()


def md_to_html(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return md.markdown(text)


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(
        """
        <html>
        <head><title>AutoApply Preview Server</title></head>
        <body>
        <h1>AutoApply Preview</h1>
        <form action="/generate" method="post">
          <label for="job">Job JSON</label><br/>
          <textarea name="job" rows="20" cols="80">{"title":"Software Engineer","company":"Acme Corp"}</textarea><br/>
          <label for="quota">Quota (optional)</label>
          <input name="quota" type="number" min="1" /><br/>
          <label for="skills">Skills (comma separated, optional)</label>
          <input name="skills" type="text" size="80" /><br/>
          <button type="submit">Generate Preview</button>
        </form>
        </body>
        </html>
        """,
        status_code=200,
    )


@app.post("/generate", response_class=HTMLResponse)
async def generate(job: str = Form(...), quota: int | None = Form(None), skills: str | None = Form(None)):
    try:
        job_obj = json.loads(job)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    quota_val = int(quota) if quota else None
    skills_list = [s.strip() for s in skills.split(",")] if skills else None

    # Use default quota if not provided
    orchestrator = Orchestrator(job=job_obj, quota=quota_val or 6, skills=skills_list)

    # Run start/generate/commit loop programmatically until Done.
    await orchestrator.start()
    while True:
        await orchestrator.generate_or_stop()
        if orchestrator.state == "Done":
            break
        # Auto-accept all proposed bullets to drive toward completion.
        # This mimics a headless run where the system accepts every proposed bullet.
        # Retrieve draft id and accept all proposed bullet ids.
        from autoapply.store.memory_store import get_draft

        draft = get_draft(orchestrator.draft_id)
        proposed = [b.id for b in draft.bullets if b.status == "proposed"]
        # Commit accepts, no rejects.
        await orchestrator.commit(proposed, [])
        if orchestrator.state == "Done":
            break
        await orchestrator.regenerate_if_needed()

    # After completion, read the preview file and convert to HTML.
    preview_path = Path("preview") / f"{orchestrator.draft_id}.md"
    if not preview_path.exists():
        raise HTTPException(status_code=500, detail="Preview file not found after generation")

    html = md_to_html(preview_path)
    return HTMLResponse(html)

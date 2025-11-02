"""Markdown preview rendering for accepted bullets and skills."""

from pathlib import Path
from autoapply.store.memory_store import get_draft


def render_preview(draft_id: str, out_dir: str = "preview") -> Path:
    """Render a Markdown preview of the current draft.

    The preview contains the job title and company, followed by the list of
    accepted bullets under an ``Experience`` section and a list of skills
    under a ``Skills`` section.  Only bullets with status ``accepted``
    appear in the preview.

    :param draft_id: ID of the draft to render.
    :param out_dir: Directory in which to place the Markdown file.
    :returns: A :class:`pathlib.Path` pointing to the generated file.
    """
    draft = get_draft(draft_id)
    accepted = [b for b in draft.bullets if b.status == "accepted"]
    lines = [
        f"# {draft.job.title} @ {draft.job.company}",
        "",
        "## Experience",
    ]
    lines.extend([f"- {b.text}" for b in accepted])
    lines.append("")
    lines.append("## Skills")
    lines.extend([f"- {s.raw}" for s in draft.skills])
    out_path = Path(out_dir) / f"{draft_id}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path
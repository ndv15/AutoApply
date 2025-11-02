"""Command‑line interface for AutoApply."""

import sys
import json
import asyncio
import questionary
from autoapply.config.env import ENV
from autoapply.orchestration.run import Orchestrator
from autoapply.store.memory_store import get_draft


async def _run(job_path: str, quota: int) -> None:
    """Run the interactive resume tailoring process."""
    with open(job_path, "r", encoding="utf-8") as f:
        job = json.load(f)
    orchestrator = Orchestrator(job=job, quota=quota)
    await orchestrator.start()
    while True:
        await orchestrator.generate_or_stop()
        if orchestrator.state == "Done":
            print("All done.")
            break
        draft = get_draft(orchestrator.draft_id)
        proposed = [b for b in draft.bullets if b.status == "proposed"]
        accept: list[str] = []
        reject: list[str] = []
        for bullet in proposed:
            # Run blocking Questionary prompt in a separate thread to avoid
            # prompt_toolkit calling asyncio.run() from inside an already
            # running event loop.
            answer = await asyncio.to_thread(
                lambda b=bullet: questionary.select(b.text, choices=["Accept", "Reject"]).ask()
            )
            if answer == "Accept":
                accept.append(bullet.id)
            else:
                reject.append(bullet.id)
        await orchestrator.commit(accept, reject)
        if orchestrator.state == "Done":
            break
        await orchestrator.regenerate_if_needed()


def main() -> None:
    """CLI entry point.

    Accepts a path to a JSON file describing the job and an optional
    quota.  When the quota is omitted it falls back to the default
    configured via the ``.env`` file.
    """
    if len(sys.argv) < 2:
        print("Usage: python -m autoapply.cli.app <job.json> [quota]")
        sys.exit(1)
    job_path = sys.argv[1]
    quota = int(sys.argv[2]) if len(sys.argv) > 2 else ENV.QUOTA_DEFAULT
    asyncio.run(_run(job_path, quota))


if __name__ == "__main__":
    main()
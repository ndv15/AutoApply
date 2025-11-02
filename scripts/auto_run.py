"""Non-interactive runner to auto-accept proposed bullets and generate preview.

Usage: python scripts/auto_run.py examples/job.json [quota]
"""
import sys
import asyncio
import json

from autoapply.orchestration.run import Orchestrator
from autoapply.store.memory_store import get_draft


async def run(job_path: str, quota: int | None = None) -> None:
    with open(job_path, "r", encoding="utf-8") as f:
        job = json.load(f)
    orch = Orchestrator(job=job, quota=quota or 6)
    await orch.start()
    # Keep generating until done. Accept all proposed bullets each round.
    while True:
        await orch.generate_or_stop()
        if orch.state == "Done":
            break
        draft = get_draft(orch.draft_id)
        proposed = [b.id for b in draft.bullets if b.status == "proposed"]
        # Accept everything
        await orch.commit(proposed, [])
        if orch.state == "Done":
            break
        await orch.regenerate_if_needed()


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print("Usage: python scripts/auto_run.py <job.json> [quota]")
        sys.exit(1)
    job_path = argv[1]
    quota = int(argv[2]) if len(argv) > 2 else None
    asyncio.run(run(job_path, quota))


if __name__ == "__main__":
    main(sys.argv)

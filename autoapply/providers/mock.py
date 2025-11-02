"""Mock implementations of research, generation and rerank providers.

These providers produce deterministic output suitable for testing and
development.  They do not call any external services and instead
generate bullet points based on the job title, company and a simple
counter.  Negative phrases in constraints are used to avoid repeating
unwanted starting phrases.
"""

from typing import List
from autoapply.providers.base import (
    ResearchProvider,
    RerankProvider,
    GeneratorProvider,
    GenerationRequest,
    GenerationResponse,
)


# Simple word banks for deterministic mock generation.
VERBS = ["Improved", "Optimized", "Accelerated", "Increased", "Reduced"]
OUTCOMES = [
    "improved reliability",
    "increased throughput",
    "reduced latency",
    "boosted conversion",
    "saved cost",
]
TOOLS = ["using Python", "with SQL", "via Kubernetes", "using Airflow", "with Tableau"]


class MockResearch(ResearchProvider):
    """Return basic research hints from the job spec."""

    async def research(self, job):  # type: ignore[override]
        return list({job.title, job.company, *job.keywords})


class MockRerank(RerankProvider):
    """Return the top items without any ranking logic."""

    async def rerank(self, items: List[str], query: str) -> List[str]:  # type: ignore[override]
        return items[:10]


class MockGenerator(GeneratorProvider):
    """Generate deterministic AMOT bullets with optional constraints."""

    async def generate(self, req: GenerationRequest) -> GenerationResponse:  # type: ignore[override]
        avoid = set((req.get("constraints") or {}).get("negativePhrases", []) or [])
        bullets: List[str] = []
        for i in range(req["count"]):
            verb = VERBS[i % len(VERBS)]
            pct = 10 + i * 5
            outcome = OUTCOMES[i % len(OUTCOMES)]
            tool = TOOLS[i % len(TOOLS)]
            base = f"{verb} data pipeline by {pct}% which {outcome} {tool}"
            if not any(phrase.lower() in base.lower() for phrase in avoid):
                bullets.append(base)
            else:
                # Fall back to a different subject to avoid the negative phrase.
                bullets.append(f"{verb} reporting workflow by {pct}% which {outcome} {tool}")
        return {"bullets": bullets}
"""Base classes and protocols for providers.

Providers encapsulate external functionality such as job research,
generation of AMOT bullets and reranking.  Using :class:`typing.Protocol`
allows different implementations to satisfy the same API without
explicit inheritance.  See :mod:`autoapply.providers.mock` for a
reference implementation.
"""

from typing import Protocol, List, TypedDict
from autoapply.domain.schemas import JobSpec


class GenerationRequest(TypedDict):
    """Request to generate AMOT bullets."""

    job: JobSpec
    count: int
    constraints: dict | None


class GenerationResponse(TypedDict):
    """Response containing generated bullet texts."""

    bullets: List[str]


class ResearchProvider(Protocol):
    """Protocol for providers that perform job research."""

    async def research(self, job: JobSpec) -> List[str]:
        """Perform research on a job spec and return a list of hints."""
        ...


class RerankProvider(Protocol):
    """Protocol for providers that rerank generated items."""

    async def rerank(self, items: List[str], query: str) -> List[str]:
        """Return the top items best matching the query."""
        ...


class GeneratorProvider(Protocol):
    """Protocol for providers that generate AMOT bullets."""

    async def generate(self, req: GenerationRequest) -> GenerationResponse:
        ...


class ProviderBundle(TypedDict):
    """Convenience bundle of provider implementations."""

    research: ResearchProvider
    generator: GeneratorProvider
    rerank: RerankProvider
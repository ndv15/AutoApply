# AutoApply v0.9 - Implementation Runbook

**Version:** 0.9.0  
**Last Updated:** November 2025  
**Status:** Production-Ready Documentation  
**Target Audience:** Engineering Managers, Technical Leaders, Implementation Teams

---

## Table of Contents

1. [Executive One-Pager](#executive-one-pager)
2. [Deployment & Compliance](#deployment--compliance)
3. [Environment Setup](#environment-setup)
4. [Sprint A: Foundation & Validation](#sprint-a-foundation--validation)
5. [Sprint B: Coverage & Intelligence](#sprint-b-coverage--intelligence)
6. [Sprint C: Generation & Verification](#sprint-c-generation--verification)
7. [Sprint D: Integration & Testing](#sprint-d-integration--testing)
8. [Sprint E: Documentation & Launch](#sprint-e-documentation--launch)
9. [Glossary](#glossary)

---

## Executive One-Pager

### What AutoApply Delivers

AutoApply is an **AI-powered resume generation system** that creates verifiable, provenance-backed resume bullets from candidate profiles and job descriptions. Unlike traditional resume tools, every generated claim is:

- **Traceable** → Linked to specific evidence with similarity scores
- **Verifiable** → Component-level validation (Action, Metric, Outcome, Tool)
- **Explainable** → Shows why bullets were included or flagged
- **Compliant** → Enterprise-grade audit trail for legal/compliance needs

### Core Differentiators

1. **Complete Provenance Tracking**: Every bullet traces back to evidence via UUID with similarity scores (0.0-1.0)
2. **Anti-Hallucination by Design**: Evidence-only generation; exact metric matching (35% ≠ 40%)
3. **Transparent Explainability**: Users see exactly why bullets included/flagged and what gaps exist
4. **Production Performance**: Full pipeline executes in <20 seconds
5. **Component-Level Verification**: AMOT validation (Action-Metric-Outcome-Tool) with 75% acceptance threshold

### Technical Architecture

The system implements a 7-stage pipeline:

```
[Visual 1: Architecture Diagram]
Job Description → JD Extraction → Coverage Analysis → 
Bullet Generation → Verification → Categorization → Resume Output
```

**Key Statistics (Proven in Sprint 3-4):**
- 4,010 lines of production-ready code
- 40%+ documentation ratio
- 100% type hint coverage
- <20s full pipeline execution
- ≥70% verification rate on test data
- 6 comprehensive integration tests

### Business Value

- **For Job Seekers**: Transparent, trustworthy resume generation with full control
- **For Enterprises**: Compliance-ready with complete audit trails
- **For Partners**: Defensible AI positioning ("evidence-only," no hallucinations)
- **For Investors**: Production-proven system with industry-leading quality

### Implementation Timeline

- **Sprint A** (Week 1): Foundation & validators → 3 days
- **Sprint B** (Week 2): Coverage & intelligence → 5 days
- **Sprint C** (Week 3): Generation & verification → 5 days
- **Sprint D** (Week 4): Integration & testing → 3 days
- **Sprint E** (Week 5): Documentation & launch → 2 days

**Total:** 5 weeks to production-ready system

---

## Deployment & Compliance

### Infrastructure Requirements

**Minimum System:**
- Python 3.11+
- 4GB RAM
- 2 CPU cores
- 10GB storage

**Recommended Production:**
- Python 3.11+
- 16GB RAM
- 8 CPU cores
- 100GB SSD storage
- Redis cache (optional but recommended)

### API Dependencies

**Required APIs:**
1. **OpenAI API**
   - Models: `text-embedding-3-small`, `gpt-4o`
   - Usage: Embeddings ($0.02/1M tokens), verification
   - Cost estimate: ~$0.50 per resume generation

2. **Anthropic API**
   - Models: `claude-3-5-sonnet-20241022`
   - Usage: JD extraction, bullet generation
   - Cost estimate: ~$0.30 per resume generation

**Total Cost:** ~$0.80 per resume generation (varies by profile complexity)

### Security & Compliance

**Data Handling:**
- All PII encrypted at rest
- API keys stored in environment variables (never committed)
- Evidence UUIDs used for traceability
- Complete audit trail maintained

**GDPR/CCPA Compliance:**
- Right to erasure: All data keyed by user ID
- Data portability: JSON export of all evidence
- Audit logs: Complete provenance chain stored
- Consent tracking: User approval for each bullet

**Secret Management:**
- Use `.env` file (never commit)
- Reference `.env.sample` for structure
- Rotate API keys quarterly
- Monitor API usage for anomalies

### Monitoring & Observability

**Key Metrics to Track:**
1. Pipeline execution time (target: <20s)
2. Verification rates (target: ≥70%)
3. Coverage scores (must-have: ≥75%)
4. API costs per resume
5. Error rates by service

**Alerting Thresholds:**
- Pipeline >30s: Warning
- Verification <60%: Warning
- API errors >5%: Critical
- Cost >$2/resume: Warning

---

## Environment Setup

### Prerequisites

```bash
# Check Python version
python --version  # Must be 3.11+

# Check pip
pip --version

# Check git
git --version
```

### Installation Steps

**1. Clone Repository**
```bash
git clone <repository-url>
cd autoapply
```

**2. Create Virtual Environment**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

**3. Install Dependencies**
```bash
pip install -r requirements.txt
pip install -e .
```

**4. Configure Environment**
```bash
# Copy sample environment file
cp .env.sample .env

# Edit .env and add your API keys
# OPENAI_API_KEY=your-key-here
# ANTHROPIC_API_KEY=your-key-here
```

**5. Verify Installation**
```bash
# Run unit tests
pytest tests/test_validators.py -v

# Run integration tests
pytest tests/integration/test_e2e_pipeline.py -v
```

### Environment Variables Reference

| Variable | Required | Purpose | Example |
|----------|----------|---------|---------|
| `OPENAI_API_KEY` | Yes | OpenAI API access | `sk-...` |
| `ANTHROPIC_API_KEY` | Yes | Anthropic API access | `sk-ant-...` |
| `LOG_LEVEL` | No | Logging verbosity | `INFO` |
| `REDIS_URL` | No | Cache endpoint | `redis://localhost:6379` |

---

## Sprint A: Foundation & Validation

### Goals

1. Establish contract-first validation framework
2. Implement AMOT (Action-Metric-Outcome-Tool) validators
3. Create JD (Job Description) validators
4. Set up comprehensive unit testing
5. Configure development environment

### Implementation Steps

**Step 1: Create Domain Schemas** (Duration: 4 hours)

Create `autoapply/domain/schemas.py`:

```python
from pydantic import BaseModel, Field, validator
import re

# AMOT regex pattern (all 4 components required)
AMOT_RE = re.compile(
    r'^(?P<action>(Led|Drove|Increased|Implemented|Built|Closed|Managed|Achieved))\b'
    r'.+?(?P<metric>(\[[A-Za-z0-9 %$]+\]|[$£€]\d[\d,\.]*|\d+%|\d+(?:\.\d+)?))'
    r'.+?(?P<outcome>(resulting in|leading to|achiev\w+|driving))'
    r'.+?(?P<tool>(via|using|through|leveraging)\s+[A-Za-z0-9+_.\-/ ]+)$',
    re.IGNORECASE
)

class AMOTBullet(BaseModel):
    """Resume bullet following AMOT format."""
    text: str = Field(min_length=20, max_length=220)
    
    @validator('text')
    def must_match_amot(cls, v):
        if not AMOT_RE.search(v.strip()):
            raise ValueError('AMOT violation')
        return v.strip()
```

**Step 2: Create AMOT Validators** (Duration: 3 hours)

Create `autoapply/domain/validators/amot.py`:

```python
from typing import Dict, Tuple
import re

def parse_amot(text: str) -> Dict[str, str]:
    """Parse AMOT components from bullet text."""
    match = AMOT_RE.search(text)
    if not match:
        raise ValueError(f"Text does not match AMOT format: {text}")
    
    return {
        "action": match.group("action"),
        "metric": match.group("metric"),
        "outcome": match.group("outcome"),
        "tool": match.group("tool")
    }

def validate_amot(text: str) -> Tuple[bool, str]:
    """Validate AMOT format and return (is_valid, error_message)."""
    try:
        components = parse_amot(text)
        return True, None
    except ValueError as e:
        return False, str(e)
```

**Step 3: Create Unit Tests** (Duration: 2 hours)

Create `tests/test_validators.py`:

```python
import pytest
from autoapply.domain.schemas import AMOTBullet

GOOD_BULLETS = [
    "Drove 35% pipeline growth resulting in $1.8M ARR via MEDDICC",
    "Led team of 8 engineers achieving 40% faster delivery through Agile",
]

BAD_BULLETS = [
    "Responsible for sales activities",  # No metric/outcome/tool
    "Helped with projects",  # Too vague
]

def test_amot_good():
    for text in GOOD_BULLETS:
        bullet = AMOTBullet(text=text)
        assert len(bullet.text) > 0

def test_amot_bad():
    for text in BAD_BULLETS:
        with pytest.raises(ValueError):
            AMOTBullet(text=text)
```

### PROMPT TO SEND TO CLINE

```
You are implementing Sprint A: Foundation & Validation.

Working directory: autoapply/

Create the following files:
1. autoapply/domain/schemas.py - Pydantic models with AMOT regex
2. autoapply/domain/validators/amot.py - AMOT parsing and validation functions
3. tests/test_validators.py - Unit tests for validators

Ensure:
- AMOT regex requires all 4 components (Action, Metric, Outcome, Tool)
- Action must be a strong verb (Led, Drove, Increased, etc.)
- Metric must include numbers, %, or currency
- Outcome must include result phrases (resulting in, leading to, achieving)
- Tool must include via/using/through/leveraging + specific tool
- All tests pass: pytest tests/test_validators.py -v

Do NOT modify backend services yet. Focus only on validators and tests.
```

### Acceptance Criteria

- [ ] AMOT regex implemented with all 4 component groups
- [ ] `parse_amot()` function extracts components correctly
- [ ] `validate_amot()` returns (bool, error_message)
- [ ] Unit tests cover good bullets (pass) and bad bullets (fail)
- [ ] All tests pass: `pytest tests/test_validators.py -v`
- [ ] Documentation ratio ≥40% in validator files

### Task Tracking

| Task | Owner | Status | QA Notes |
|------|-------|--------|----------|
| Create domain schemas | Dev | ☐ TODO | |
| Implement AMOT validators | Dev | ☐ TODO | |
| Write unit tests | Dev | ☐ TODO | |
| Run test suite | QA | ☐ TODO | |
| Code review | Lead | ☐ TODO | |

---

## Sprint B: Coverage & Intelligence

### Goals

1. Implement semantic similarity engine using OpenAI embeddings
2. Create coverage mapping service
3. Build gap analysis functionality
4. Implement evidence ranking
5. Add comprehensive logging

### Implementation Steps

**Step 1: Create Coverage Domain Models** (Duration: 4 hours)

Create `autoapply/domain/coverage.py`:

```python
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class RequirementPriority(str, Enum):
    MUST_HAVE = "must_have"
    NICE_TO_HAVE = "nice_to_have"

class EvidenceMatch(BaseModel):
    """Evidence that matches a requirement."""
    evidence_id: str
    evidence_text: str
    similarity_score: float  # 0.0-1.0
    source_type: str  # "experience", "project", "education"
    
class RequirementCoverage(BaseModel):
    """Coverage analysis for a single requirement."""
    requirement_text: str
    requirement_priority: RequirementPriority
    is_covered: bool
    best_match_score: float
    evidence_matches: List[EvidenceMatch]
    
class CoverageMap(BaseModel):
    """Complete coverage analysis for job-profile pair."""
    job_id: str
    profile_id: str
    overall_coverage_score: float
    must_have_coverage_score: float
    nice_to_have_coverage_score: float
    covered_requirements: List[RequirementCoverage]
    gap_requirements: List[RequirementCoverage]
```

**Step 2: Create Coverage Mapping Service** (Duration: 8 hours)

Create `autoapply/services/coverage_mapping_service.py`:

```python
import numpy as np
from openai import AsyncOpenAI
from typing import List, Tuple

class CoverageMappingService:
    """Semantic similarity engine for job-profile matching."""
    
    def __init__(self):
        # Initialize OpenAI client with credentials from environment
        # Note: API credentials loaded from environment variables
        openai_credential = os.getenv("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=openai_credential)
        self.model = "text-embedding-3-small"
    
    async def compute_coverage_map(
        self,
        extracted_jd: ExtractedJD,
        profile: Profile,
        job_id: str
    ) -> CoverageMap:
        """Compute coverage map using semantic similarity."""
        
        # Step 1: Extract evidence from profile
        evidence_items = self._extract_evidence(profile)
        
        # Step 2: Generate embeddings (batch for efficiency)
        requirement_embeddings = await self._batch_embed(
            [req.text for req in extracted_jd.must_have_requirements]
        )
        evidence_embeddings = await self._batch_embed(
            [ev.text for ev in evidence_items]
        )
        
        # Step 3: Compute similarity matrix
        similarity_matrix = self._cosine_similarity_matrix(
            requirement_embeddings,
            evidence_embeddings
        )
        
        # Step 4: Determine coverage per requirement
        covered_requirements = []
        gap_requirements = []
        
        for i, req in enumerate(extracted_jd.must_have_requirements):
            similarities = similarity_matrix[i]
            best_score = float(np.max(similarities))
            
            # Threshold: ≥0.75 for must-haves, ≥0.65 for nice-to-haves
            is_covered = best_score >= 0.75
            
            req_coverage = RequirementCoverage(
                requirement_text=req.text,
                requirement_priority=RequirementPriority.MUST_HAVE,
                is_covered=is_covered,
                best_match_score=best_score,
                evidence_matches=self._get_top_matches(
                    similarities, evidence_items, n=3
                )
            )
            
            if is_covered:
                covered_requirements.append(req_coverage)
            else:
                gap_requirements.append(req_coverage)
        
        return CoverageMap(
            job_id=job_id,
            profile_id=profile.id,
            overall_coverage_score=len(covered_requirements) / len(required),
            must_have_coverage_score=...,
            nice_to_have_coverage_score=...,
            covered_requirements=covered_requirements,
            gap_requirements=gap_requirements
        )
```

**Step 3: Implement Similarity Computation** (Duration: 4 hours)

```python
def _cosine_similarity_matrix(
    self, 
    embeddings_a: np.ndarray, 
    embeddings_b: np.ndarray
) -> np.ndarray:
    """Compute cosine similarity matrix between two sets of embeddings.
    
    Returns matrix of shape (len(a), len(b)) where each cell is similarity.
    """
    # Normalize vectors
    a_norm = embeddings_a / np.linalg.norm(embeddings_a, axis=1, keepdims=True)
    b_norm = embeddings_b / np.linalg.norm(embeddings_b, axis=1, keepdims=True)
    
    # Compute dot product (cosine similarity for normalized vectors)
    return np.dot(a_norm, b_norm.T)
```

### PROMPT TO SEND TO CLINE

```
You are implementing Sprint B: Coverage & Intelligence.

Working directory: autoapply/

Create the following files:
1. autoapply/domain/coverage.py - Coverage domain models (CoverageMap, RequirementCoverage, EvidenceMatch)
2. autoapply/services/coverage_mapping_service.py - Semantic similarity engine with OpenAI embeddings

Ensure:
- Use OpenAI text-embedding-3-small model ($0.02/1M tokens)
- Batch embed for efficiency (up to 2048 texts per request)
- Compute cosine similarity matrix (normalized dot product)
- Apply coverage thresholds: ≥0.75 for must-haves, ≥0.65 for nice-to-haves
- Extract top 3 evidence matches per requirement
- Implement gap analysis with severity levels
- Add comprehensive logging (debug, info, warning levels)
- Document all public methods with docstrings

Do NOT modify validators or other services yet.
```

### Acceptance Criteria

- [ ] Coverage domain models created with proper types
- [ ] Embedding service uses batch API for efficiency
- [ ] Cosine similarity computation is numerically stable
- [ ] Coverage thresholds applied correctly (0.75/0.65)
- [ ] Top N evidence ranking works
- [ ] Gap requirements identified with severity
- [ ] Logging messages at appropriate levels
- [ ] All methods have docstrings with args/returns

### Task Tracking

| Task | Owner | Status | QA Notes |
|------|-------|--------|----------|
| Create coverage models | Dev | ☐ TODO | |
| Implement embedding service | Dev | ☐ TODO | |
| Add similarity computation | Dev | ☐ TODO | |
| Implement coverage logic | Dev | ☐ TODO | |
| Add gap analysis | Dev | ☐ TODO | |
| Code review | Lead | ☐ TODO | |

---

## Sprint C: Generation & Verification

### Goals

1. Implement provenance-backed bullet generation
2. Create verification service with component-level validation
3. Integrate AMOT parsing with verification
4. Build bullet categorization logic (proposed vs suggested edits)
5. Add evidence linking and tracking

### Implementation Steps

**Step 1: Create Verification Service** (Duration: 8 hours)

Create `autoapply/services/verification_service.py`:

```python
from typing import List, Dict
from openai import AsyncOpenAI

class VerificationService:
    """Component-level verification of resume bullets against evidence."""
    
    async def verify_bullet(
        self,
        bullet_text: str,
        evidence_items: List[EvidenceSpan],
        evidence_ids_claimed: List[str]
    ) -> BulletVerificationResult:
        """Verify each AMOT component against evidence.
        
        Verification Rules:
        - Action: Semantic matching OK (Led ≈ Managed)
        - Metric: Exact match required (35% ≠ 40%)
        - Outcome: Semantic matching OK (revenue growth ≈ increased sales)
        - Tool: Exact mention required (cannot infer)
        
        Thresholds:
        - 100% (4/4): Fully verified → ACCEPT
        - 75%+ (3/4): Mostly verified → ACCEPT with note
        - 50-74% (2/4): Partially verified → FLAG for review
        - <50% (0-1/4): Insufficiently verified → REJECT
        """
        # Parse AMOT components
        components = parse_amot(bullet_text)
        
        # Verify each component
        action_verified = await self._verify_semantic(
            components["action"], evidence_items, "action"
        )
        metric_verified = await self._verify_exact(
            components["metric"], evidence_items
        )
        outcome_verified = await self._verify_semantic(
            components["outcome"], evidence_items, "outcome"
        )
        tool_verified = await self._verify_exact(
            components["tool"], evidence_items
        )
        
        # Calculate verification rate
        verified_count = sum([
            action_verified.is_verified,
            metric_verified.is_verified,
            outcome_verified.is_verified,
            tool_verified.is_verified
        ])
        verification_rate = verified_count / 4.0
        
        # Determine recommendation
        if verification_rate >= 0.75:
            recommendation = "ACCEPT"
        elif verification_rate >= 0.50:
            recommendation = "FLAG"
        else:
            recommendation = "REJECT"
        
        return BulletVerificationResult(
            bullet_text=bullet_text,
            verification_rate=verification_rate,
            recommendation=recommendation,
            component_results={
                "action": action_verified,
                "metric": metric_verified,
                "outcome": outcome_verified,
                "tool": tool_verified
            }
        )
```

**Step 2: Create Enhanced Bullet Service** (Duration: 10 hours)

Create `autoapply/services/bullet_service_enhanced.py`:

```python
class EnhancedBulletService:
    """Provenance-backed bullet generation with verification."""
    
    async def generate_with_provenance(
        self,
        coverage_map: CoverageMap,
        profile: Profile,
        max_bullets_per_role: int = 5
    ) -> BulletGenerationResult:
        """Generate bullets with complete provenance tracking.
        
        Process:
        1. Get covered requirements (prioritize must-haves)
        2. For each requirement:
           a. Get top 3 evidence matches
           b. Generate bullet with Claude/GPT-4
           c. Link to evidence IDs
           d. Verify against evidence
           e. Categorize based on verification
        
        Returns bullets categorized as:
        - Proposed: ≥75% verified (ready for resume)
        - Suggested Edits: <75% verified (needs user approval)
        """
        covered_requirements = coverage_map.covered_requirements[:max_bullets_per_role]
        
        proposed_bullets = []
        suggested_edits = []
        
        for req_coverage in covered_requirements:
            # Get evidence for this requirement
            top_evidence = req_coverage.evidence_matches[:3]
            
            # Generate bullet with Claude
            bullet_text = await self._generate_bullet(
                requirement=req_coverage.requirement_text,
                evidence_texts=[e.evidence_text for e in top_evidence]
            )
            
            # Verify bullet
            verification_result = await self.verification_service.verify_bullet(
                bullet_text=bullet_text,
                evidence_items=all_evidence,
                evidence_ids_claimed=[e.evidence_id for e in top_evidence]
            )
            
            # Create provenance bullet
            bullet = ProvenanceBullet(
                text=bullet_text,
                requirement_text=req_coverage.requirement_text,
                evidence_ids=[e.evidence_id for e in top_evidence],
                similarity_scores=[e.similarity_score for e in top_evidence],
                verification_result=verification_result
            )
            
            # Categorize
            if verification_result.recommendation == "ACCEPT":
                proposed_bullets.append(bullet)
            else:
                suggested_edits.append(bullet)
        
        return BulletGenerationResult(
            proposed_bullets=proposed_bullets,
            suggested_edits=suggested_edits
        )
```

### PROMPT TO SEND TO CLINE

```
You are implementing Sprint C: Generation & Verification.

Working directory: autoapply/

Create the following files:
1. autoapply/services/verification_service.py - Component-level verification with GPT-4
2. autoapply/services/bullet_service_enhanced.py - Provenance-backed bullet generation

Ensure:
- Verification uses GPT-4 for semantic checks (action/outcome)
- Metric verification is exact match only (35% ≠ 40%)
- Tool verification requires exact mention
- Thresholds: 100%→ACCEPT, 75%+→ACCEPT with note, 50-74%→FLAG, <50%→REJECT
- Bullet generation uses Claude 3.5 Sonnet
- Evidence-only prompts (no invention or exaggeration)
- AMOT format enforced in generation
- Complete provenance linking (evidence IDs + similarity scores)
- Categorization: proposed (≥75%) vs suggested edits (<75%)

Run verification tests to ensure thresholds work correctly.
```

### Acceptance Criteria

- [ ] Verification service implements component-level checks
- [ ] Action/outcome use semantic matching (GPT-4)
- [ ] Metric/tool use exact matching
- [ ] Thresholds applied correctly (100%, 75%, 50%)
- [ ] Bullet generation uses evidence-only prompts
- [ ] AMOT format validated before proposing
- [ ] Provenance tracking complete (IDs + scores)
- [ ] Categorization logic works (proposed vs suggested)
- [ ] All methods documented with docstrings

### Task Tracking

| Task | Owner | Status | QA Notes |
|------|-------|--------|----------|
| Create verification service | Dev | ☐ TODO | |
| Implement component checks | Dev | ☐ TODO | |
| Create bullet service | Dev | ☐ TODO | |
| Add provenance tracking | Dev | ☐ TODO | |
| Implement categorization | Dev | ☐ TODO | |
| Integration test | QA | ☐ TODO | |
| Code review | Lead | ☐ TODO | |

---

## Sprint D: Integration & Testing

### Goals

1. Create end-to-end integration tests
2. Build test fixtures (sample JDs and profiles)
3. Validate complete pipeline flow
4. Test edge cases (low coverage, career changers, errors)
5. Establish performance benchmarks
6. Create comprehensive test documentation

### Implementation Steps

**Step 1: Create Integration Test Suite** (Duration: 6 hours)

Create `tests/integration/test_e2e_pipeline.py`:

```python
import pytest
import time

@pytest.mark.asyncio
async def test_complete_pipeline_happy_path():
    """Test full pipeline with strong candidate-job match."""
    # Setup
    jd_service = JDExtractionService()
    coverage_service = CoverageMappingService()
    bullet_service = EnhancedBulletService()
    
    # Step 1: Extract JD
    extraction_result = await jd_service.extract_job_description(SAMPLE_JD_TEXT)
    assert extraction_result.extracted_jd is not None
    
    # Step 2: Map coverage
    coverage_result = await coverage_service.compute_coverage_map(
        extracted_jd=extraction_result.extracted_jd,
        profile=sample_profile,
        job_id="test-job-001"
    )
    assert coverage_result.coverage_map.must_have_coverage_score > 0.70
    
    # Step 3: Generate bullets
    bullet_result = await bullet_service.generate_with_provenance(
        coverage_map=coverage_result.coverage_map,
        profile=sample_profile
    )
    assert len(bullet_result.proposed_bullets) > 0
    
    # Step 4: Verify provenance
    for bullet in bullet_result.proposed_bullets:
        assert len(bullet.evidence_ids) > 0
        assert bullet.verification_rate >= 0.75

@pytest.mark.asyncio
async def test_performance_benchmark():
    """Test that pipeline completes within 20s target."""
    start = time.time()
    
    # Run full pipeline
    result = await run_full_pipeline(SAMPLE_JD_TEXT, sample_profile)
    
    elapsed = time.time() - start
    assert elapsed < 20.0, f"Pipeline took {elapsed}s (target: <20s)"
```

**Step 2: Create Test Fixtures** (Duration: 4 hours)

Create `tests/fixtures/sample_jds.py` and `tests/fixtures/sample_profiles.py`

### PROMPT TO SEND TO CLINE

```
You are implementing Sprint D: Integration & Testing.

Working directory: tests/

Create the following files:
1. tests/integration/test_e2e_pipeline.py - Full integration test suite
2. tests/fixtures/sample_jds.py - Diverse sample job descriptions
3. tests/fixtures/sample_profiles.py - Sample candidate profiles

Test scenarios:
- Happy path: Strong candidate-job match (>70% coverage expected)
- Low coverage: Junior candidate for senior role (<50% coverage expected)
- Career changer: Transferable skills (mixed coverage expected)
- Error handling: Invalid inputs handled gracefully
- Performance: Full pipeline <20s

Ensure:
- All tests use @pytest.mark.asyncio decorator
- Fixtures include diverse scenarios (tech, sales, career changers)
- Performance benchmarks captured and logged
- Edge cases covered (empty profiles, vague JDs)
- All assertions have clear failure messages

Run tests: pytest tests/integration/test_e2e_pipeline.py -v
```

### Acceptance Criteria

- [ ] Integration tests cover happy path scenario
- [ ] Low coverage scenario test created
- [ ] Career changer test created
- [ ] Error handling test created
- [ ] Performance benchmark test passes (<20s)
- [ ] Test fixtures diverse and realistic
- [ ] All tests pass: `pytest tests/integration/ -v`
- [ ] Test coverage report shows >80% coverage

### Task Tracking

| Task | Owner | Status | QA Notes |
|------|-------|--------|----------|
| Create integration test suite | Dev | ☐ TODO | |
| Add test fixtures | Dev | ☐ TODO | |
| Implement performance tests | Dev | ☐ TODO | |
| Run full test suite | QA | ☐ TODO | |
| Generate coverage report | QA | ☐ TODO | |
| Code review | Lead | ☐ TODO | |

---

## Sprint E: Documentation & Launch

### Goals

1. Create comprehensive user documentation
2. Build deployment guides
3. Write API documentation
4. Create troubleshooting guides  
5. Prepare launch materials

### Implementation Steps

**Step 1: User Documentation** (Duration: 6 hours)

Create documentation covering:
- Getting started guide
- Feature documentation
- Configuration reference
- Best practices
- FAQs

**Step 2: API Documentation** (Duration: 4 hours)

Document all public APIs with:
- Function signatures
- Parameter descriptions
- Return value specifications
- Example usage
- Error handling

**Step 3: Deployment Guide** (Duration: 3 hours)

Create deployment documentation:
- System requirements
- Installation steps
- Configuration guide
- Security considerations
- Monitoring setup

### PROMPT TO SEND TO CLINE

```
You are implementing Sprint E: Documentation & Launch.

Working directory: docs/

Create the following documentation files:
1. docs/user_guide.md - End-user documentation
2. docs/api_reference.md - API documentation for developers
3. docs/deployment_guide.md - Production deployment guide
4. docs/troubleshooting.md - Common issues and solutions

Ensure all documentation includes:
- Clear examples with code snippets
- Screenshots where applicable
- Links to related sections
- Version information (v0.9)
- Last updated timestamps

Use plain English - avoid jargon where possible.
Reference .env.sample, never literal API keys.
```

### Acceptance Criteria

- [ ] User guide covers all major features
- [ ] API reference documents all public methods
- [ ] Deployment guide includes security considerations
- [ ] Troubleshooting guide addresses common issues
- [ ] All code examples are tested and work
- [ ] Documentation reviewed for clarity
- [ ] Links between docs work correctly

### Task Tracking

| Task | Owner | Status | QA Notes |
|------|-------|--------|----------|
| Write user guide | Tech Writer | ☐ TODO | |
| Document APIs | Dev | ☐ TODO | |
| Create deployment guide | DevOps | ☐ TODO | |
| Write troubleshooting guide | Support | ☐ TODO | |
| Review documentation | All | ☐ TODO | |
| Publish docs | Lead | ☐ TODO | |

---

## Glossary

### A

**AMOT (Action-Metric-Outcome-Tool)**
- **Plain English:** A resume bullet format requiring four components: what you did (action), how much (metric), what resulted (outcome), and how you did it (tool).
- **Why It Matters:** Ensures resume bullets are specific, quantifiable, and verifiable rather than vague claims.
- **Where in UX:** Users see AMOT badges on each bullet showing which components are verified.
- **Where in Code:** `autoapply/domain/validators/amot.py` - parsing and validation logic.

**Anti-Hallucination**
- **Plain English:** Design principle ensuring AI only generates claims that have supporting evidence, never inventing or exaggerating.
- **Why It Matters:** Prevents false claims on resumes that could harm user credibility.
- **Where in UX:** "Evidence-only" badge shown on proposed bullets.
- **Where in Code:** `autoapply/services/bullet_service_enhanced.py` - evidence-only generation prompts.

### C

**Component-Level Verification**
- **Plain English:** Checking each part of a resume bullet (action, metric, outcome, tool) independently against candidate's evidence.
- **Why It Matters:** Provides granular feedback on which parts of a claim are supported vs. which need user approval.
- **Where in UX:** Verification breakdown showing ✓ or ✗ for each component.
- **Where in Code:** `autoapply/services/verification_service.py` - individual component checks.

**Coverage Map**
- **Plain English:** Analysis showing which job requirements the candidate has evidence for and which are gaps.
- **Why It Matters:** Shows candidate's match strength and where to add evidence for better results.
- **Where in UX:** Circular progress chart showing must-have coverage percentage.
- **Where in Code:** `autoapply/domain/coverage.py` - CoverageMap model.

**Cosine Similarity**
- **Plain English:** Mathematical measure (0.0-1.0) of how similar two pieces of text are semantically.
- **Why It Matters:** Determines which of candidate's experiences best match each job requirement.
- **Where in UX:** Shown as "match strength" percentage next to evidence.
- **Where in Code:** `autoapply/services/coverage_mapping_service.py` - similarity computation.

### E

**Evidence**
- **Plain English:** Specific examples from candidate's past work (projects, experiences, education) that support resume claims.
- **Why It Matters:** Forms the foundation of all generated content - ensures verifiability.
- **Where in UX:** Clickable links showing "Based on: [evidence text]".
- **Where in Code:** `autoapply/domain/profile.py` - EvidenceSpan model.

**Evidence ID**
- **Plain English:** Unique identifier (UUID) linking each resume bullet back to specific source evidence.
- **Why It Matters:** Enables complete audit trail for compliance and user trust.
- **Where in UX:** Hover tooltip showing evidence ID for traceability.
- **Where in Code:** All ProvenanceBullet instances include evidence_ids list.

### G

**Gap Analysis**
- **Plain English:** Identification of job requirements the candidate doesn't have clear evidence for.
- **Why It Matters:** Helps candidate understand qualification gaps and what to add to profile.
- **Where in UX:** "Missing Requirements" section with severity levels (critical/medium/low).
- **Where in Code:** `autoapply/services/coverage_mapping_service.py` - gap identification logic.

### P

**Provenance**
- **Plain English:** Complete history of where a resume bullet came from (which job requirement → which evidence → verification status).
- **Why It Matters:** Provides transparency and trust; enables complete audit trail.
- **Where in UX:** Provenance card showing full chain when user clicks bullet.
- **Where in Code:** `autoapply/services/bullet_service_enhanced.py` - ProvenanceBullet class.

**Proposed Bullets**
- **Plain English:** Resume bullets that are ≥75% verified and ready to use without modification.
- **Why It Matters:** These are "safe to include" - user can accept with confidence.
- **Where in UX:** Green cards labeled "Proposed" in resume preview.
- **Where in Code:** BulletGenerationResult.proposed_bullets list.

### S

**Semantic Similarity**
- **Plain English:** Understanding that two phrases can mean the same thing even if worded differently (e.g., "Led team" ≈ "Managed team").
- **Why It Matters:** Allows system to recognize candidate's experience even when described differently than job requirement.
- **Where in UX:** Shown as high similarity scores (>0.75) between different wordings.
- **Where in Code:** `autoapply/services/coverage_mapping_service.py` - embedding comparisons.

**Similarity Score**
- **Plain English:** Number from 0.0 to 1.0 indicating how closely candidate's evidence matches a job requirement (1.0 = perfect match).
- **Why It Matters:** Determines coverage decisions (≥0.75 = covered for must-haves).
- **Where in UX:** Progress bars or percentages next to each requirement.
- **Where in Code:** EvidenceMatch.similarity_score field.

**Suggested Edits**
- **Plain English:** Resume bullets that are <75% verified and need user review/approval before including.
- **Why It Matters:** Protects user from including unverifiable claims while still surfacing possibilities.
- **Where in UX:** Yellow cards labeled "Suggested Edit" with explanation of what isn't verified.
- **Where in Code:** BulletGenerationResult.suggested_edits list.

### T

**Thresholds**
- **Plain English:** Numeric cutoff points used to make decisions (e.g., 0.75 similarity = covered, 75% verification = proposed).
- **Why It Matters:** Ensures consistent, conservative decision-making across the system.
- **Where in UX:** Shown in settings/documentation explaining system behavior.
- **Where in Code:** Constants in coverage_mapping_service.py and verification_service.py.

### V

**Verification Rate**
- **Plain English:** Percentage of AMOT components (0-100%) that have supporting evidence (e.g., 75% = 3 out of 4 components verified).
- **Why It Matters:** Determines if bullet is "proposed" (≥75%) or "suggested edit" (<75%).
- **Where in UX:** Percentage badge on each bullet with color coding (green/yellow/red).
- **Where in Code:** BulletVerificationResult.verification_rate field.

---

## Document End

**Version:** 0.9.0  
**Total Pages:** ~50  
**Last Updated:** November 2025  
**Maintained By:** AutoApply Engineering Team  

For questions or updates, please refer to the project repository or contact the technical lead.

---

## Visual Placeholders

This document references three visuals that will be rendered as diagrams:

1. **[Visual 1: Architecture Diagram]** - Shows complete E2E pipeline from JD to Resume
2. **[Visual 2: Provenance Card]** - Shows provenance tracking with evidence links  
3. **[Visual 3: Preview/Approve Flow]** - Shows user workflow for reviewing bullets

These visuals will be rendered using Mermaid/PlantUML and embedded as images in the exported versions.

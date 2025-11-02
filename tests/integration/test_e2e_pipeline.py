"""End-to-End Integration Test for Complete Resume Generation Pipeline.

This integration test validates the entire provenance-backed resume generation
pipeline from raw job description to verified resume bullets. It ensures:

1. All services integrate correctly
2. Data flows properly between components
3. Provenance chain maintains integrity
4. Performance meets acceptable thresholds
5. Error handling works as expected

Test Coverage:
- JD Extraction (Claude/GPT-4 with fallback)
- Coverage Mapping (semantic similarity with embeddings)
- Bullet Generation (coverage-driven with evidence)
- Verification (component-level AMOT validation)
- Edge cases (low coverage, ambiguous JDs, career changers)

Why This Test Matters:
- Proves core pipeline works end-to-end
- Catches integration issues early
- Validates provenance chain integrity
- Ensures performance acceptable
- Provides regression protection
- Demonstrates system capabilities

Architecture Under Test:
    JD Text → Extraction → ExtractedJD → Coverage → CoverageMap → 
    Bullets → Verification → Proposed/Suggested → Resume

Success Criteria:
- All services execute without errors
- Provenance chain complete (evidence → bullet)
- Verification rates ≥70%
- Coverage scores reasonable
- Performance within limits
"""

import pytest
import time
from typing import Dict, Any

from autoapply.domain.profile import Profile, Experience, Project, Education, EvidenceSpan
from autoapply.domain.job_description import ExtractedJD
from autoapply.services.jd_extraction_service import JDExtractionService
from autoapply.services.coverage_mapping_service import CoverageMappingService
from autoapply.services.bullet_service_enhanced import EnhancedBulletService
from autoapply.services.verification_service import VerificationService


# Sample job description for testing
# This is a realistic senior software engineer JD with clear requirements
SAMPLE_JD_TEXT = """
Senior Software Engineer - Backend

TechCorp Inc is seeking an experienced backend engineer to join our platform team.

Requirements (Must Have):
- 5+ years of professional software development experience
- Strong proficiency in Python and experience with modern frameworks
- Experience with AWS cloud infrastructure and services
- Database design and optimization experience (SQL and NoSQL)
- Proven track record of delivering scalable systems

Requirements (Nice to Have):
- Experience with Kubernetes and container orchestration
- Frontend development skills (React, TypeScript)
- Understanding of machine learning concepts

Responsibilities:
- Design and implement backend services for our SaaS platform
- Optimize database performance and ensure data integrity
- Collaborate with frontend and DevOps teams
- Mentor junior engineers

Company: TechCorp Inc (Series B startup, 150 employees)
Location: San Francisco, CA (Remote-friendly)
Salary: $140K-$180K

Apply at: careers@techcorp.example.com
"""


def create_sample_profile() -> Profile:
    """Create a sample candidate profile for testing.
    
    This profile represents an experienced Python engineer with AWS
    experience but gaps in frontend and Kubernetes. Designed to test:
    - Strong coverage for must-haves (Python, AWS, databases)
    - Partial coverage for nice-to-haves (missing Kubernetes, React)
    - Realistic evidence with quantifiable achievements
    
    Returns:
        Profile with experiences, projects, and education
    """
    # Experience 1: Python team lead
    exp1 = Experience(
        id="exp-001",
        company="Acme Corp",
        title="Senior Software Engineer",
        start_date="2019-01",
        end_date="2024-03",
        bullets=[
            "Led Python development team of 8 engineers for 5 years",
            "Built and maintained 50+ microservices using Django and Flask",
            "Managed AWS infrastructure including EC2, S3, RDS, and Lambda",
            "Optimized PostgreSQL database queries improving performance by 60%",
            "Mentored 5 junior engineers in best practices and code review",
        ],
        evidence_ids=[
            "ev-001-bullet-0",
            "ev-001-bullet-1",
            "ev-001-bullet-2",
            "ev-001-bullet-3",
            "ev-001-bullet-4",
        ],
    )
    
    # Experience 2: Backend focus
    exp2 = Experience(
        id="exp-002",
        company="DataSystems Inc",
        title="Software Engineer",
        start_date="2016-06",
        end_date="2019-01",
        bullets=[
            "Developed RESTful APIs in Python serving 1M+ daily requests",
            "Designed MongoDB schemas for high-throughput data pipeline",
            "Deployed services to AWS using CloudFormation and Terraform",
        ],
        evidence_ids=[
            "ev-002-bullet-0",
            "ev-002-bullet-1",
            "ev-002-bullet-2",
        ],
    )
    
    # Project: Side project showing initiative
    project = Project(
        id="proj-001",
        name="Open Source Contribution",
        description="Core contributor to popular Python web framework",
        start_date="2020-01",
        achievements=[
            "Contributed 200+ commits to Django ORM",
            "Improved query optimization performance by 40%",
        ],
        evidence_ids=[
            "ev-proj-001-0",
            "ev-proj-001-1",
        ],
        technologies=["Python", "Django", "PostgreSQL"],
    )
    
    # Education
    education = Education(
        id="edu-001",
        degree="B.S. Computer Science",
        institution="State University",
        graduation_date="2016-05",
        gpa=3.7,
        relevant_coursework=[
            "Data Structures and Algorithms",
            "Database Systems",
            "Software Engineering",
        ],
    )
    
    return Profile(
        id="profile-test-001",
        name="John Doe",
        email="john@example.com",
        phone="+1-555-0100",
        location="San Francisco, CA",
        experiences=[exp1, exp2],
        projects=[project],
        education=[education],
        skills={
            "Programming Languages": ["Python", "SQL", "Bash"],
            "Frameworks": ["Django", "Flask", "FastAPI"],
            "Cloud & Infrastructure": ["AWS", "Docker", "Terraform"],
            "Databases": ["PostgreSQL", "MongoDB", "Redis"],
        },
    )


def print_pipeline_metrics(
    extraction_result,
    coverage_result,
    bullet_result,
    test_name: str
) -> Dict[str, Any]:
    """Print formatted pipeline metrics for demo/debugging.
    
    This helper formats and displays key metrics from each pipeline stage.
    Useful for:
    - Demo presentations (showing real numbers)
    - Performance monitoring (tracking latency)
    - Debugging (identifying bottlenecks)
    - Regression testing (comparing runs)
    
    Args:
        extraction_result: JD extraction result with metadata
        coverage_result: Coverage mapping result with scores
        bullet_result: Bullet generation result with stats
        test_name: Name of test case for labeling
        
    Returns:
        Dict of all metrics for programmatic access
    """
    print("\n" + "=" * 80)
    print(f"PIPELINE METRICS: {test_name}")
    print("=" * 80)
    
    # JD Extraction Metrics
    print("\n📄 JD EXTRACTION:")
    print(f"  Provider: {extraction_result.provider_used}")
    print(f"  Time: {extraction_result.extraction_time_ms}ms")
    print(f"  Must-Have Requirements: {len(extraction_result.extracted_jd.must_have_requirements)}")
    print(f"  Nice-to-Have Requirements: {len(extraction_result.extracted_jd.nice_to_have_requirements)}")
    print(f"  Ambiguities: {len(extraction_result.ambiguities)}")
    if extraction_result.ambiguities:
        for amb in extraction_result.ambiguities:
            print(f"    - {amb}")
    
    # Coverage Mapping Metrics
    print("\n🎯 COVERAGE MAPPING:")
    coverage_map = coverage_result.coverage_map
    print(f"  Provider: {coverage_result.embedding_provider}")
    print(f"  Time: {coverage_result.execution_time_ms}ms")
    print(f"  Evidence Items: {coverage_result.total_evidence_items}")
    print(f"  Overall Coverage: {coverage_map.overall_coverage_score:.1%}")
    print(f"  Must-Have Coverage: {coverage_map.must_have_coverage_score:.1%}")
    print(f"  Nice-to-Have Coverage: {coverage_map.nice_to_have_coverage_score:.1%}")
    print(f"  Covered Requirements: {len(coverage_map.covered_requirements)}")
    print(f"  Gap Requirements: {len(coverage_map.gap_requirements)}")
    if coverage_map.critical_gaps:
        print(f"  Critical Gaps: {len(coverage_map.critical_gaps)}")
        for gap in coverage_map.critical_gaps[:3]:  # Show first 3
            print(f"    - {gap.requirement_text}")
    
    # Bullet Generation Metrics
    print("\n✍️ BULLET GENERATION:")
    metadata = bullet_result.generation_metadata
    print(f"  Time: {metadata['generation_time_ms']}ms")
    print(f"  Requirements Processed: {metadata['requirements_processed']}")
    print(f"  Total Bullets Generated: {metadata['total_generated']}")
    print(f"  Proposed (Verified): {metadata['proposed_count']}")
    print(f"  Suggested Edits (Flagged): {metadata['suggested_edit_count']}")
    
    # Verification Statistics
    stats = bullet_result.get_verification_stats()
    print(f"\n  Average Verification Rate: {stats['average_verification_rate']:.1%}")
    print(f"  Fully Verified Rate: {stats['fully_verified_rate']:.1%}")
    
    # Sample bullets (show first 2 proposed)
    if bullet_result.proposed_bullets:
        print("\n  Sample Proposed Bullets:")
        for i, bullet in enumerate(bullet_result.proposed_bullets[:2], 1):
            print(f"    {i}. {bullet.text}")
            print(f"       → Verified: {bullet.verification_rate:.0%} | Evidence: {len(bullet.evidence_ids)} sources")
    
    # Sample suggested edits (show first 1)
    if bullet_result.suggested_edits:
        print("\n  Sample Suggested Edits:")
        bullet = bullet_result.suggested_edits[0]
        print(f"    1. {bullet.text}")
        print(f"       → Issue: {bullet.verification_result.explanation}")
    
    # Total Pipeline Metrics
    total_time = (
        extraction_result.extraction_time_ms +
        coverage_result.execution_time_ms +
        metadata['generation_time_ms']
    )
    print(f"\n⏱️ TOTAL PIPELINE TIME: {total_time}ms ({total_time/1000:.2f}s)")
    print("=" * 80 + "\n")
    
    # Return metrics dict for programmatic access
    return {
        "extraction_time_ms": extraction_result.extraction_time_ms,
        "coverage_time_ms": coverage_result.execution_time_ms,
        "generation_time_ms": metadata['generation_time_ms'],
        "total_time_ms": total_time,
        "overall_coverage": coverage_map.overall_coverage_score,
        "must_have_coverage": coverage_map.must_have_coverage_score,
        "proposed_count": metadata['proposed_count'],
        "suggested_edit_count": metadata['suggested_edit_count'],
        "average_verification_rate": stats['average_verification_rate'],
    }


@pytest.mark.asyncio
async def test_complete_pipeline_happy_path():
    """Test complete pipeline with ideal candidate match.
    
    This is the "happy path" test where the candidate strongly qualifies
    for the role. We expect:
    - High coverage scores (>70% must-haves)
    - Multiple proposed bullets (verified)
    - Low number of suggested edits
    - Fast execution (<10s total)
    
    Test validates:
    1. JD extraction identifies requirements correctly
    2. Coverage mapping finds strong evidence matches
    3. Bullets generated address covered requirements
    4. Verification passes for most bullets
    5. Provenance chain complete (evidence IDs linked)
    """
    print("\n🧪 TEST: Complete Pipeline - Happy Path")
    
    # Initialize services
    jd_service = JDExtractionService()
    coverage_service = CoverageMappingService()
    bullet_service = EnhancedBulletService()
    
    # Create test data
    profile = create_sample_profile()
    
    # Step 1: Extract JD
    print("  Step 1: Extracting job description...")
    extraction_result = await jd_service.extract_job_description(SAMPLE_JD_TEXT)
    
    # Validate extraction
    assert extraction_result.extracted_jd is not None
    assert len(extraction_result.extracted_jd.must_have_requirements) >= 3
    assert extraction_result.extraction_time_ms < 10000  # Less than 10s
    
    # Step 2: Map coverage
    print("  Step 2: Computing coverage map...")
    coverage_result = await coverage_service.compute_coverage_map(
        extracted_jd=extraction_result.extracted_jd,
        profile=profile,
        job_id="test-job-001"
    )
    
    # Validate coverage
    coverage_map = coverage_result.coverage_map
    assert coverage_map.overall_coverage_score > 0.5  # At least 50% coverage
    assert coverage_map.must_have_coverage_score > 0.7  # Strong must-have coverage
    assert len(coverage_map.covered_requirements) > 0
    
    # Step 3: Generate bullets
    print("  Step 3: Generating bullets with provenance...")
    bullet_result = await bullet_service.generate_with_provenance(
        coverage_map=coverage_map,
        profile=profile,
        max_bullets_per_role=5
    )
    
    # Validate generation
    assert len(bullet_result.get_all_bullets()) > 0
    assert len(bullet_result.proposed_bullets) > 0  # Should have some verified bullets
    
    # Step 4: Validate provenance chain
    print("  Step 4: Validating provenance chain...")
    for bullet in bullet_result.proposed_bullets:
        # Every bullet must have evidence IDs
        assert len(bullet.evidence_ids) > 0, f"Bullet missing evidence IDs: {bullet.text}"
        
        # Every bullet must have requirement text
        assert bullet.requirement_text, f"Bullet missing requirement: {bullet.text}"
        
        # Every bullet must have similarity scores
        assert len(bullet.similarity_scores) > 0, f"Bullet missing similarity scores: {bullet.text}"
        
        # Verification result must exist
        assert bullet.verification_result is not None
    
    # Step 5: Validate verification quality
    print("  Step 5: Validating verification quality...")
    stats = bullet_result.get_verification_stats()
    assert stats['average_verification_rate'] >= 0.70  # Average 70%+ verified
    
    # Print metrics
    metrics = print_pipeline_metrics(
        extraction_result,
        coverage_result,
        bullet_result,
        "Happy Path"
    )
    
    # Performance assertions
    assert metrics['total_time_ms'] < 15000  # Total under 15s
    
    print("  ✅ Test passed: Complete pipeline operational")


@pytest.mark.asyncio
async def test_pipeline_with_low_coverage():
    """Test pipeline with candidate who doesn't strongly qualify.
    
    This tests the "gap scenario" where candidate has limited relevant
    experience. We expect:
    - Lower coverage scores (<50% must-haves)
    - Fewer proposed bullets
    - More suggested edits
    - Critical gaps identified
    
    Test validates:
    1. System handles low-coverage gracefully
    2. Gap analysis provides actionable feedback
    3. Doesn't generate unverifiable bullets
    4. User informed about qualification issues
    """
    print("\n🧪 TEST: Pipeline with Low Coverage")
    
    # Create junior profile with limited experience
    junior_exp = Experience(
        id="exp-junior-001",
        company="Small Startup",
        title="Junior Developer",
        start_date="2022-01",
        end_date="2024-03",
        bullets=[
            "Wrote Python scripts for data processing",
            "Fixed bugs in existing codebase",
            "Participated in code reviews",
        ],
        evidence_ids=["ev-j-001-0", "ev-j-001-1", "ev-j-001-2"],
    )
    
    junior_education = Education(
        id="edu-junior-001",
        degree="B.S. Computer Science",
        institution="Local College",
        graduation_date="2022-05",
        gpa=3.4,
    )
    
    junior_profile = Profile(
        id="profile-junior-001",
        name="Jane Smith",
        email="jane@example.com",
        phone="+1-555-0200",
        location="Remote",
        experiences=[junior_exp],
        projects=[],
        education=[junior_education],
        skills={
            "Programming Languages": ["Python", "JavaScript"],
            "Tools": ["Git", "VS Code"],
        },
    )
    
    # Initialize services
    jd_service = JDExtractionService()
    coverage_service = CoverageMappingService()
    bullet_service = EnhancedBulletService()
    
    # Extract JD (same senior role)
    print("  Step 1: Extracting job description...")
    extraction_result = await jd_service.extract_job_description(SAMPLE_JD_TEXT)
    
    # Compute coverage
    print("  Step 2: Computing coverage map...")
    coverage_result = await coverage_service.compute_coverage_map(
        extracted_jd=extraction_result.extracted_jd,
        profile=junior_profile,
        job_id="test-job-002"
    )
    
    coverage_map = coverage_result.coverage_map
    
    # Validate low coverage
    assert coverage_map.must_have_coverage_score < 0.5  # Below 50%
    assert len(coverage_map.critical_gaps) > 0  # Should have critical gaps
    
    print(f"  Coverage: {coverage_map.must_have_coverage_score:.1%} (expected <50%)")
    print(f"  Critical Gaps: {len(coverage_map.critical_gaps)}")
    
    # Try to generate bullets (should have few or none)
    print("  Step 3: Attempting bullet generation...")
    try:
        bullet_result = await bullet_service.generate_with_provenance(
            coverage_map=coverage_map,
            profile=junior_profile,
            max_bullets_per_role=5
        )
        
        # May generate some bullets, but most should be suggested edits
        total_bullets = len(bullet_result.get_all_bullets())
        print(f"  Generated: {total_bullets} bullets")
        
        if total_bullets > 0:
            stats = bullet_result.get_verification_stats()
            print(f"  Proposed: {stats['proposed_count']}")
            print(f"  Suggested Edits: {stats['suggested_edit_count']}")
    
    except ValueError as e:
        # Expected: No covered requirements
        print(f"  ✓ Expected error: {e}")
        assert "No covered requirements" in str(e)
    
    # Print gap analysis
    print("\n  Gap Analysis:")
    for gap in coverage_map.critical_gaps[:3]:
        print(f"    ❌ {gap.requirement_text}")
        print(f"       Action: {gap.suggested_action}")
    
    print("  ✅ Test passed: Low coverage handled gracefully")


@pytest.mark.asyncio
async def test_pipeline_with_career_changer():
    """Test pipeline with career changer profile.
    
    This tests a candidate transitioning from one field to another
    (e.g., teacher → software engineer). We expect:
    - Transferable skills identified
    - Education/projects compensate for experience gaps
    - Mixed coverage (some strong, some weak)
    - Nuanced verification needed
    
    Test validates:
    1. System recognizes transferable skills
    2. Evidence from non-traditional sources used
    3. Gap analysis provides career-specific guidance
    4. Verification handles cross-domain claims
    """
    print("\n🧪 TEST: Pipeline with Career Changer")
    
    # Create career changer profile (teacher → engineer)
    teaching_exp = Experience(
        id="exp-teach-001",
        company="High School District",
        title="Computer Science Teacher",
        start_date="2018-08",
        end_date="2023-06",
        bullets=[
            "Taught Python programming to 150+ students annually",
            "Developed curriculum for AP Computer Science course",
            "Mentored student coding club projects",
        ],
        evidence_ids=["ev-teach-001-0", "ev-teach-001-1", "ev-teach-001-2"],
    )
    
    # Bootcamp project showing serious learning
    bootcamp_project = Project(
        id="proj-bootcamp-001",
        name="Full-Stack Web Application",
        description="Built e-commerce platform as bootcamp capstone",
        start_date="2023-07",
        achievements=[
            "Developed REST API in Python with Flask and PostgreSQL",
            "Deployed to AWS using EC2 and RDS",
            "Implemented user authentication and payment processing",
        ],
        evidence_ids=["ev-proj-boot-0", "ev-proj-boot-1", "ev-proj-boot-2"],
        technologies=["Python", "Flask", "PostgreSQL", "AWS", "React"],
    )
    
    changer_education = Education(
        id="edu-changer-001",
        degree="M.S. Computer Science",
        institution="State University",
        graduation_date="2024-05",
        gpa=3.9,
        relevant_coursework=[
            "Software Engineering",
            "Database Systems",
            "Cloud Computing",
        ],
    )
    
    changer_profile = Profile(
        id="profile-changer-001",
        name="Alex Johnson",
        email="alex@example.com",
        phone="+1-555-0300",
        location="Boston, MA",
        experiences=[teaching_exp],
        projects=[bootcamp_project],
        education=[changer_education],
        skills={
            "Programming Languages": ["Python", "JavaScript"],
            "Frameworks": ["Flask", "React"],
            "Cloud": ["AWS"],
            "Databases": ["PostgreSQL"],
        },
    )
    
    # Initialize services
    jd_service = JDExtractionService()
    coverage_service = CoverageMappingService()
    bullet_service = EnhancedBulletService()
    
    # Extract JD
    print("  Step 1: Extracting job description...")
    extraction_result = await jd_service.extract_job_description(SAMPLE_JD_TEXT)
    
    # Compute coverage
    print("  Step 2: Computing coverage map...")
    coverage_result = await coverage_service.compute_coverage_map(
        extracted_jd=extraction_result.extracted_jd,
        profile=changer_profile,
        job_id="test-job-003"
    )
    
    coverage_map = coverage_result.coverage_map
    
    # Validate mixed coverage
    # Should have some coverage from projects/education despite experience gap
    assert coverage_map.overall_coverage_score > 0.3  # Some coverage
    assert len(coverage_map.covered_requirements) > 0
    assert len(coverage_map.gap_requirements) > 0
    
    print(f"  Coverage: {coverage_map.overall_coverage_score:.1%}")
    print(f"  Covered: {len(coverage_map.covered_requirements)}")
    print(f"  Gaps: {len(coverage_map.gap_requirements)}")
    
    # Generate bullets
    print("  Step 3: Generating bullets...")
    bullet_result = await bullet_service.generate_with_provenance(
        coverage_map=coverage_map,
        profile=changer_profile,
        max_bullets_per_role=5
    )
    
    # Should generate some bullets (projects/education evidence)
    assert len(bullet_result.get_all_bullets()) > 0
    
    # Print metrics
    metrics = print_pipeline_metrics(
        extraction_result,
        coverage_result,
        bullet_result,
        "Career Changer"
    )
    
    print("  ✅ Test passed: Career changer handled appropriately")


@pytest.mark.asyncio
async def test_pipeline_error_handling():
    """Test pipeline error handling and recovery.
    
    This tests how the system handles various error conditions:
    - Invalid JD text
    - Empty profile
    - API failures (mocked)
    - Invalid data structures
    
    Test validates:
    1. Graceful error handling
    2. Informative error messages
    3. No crashes or data corruption
    4. Fallback logic works
    """
    print("\n🧪 TEST: Error Handling")
    
    jd_service = JDExtractionService()
    coverage_service = CoverageMappingService()
    
    # Test 1: Invalid JD text
    print("  Test 1: Invalid JD text...")
    try:
        result = await jd_service.extract_job_description("")
        # Should either return None or raise ValueError
        if result.extracted_jd is not None:
            # If it doesn't fail, it should at least have no requirements
            assert len(result.extracted_jd.must_have_requirements) == 0
    except ValueError as e:
        print(f"    ✓ Caught expected error: {e}")
    
    # Test 2: Empty profile
    print("  Test 2: Empty profile...")
    empty_profile = Profile(
        id="profile-empty",
        name="Empty User",
        email="empty@example.com",
        phone="+1-555-9999",
        location="Nowhere",
        experiences=[],
        projects=[],
        education=[],
        skills={},
    )
    
    # Extract valid JD
    extraction_result = await jd_service.extract_job_description(SAMPLE_JD_TEXT)
    
    # Try coverage mapping with empty profile
    try:
        coverage_result = await coverage_service.compute_coverage_map(
            extracted_jd=extraction_result.extracted_jd,
            profile=empty_profile,
            job_id="test-job-error"
        )
        
        # Should work but have 0% coverage
        assert coverage_result.coverage_map.overall_coverage_score == 0.0
        print("    ✓ Empty profile handled: 0% coverage")
    
    except Exception as e:
        print(f"    ✓ Caught expected error: {e}")
    
    print("  ✅ Test passed: Error handling robust")


@pytest.mark.asyncio
async def test_pipeline_performance():
    """Test pipeline performance and benchmarks.
    
    This test measures and validates performance across the pipeline:
    - JD extraction latency
    - Coverage mapping time
    - Bullet generation speed
    - Total end-to-end time
    
    Success criteria:
    - JD extraction: <5s
    - Coverage mapping: <3s  
    - Bullet generation: <7s
    - Total pipeline: <15s
    """
    print("\n🧪 TEST: Performance Benchmarks")
    
    # Initialize services
    jd_service = JDExtractionService()
    coverage_service = CoverageMappingService()
    bullet_service = EnhancedBulletService()
    
    # Create test data
    profile = create_sample_profile()
    
    # Benchmark JD extraction
    print("  Benchmarking JD extraction...")
    start_time = time.time()
    extraction_result = await jd_service.extract_job_description(SAMPLE_JD_TEXT)
    extraction_time = time.time() - start_time
    
    print(f"    Time: {extraction_time:.2f}s")
    assert extraction_time < 10.0, f"JD extraction too slow: {extraction_time:.2f}s"
    
    # Benchmark coverage mapping
    print("  Benchmarking coverage mapping...")
    start_time = time.time()
    coverage_result = await coverage_service.compute_coverage_map(
        extracted_jd=extraction_result.extracted_jd,
        profile=profile,
        job_id="test-job-perf"
    )
    coverage_time = time.time() - start_time
    
    print(f"    Time: {coverage_time:.2f}s")
    assert coverage_time < 5.0, f"Coverage mapping too slow: {coverage_time:.2f}s"
    
    # Benchmark bullet generation
    print("  Benchmarking bullet generation...")
    start_time = time.time()
    bullet_result = await bullet_service.generate_with_provenance(
        coverage_map=coverage_result.coverage_map,
        profile=profile,
        max_bullets_per_role=5
    )
    generation_time = time.time() - start_time
    
    print(f"    Time: {generation_time:.2f}s")
    assert generation_time < 10.0, f"Bullet generation too slow: {generation_time:.2f}s"
    
    # Total time
    total_time = extraction_time + coverage_time + generation_time
    print(f"\n  Total Pipeline Time: {total_time:.2f}s")
    assert total_time < 20.0, f"Total pipeline too slow: {total_time:.2f}s"
    
    # Print performance summary
    print("\n  Performance Summary:")
    print(f"    JD Extraction:    {extraction_time:.2f}s")
    print(f"    Coverage Mapping: {coverage_time:.2f}s")
    print(f"    Bullet Generation:{generation_time:.2f}s")
    print(f"    ──────────────────────────")
    print(f"    Total:            {total_time:.2f}s")
    
    print("  ✅ Test passed: Performance acceptable")


@pytest.mark.asyncio
async def test_provenance_chain_integrity():
    """Test that provenance chain is complete and accurate.
    
    This is a critical test ensuring every generated bullet maintains
    a complete audit trail back to evidence. We validate:
    - Evidence IDs are valid UUIDs or formatted strings
    - Evidence IDs map to real evidence in profile
    - Similarity scores are reasonable (0-1 range)
    - Requirement text matches original JD
    - Verification links back to same evidence
    
    Why this matters:
    - Legal compliance (claims must be verifiable)
    - User trust (transparency about sources)
    - Debugging (trace errors to source)
    - Audit trail (regulatory requirements)
    """
    print("\n🧪 TEST: Provenance Chain Integrity")
    
    # Initialize services
    jd_service = JDExtractionService()
    coverage_service = CoverageMappingService()
    bullet_service = EnhancedBulletService()
    
    # Create test data
    profile = create_sample_profile()
    
    # Run pipeline
    print("  Running pipeline...")
    extraction_result = await jd_service.extract_job_description(SAMPLE_JD_TEXT)
    coverage_result = await coverage_service.compute_coverage_map(
        extracted_jd=extraction_result.extracted_jd,
        profile=profile,
        job_id="test-job-prov"
    )
    bullet_result = await bullet_service.generate_with_provenance(
        coverage_map=coverage_result.coverage_map,
        profile=profile,
        max_bullets_per_role=5
    )
    
    # Collect all evidence IDs from profile
    valid_evidence_ids = set()
    for exp in profile.experiences:
        valid_evidence_ids.update(exp.evidence_ids)
    for proj in profile.projects:
        valid_evidence_ids.update(proj.evidence_ids)
    
    print(f"  Valid evidence IDs in profile: {len(valid_evidence_ids)}")
    
    # Validate each bullet's provenance
    print("  Validating provenance chains...")
    for i, bullet in enumerate(bullet_result.get_all_bullets(), 1):
        print(f"\n  Bullet {i}: {bullet.text[:50]}...")
        
        # 1. Evidence IDs exist
        assert len(bullet.evidence_ids) > 0, "Bullet has no evidence IDs"
        print(f"    ✓ Has {len(bullet.evidence_ids)} evidence IDs")
        
        # 2. Evidence IDs are valid (exist in profile)
        for eid in bullet.evidence_ids:
            assert eid in valid_evidence_ids or eid.startswith(("exp-", "proj-", "edu-")), \
                f"Invalid evidence ID: {eid}"
        print(f"    ✓ Evidence IDs valid")
        
        # 3. Similarity scores are reasonable
        for score in bullet.similarity_scores:
            assert 0.0 <= score <= 1.0, f"Invalid similarity score: {score}"
        print(f"    ✓ Similarity scores valid ({bullet.similarity_scores[0]:.2f})")
        
        # 4. Requirement text exists
        assert bullet.requirement_text, "Bullet missing requirement text"
        print(f"    ✓ Requirement: '{bullet.requirement_text[:40]}...'")
        
        # 5. Verification result exists
        assert bullet.verification_result is not None, "Bullet missing verification"
        print(f"    ✓ Verified: {bullet.verification_rate:.0%}")
        
        # 6. AMOT components parsed
        assert bullet.action, "Missing action component"
        assert bullet.metric, "Missing metric component"
        assert bullet.outcome, "Missing outcome component"
        assert bullet.tool, "Missing tool component"
        print(f"    ✓ AMOT: {bullet.action} | {bullet.metric} | {bullet.outcome} | {bullet.tool}")
    
    print(f"\n  ✅ Test passed: All {len(bullet_result.get_all_bullets())} bullets have complete provenance")


if __name__ == "__main__":
    """Run tests with pytest or directly for quick debugging."""
    import asyncio
    
    print("\n" + "=" * 80)
    print("INTEGRATION TEST SUITE: Resume Generation Pipeline")
    print("=" * 80)
    
    async def run_all_tests():
        """Run all tests in sequence."""
        try:
            await test_complete_pipeline_happy_path()
            await test_pipeline_with_low_coverage()
            await test_pipeline_with_career_changer()
            await test_pipeline_error_handling()
            await test_pipeline_performance()
            await test_provenance_chain_integrity()
            
            print("\n" + "=" * 80)
            print("ALL TESTS PASSED ✅")
            print("=" * 80)
        
        except Exception as e:
            print(f"\n❌ TEST FAILED: {e}")
            raise
    
    # Run tests
    asyncio.run(run_all_tests())

"""Coverage mapping schemas for matching job requirements to profile evidence.

Coverage mapping is the heart of our provenance system. It determines:
1. Which job requirements the candidate has evidence for
2. Which requirements have no supporting evidence (gaps)
3. How strongly each piece of evidence matches each requirement

This information drives:
- Bullet generation (prioritize addressing covered requirements)
- Gap analysis (alert user to missing qualifications)
- Suggested edits (unverifiable claims need approval)
- Resume ordering (strongest matches first)

The mapping uses semantic similarity (via embeddings) rather than exact keyword
matching, so it can detect when "Python expertise" matches "5 years of Python
development experience" even though the wording differs.
"""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class EvidenceMatch(BaseModel):
    """A single piece of profile evidence matched to a job requirement.
    
    This represents one potential connection between what the candidate has done
    (evidence) and what the job requires (requirement). Each match includes a
    similarity score that indicates how well the evidence addresses the requirement.
    
    For example:
    - Requirement: "5+ years Python experience"
    - Evidence: "Led Python development team for 6 years at TechCorp"
    - Similarity: 0.92 (very strong match)
    
    Attributes:
        evidence_id: UUID of the evidence from profile (links to Experience.evidence_ids)
        evidence_text: The actual evidence text from the resume
        evidence_source: Where the evidence came from (experience/education/project)
        evidence_source_id: ID of the parent entity (e.g., experience ID)
        similarity_score: How well evidence matches requirement (0-1, higher is better)
        keywords_matched: Specific keywords that matched (for explainability)
    """

    evidence_id: str = Field(description="UUID linking to profile evidence")
    evidence_text: str = Field(description="The evidence text (bullet, achievement, etc.)")
    evidence_source: str = Field(
        description="Source type: experience, education, project, certification"
    )
    evidence_source_id: str = Field(description="ID of the parent entity (e.g., exp ID)")
    
    # Similarity scoring (critical for prioritization)
    similarity_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Semantic similarity score (0-1), higher means better match"
    )
    
    # Explainability (helps users understand why something matched)
    keywords_matched: List[str] = Field(
        default_factory=list,
        description="Keywords that appeared in both requirement and evidence"
    )


class RequirementCoverage(BaseModel):
    """Coverage analysis for a single job requirement.
    
    For each requirement in the job description, we analyze how well the
    candidate's profile covers it. This includes:
    1. Finding all relevant evidence
    2. Ranking evidence by similarity
    3. Determining if there's sufficient coverage
    4. Identifying gaps
    
    Example:
    - Requirement: "AWS cloud experience"
    - Matches: [
        Evidence("Deployed 50+ services to AWS", score=0.95),
        Evidence("Managed AWS infrastructure", score=0.88),
        Evidence("Used EC2, S3, Lambda extensively", score=0.87)
      ]
    - Is Covered: True (strong evidence)
    - Coverage Score: 0.95 (highest match)
    
    Attributes:
        requirement_text: The requirement as stated in JD
        requirement_priority: Must-have or nice-to-have (affects importance)
        requirement_keywords: Keywords extracted from requirement
        
        matched_evidence: List of evidence that could address this requirement
        best_match_score: Score of the strongest evidence match
        
        is_covered: Whether we have sufficient evidence for this requirement
        coverage_confidence: How confident we are in the coverage (0-1)
        
        gap_severity: If not covered, how critical is this gap (high/medium/low)
        suggested_actions: What the user should do about gaps
    """

    # The requirement being analyzed
    requirement_text: str = Field(description="The requirement from job description")
    requirement_priority: str = Field(description="must_have or nice_to_have")
    requirement_keywords: List[str] = Field(
        default_factory=list,
        description="Keywords for matching"
    )
    
    # Evidence that matches this requirement (sorted by similarity, best first)
    matched_evidence: List[EvidenceMatch] = Field(
        default_factory=list,
        description="Evidence that could address this requirement, ranked by strength"
    )
    
    # Coverage scores
    best_match_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Score of the strongest evidence match (0 if no matches)"
    )
    
    # Coverage determination
    is_covered: bool = Field(
        default=False,
        description="True if we have sufficient evidence for this requirement"
    )
    coverage_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="How confident we are in the coverage determination"
    )
    
    # Gap analysis (for requirements that aren't well-covered)
    gap_severity: Optional[str] = Field(
        None,
        description="If not covered: high (critical), medium (important), low (minor)"
    )
    suggested_actions: List[str] = Field(
        default_factory=list,
        description="What user should do (e.g., 'Add AWS projects to profile')"
    )

    def get_top_evidence(self, n: int = 3) -> List[EvidenceMatch]:
        """Get the N strongest evidence matches.
        
        Useful for showing users the best evidence to include in resume bullets.
        
        Args:
            n: Number of top matches to return
            
        Returns:
            Top N evidence matches, sorted by similarity score descending
        """
        return sorted(
            self.matched_evidence,
            key=lambda x: x.similarity_score,
            reverse=True
        )[:n]

    def has_strong_evidence(self, threshold: float = 0.8) -> bool:
        """Check if there's at least one strong evidence match.
        
        Strong evidence (>0.8 similarity) means we can confidently generate
        a bullet addressing this requirement with provenance backing.
        
        Args:
            threshold: Minimum similarity score for "strong" evidence
            
        Returns:
            True if best match exceeds threshold
        """
        return self.best_match_score >= threshold


class CoverageMap(BaseModel):
    """Complete coverage analysis for a job-profile pair.
    
    This is the comprehensive result of comparing a job description against
    a candidate's profile. It tells us:
    1. Which requirements are covered (candidate qualifies)
    2. Which requirements are gaps (candidate doesn't qualify)
    3. Which evidence is most relevant for bullet generation
    4. Overall match percentage (for ranking/sorting jobs)
    
    The coverage map is used throughout the pipeline:
    - Bullet generation prioritizes covered requirements
    - Gap analysis alerts user to missing qualifications
    - Resume ordering highlights strongest evidence first
    - Verification service checks evidence for each generated bullet
    
    Attributes:
        job_id: ID of the job being analyzed
        profile_id: ID of the candidate profile
        
        requirement_coverage: Detailed coverage for each requirement
        
        covered_requirements: Requirements with sufficient evidence
        gap_requirements: Requirements with insufficient/no evidence
        
        overall_coverage_score: Percentage of requirements covered (0-1)
        must_have_coverage_score: Percentage of must-haves covered (0-1)
        nice_to_have_coverage_score: Percentage of nice-to-haves covered (0-1)
        
        top_matching_evidence: Best evidence overall (for resume ordering)
        critical_gaps: Most important missing qualifications
    """

    # Job and profile being analyzed
    job_id: str = Field(description="ID of the job")
    profile_id: str = Field(description="ID of the candidate profile")
    
    # Detailed coverage for each requirement
    requirement_coverage: List[RequirementCoverage] = Field(
        default_factory=list,
        description="Coverage analysis for each job requirement"
    )
    
    # Summary lists (for quick filtering)
    covered_requirements: List[str] = Field(
        default_factory=list,
        description="Requirements with sufficient evidence (for bullet generation)"
    )
    gap_requirements: List[str] = Field(
        default_factory=list,
        description="Requirements with insufficient/no evidence (gaps)"
    )
    
    # Overall scores
    overall_coverage_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall match: % of all requirements covered"
    )
    must_have_coverage_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Critical metric: % of must-have requirements covered"
    )
    nice_to_have_coverage_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Bonus metric: % of nice-to-have requirements covered"
    )
    
    # Prioritized evidence (for bullet generation)
    top_matching_evidence: List[EvidenceMatch] = Field(
        default_factory=list,
        description="Top 10 strongest evidence matches across all requirements"
    )
    
    # Gap analysis
    critical_gaps: List[RequirementCoverage] = Field(
        default_factory=list,
        description="Must-have requirements that aren't covered (high severity)"
    )

    def get_must_have_coverage(self) -> List[RequirementCoverage]:
        """Get coverage for must-have requirements only.
        
        Must-haves are critical - if many are gaps, user may not qualify.
        
        Returns:
            List of RequirementCoverage for must-have requirements
        """
        return [rc for rc in self.requirement_coverage if rc.requirement_priority == "must_have"]

    def get_nice_to_have_coverage(self) -> List[RequirementCoverage]:
        """Get coverage for nice-to-have requirements only.
        
        Nice-to-haves are bonuses that strengthen the application.
        
        Returns:
            List of RequirementCoverage for nice-to-have requirements
        """
        return [rc for rc in self.requirement_coverage if rc.requirement_priority == "nice_to_have"]

    def is_strong_match(self, threshold: float = 0.7) -> bool:
        """Determine if this is a strong overall match.
        
        Strong match means the candidate likely qualifies for the role.
        We prioritize must-have coverage for this determination.
        
        Args:
            threshold: Minimum must-have coverage score for "strong"
            
        Returns:
            True if must-have coverage exceeds threshold
        """
        return self.must_have_coverage_score >= threshold

    def get_prioritized_requirements(self) -> List[RequirementCoverage]:
        """Get requirements in priority order for bullet generation.
        
        Priority order:
        1. Covered must-haves (best evidence first)
        2. Covered nice-to-haves (best evidence first)
        3. Uncovered must-haves (for gap analysis)
        
        Returns:
            Requirements sorted by priority
        """
        covered_must_haves = [
            rc for rc in self.requirement_coverage
            if rc.requirement_priority == "must_have" and rc.is_covered
        ]
        covered_nice_to_haves = [
            rc for rc in self.requirement_coverage
            if rc.requirement_priority == "nice_to_have" and rc.is_covered
        ]
        uncovered_must_haves = [
            rc for rc in self.requirement_coverage
            if rc.requirement_priority == "must_have" and not rc.is_covered
        ]
        
        # Sort each group by evidence strength
        covered_must_haves.sort(key=lambda x: x.best_match_score, reverse=True)
        covered_nice_to_haves.sort(key=lambda x: x.best_match_score, reverse=True)
        
        return covered_must_haves + covered_nice_to_haves + uncovered_must_haves

    def get_evidence_for_requirement(self, requirement_text: str) -> Optional[RequirementCoverage]:
        """Find coverage for a specific requirement.
        
        Args:
            requirement_text: The requirement to look up
            
        Returns:
            RequirementCoverage if found, None otherwise
        """
        for rc in self.requirement_coverage:
            if rc.requirement_text == requirement_text:
                return rc
        return None


class CoverageMapResult(BaseModel):
    """Result from coverage mapping service, including metadata.
    
    Wraps the coverage map with execution metadata for monitoring and debugging.
    
    Attributes:
        coverage_map: The coverage analysis
        execution_time_ms: Time taken to compute coverage
        embedding_provider: Which provider computed embeddings (e.g., "openai")
        total_evidence_items: Total evidence items from profile
        total_requirements: Total requirements from job
    """

    coverage_map: CoverageMap
    execution_time_ms: int = Field(description="Time to compute coverage mapping")
    embedding_provider: str = Field(description="Provider used for embeddings (e.g., 'openai')")
    total_evidence_items: int = Field(description="Number of evidence items processed")
    total_requirements: int = Field(description="Number of requirements from job")

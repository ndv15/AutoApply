"""Coverage Mapping Service using semantic similarity via embeddings.

This service is the heart of our provenance system. It determines which job
requirements a candidate's profile covers by computing semantic similarity
between requirements and evidence using embeddings.

Why Embeddings Over Keywords:
- Handles synonyms: "Python expertise" matches "Led Python development"
- Context-aware: "cloud experience" matches "AWS", "GCP", "Azure"
- Robust to phrasing: Different wording, same meaning

Architecture:
    Profile Evidence → Embeddings (cached) ─┐
    Job Requirements → Embeddings (cached) ─┤→ Cosine Similarity → Coverage Scores
    
The service produces a CoverageMap that drives the entire tailoring pipeline:
- Bullet generation prioritizes covered requirements
- Gap analysis identifies missing qualifications
- Verification checks bullets against evidence
- Resume ordering highlights strongest matches

Performance Optimizations:
- Batch embedding generation (fewer API calls)
- Redis caching (evidence reusable across jobs)
- Threshold-based filtering (skip weak matches)

Cost Optimization:
- Use text-embedding-3-small ($0.02/1M tokens vs $0.13 for large)
- Cache embeddings with 30-day TTL
- Batch process to minimize requests
"""

import time
import numpy as np
from typing import List, Dict, Optional, Tuple
from openai import AsyncOpenAI

from autoapply.domain.job_description import ExtractedJD, Requirement
from autoapply.domain.profile import Profile, Experience, Education, Project, EvidenceSpan
from autoapply.domain.coverage import (
    CoverageMap,
    CoverageMapResult,
    RequirementCoverage,
    EvidenceMatch,
)
from autoapply.config.env import get_openai_api_key
from autoapply.util.logger import get_logger

logger = get_logger(__name__)

# OpenAI embedding model - optimized for similarity tasks
# text-embedding-3-small: $0.02/1M tokens, 1536 dimensions, fast
EMBEDDING_MODEL = "text-embedding-3-small"

# Similarity thresholds - tuned based on research and testing
# These determine when a requirement is "covered" vs "gap"
SIMILARITY_THRESHOLDS = {
    "must_have_covered": 0.75,  # Must-have needs strong evidence to be "covered"
    "nice_to_have_covered": 0.65,  # Nice-to-have can be "covered" with moderate evidence
    "weak_match": 0.50,  # Below this, consider unrelated
    "strong_match": 0.85,  # Above this, near-exact match
}


class CoverageMappingService:
    """Service for computing coverage maps via semantic similarity.
    
    This service orchestrates the coverage mapping process:
    1. Extract evidence from profile (bullets, achievements)
    2. Generate embeddings for evidence and requirements
    3. Compute cosine similarity between all pairs
    4. Determine coverage based on thresholds
    5. Identify gaps and suggest actions
    6. Rank evidence for bullet generation
    
    The service is designed to be:
    - Transparent: Every decision is logged and explainable
    - Conservative: Requires strong evidence to mark as "covered"
    - Efficient: Caches embeddings, batches API calls
    - Tunable: Thresholds can be adjusted per industry
    """

    def __init__(self) -> None:
        """Initialize the coverage mapping service with OpenAI client.
        
        Sets up the embedding provider and initializes caching (future).
        If API key is missing, logs warning but doesn't fail (allows testing).
        """
        # Initialize OpenAI client for embeddings
        openai_key = get_openai_api_key()
        self.openai_client = AsyncOpenAI(api_key=openai_key) if openai_key else None
        
        if not self.openai_client:
            logger.warning(
                "OpenAI API key not configured. Coverage mapping will fail. "
                "Set OPENAI_API_KEY in .env"
            )
        
        # TODO: Initialize Redis cache for embeddings
        # self.cache = RedisCache()

    async def compute_coverage_map(
        self,
        extracted_jd: ExtractedJD,
        profile: Profile,
        job_id: str,
    ) -> CoverageMapResult:
        """Compute complete coverage map for job-profile pair.
        
        This is the main entry point for coverage mapping. It performs the
        full analysis pipeline:
        
        Process:
        1. Extract all evidence from profile (experiences, projects, etc.)
        2. Generate embeddings for requirements and evidence
        3. Compute similarity matrix (requirements x evidence)
        4. For each requirement, find best matching evidence
        5. Determine if requirement is covered based on thresholds
        6. Calculate overall coverage scores
        7. Identify critical gaps
        8. Rank evidence for bullet generation
        
        Args:
            extracted_jd: Structured job description with requirements
            profile: Candidate profile with evidence
            job_id: Unique job identifier for this analysis
            
        Returns:
            CoverageMapResult with complete analysis and metadata
            
        Raises:
            RuntimeError: If embedding generation fails and no fallback available
        """
        start_time = time.time()
        
        logger.info(
            f"Starting coverage mapping: job_id={job_id}, profile_id={profile.id}"
        )
        
        # Step 1: Extract evidence from profile
        # Each piece of evidence gets a unique ID for provenance tracking
        evidence_items = self._extract_evidence_from_profile(profile)
        logger.debug(f"Extracted {len(evidence_items)} evidence items from profile")
        
        # Step 2: Get all requirements from job
        # Combines must-have and nice-to-have for comprehensive analysis
        all_requirements = extracted_jd.get_all_requirements()
        logger.debug(f"Analyzing {len(all_requirements)} job requirements")
        
        # Step 3: Generate embeddings
        # Batch process for efficiency (fewer API calls)
        try:
            evidence_embeddings = await self._generate_embeddings(
                [ev.text for ev in evidence_items]
            )
            requirement_embeddings = await self._generate_embeddings(
                [req.text for req in all_requirements]
            )
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise RuntimeError(f"Failed to generate embeddings: {e}")
        
        # Step 4: Compute similarity matrix
        # Each (requirement, evidence) pair gets a similarity score
        similarity_matrix = self._compute_similarity_matrix(
            requirement_embeddings,
            evidence_embeddings
        )
        
        # Step 5: Analyze coverage for each requirement
        # Determines which requirements are covered and which are gaps
        requirement_coverage_list = self._analyze_requirement_coverage(
            all_requirements,
            evidence_items,
            similarity_matrix
        )
        
        # Step 6: Calculate overall scores
        # Aggregates per-requirement coverage into job-level metrics
        coverage_map = self._build_coverage_map(
            job_id=job_id,
            profile_id=profile.id,
            requirement_coverage_list=requirement_coverage_list,
            evidence_items=evidence_items,
            similarity_matrix=similarity_matrix
        )
        
        # Calculate execution time
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        logger.info(
            f"Coverage mapping complete: "
            f"overall={coverage_map.overall_coverage_score:.2%}, "
            f"must_have={coverage_map.must_have_coverage_score:.2%}, "
            f"time={elapsed_ms}ms"
        )
        
        return CoverageMapResult(
            coverage_map=coverage_map,
            execution_time_ms=elapsed_ms,
            embedding_provider=EMBEDDING_MODEL,
            total_evidence_items=len(evidence_items),
            total_requirements=len(all_requirements),
        )

    def _extract_evidence_from_profile(self, profile: Profile) -> List[EvidenceSpan]:
        """Extract all evidence spans from profile for matching.
        
        Evidence comes from multiple sources:
        - Experience bullets (primary source for most roles)
        - Project achievements
        - Education accomplishments
        - Certification details
        
        Each evidence span maintains its provenance (source type and ID)
        so we can trace generated bullets back to their origin.
        
        Args:
            profile: Candidate profile
            
        Returns:
            List of EvidenceSpan objects with UUIDs and source tracking
        """
        evidence_items: List[EvidenceSpan] = []
        
        # Extract from experiences
        # Most important source - actual work accomplishments
        for exp in profile.experiences:
            for i, bullet in enumerate(exp.bullets):
                # Each bullet should already have an evidence_id from ingestion
                # If not, we use the index as a fallback
                evidence_id = (
                    exp.evidence_ids[i] 
                    if i < len(exp.evidence_ids) 
                    else f"{exp.id}-bullet-{i}"
                )
                
                evidence_items.append(
                    EvidenceSpan(
                        id=evidence_id,
                        source_type="experience",
                        source_id=exp.id,
                        text=bullet,
                        category="work_achievement",
                    )
                )
        
        # Extract from projects
        # Important for technical roles, side projects, open source
        for project in profile.projects:
            # Project description as evidence
            evidence_items.append(
                EvidenceSpan(
                    id=f"{project.id}-desc",
                    source_type="project",
                    source_id=project.id,
                    text=project.description,
                    category="project_description",
                )
            )
            
            # Project achievements as separate evidence
            for i, achievement in enumerate(project.achievements):
                evidence_id = (
                    project.evidence_ids[i]
                    if i < len(project.evidence_ids)
                    else f"{project.id}-achievement-{i}"
                )
                
                evidence_items.append(
                    EvidenceSpan(
                        id=evidence_id,
                        source_type="project",
                        source_id=project.id,
                        text=achievement,
                        category="project_achievement",
                    )
                )
        
        # Extract from education
        # Relevant coursework, honors, thesis work
        for edu in profile.education:
            # Degree as evidence (e.g., "B.S. Computer Science" matches "CS degree required")
            evidence_items.append(
                EvidenceSpan(
                    id=f"{edu.id}-degree",
                    source_type="education",
                    source_id=edu.id,
                    text=f"{edu.degree} from {edu.institution}",
                    category="education_credential",
                )
            )
            
            # Relevant coursework
            for i, course in enumerate(edu.relevant_coursework):
                evidence_items.append(
                    EvidenceSpan(
                        id=f"{edu.id}-course-{i}",
                        source_type="education",
                        source_id=edu.id,
                        text=course,
                        category="education_coursework",
                    )
                )
        
        logger.debug(
            f"Extracted evidence: {len(evidence_items)} items from "
            f"{len(profile.experiences)} experiences, "
            f"{len(profile.projects)} projects, "
            f"{len(profile.education)} education entries"
        )
        
        return evidence_items

    async def _generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts using OpenAI.
        
        Embeddings are dense vector representations that capture semantic meaning.
        We use these to compute similarity between requirements and evidence.
        
        The service batches requests for efficiency and will implement caching
        in the future to avoid redundant API calls for the same text.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            NumPy array of shape (n_texts, embedding_dim)
            
        Raises:
            RuntimeError: If API call fails
        """
        if not texts:
            return np.array([])
        
        logger.debug(f"Generating embeddings for {len(texts)} texts")
        
        try:
            # TODO: Check cache first
            # cached_embeddings = await self.cache.get_embeddings(texts)
            # if all_cached: return cached_embeddings
            
            # Call OpenAI embedding API
            # The API handles batching internally, but we may want to chunk
            # large requests (>1000 texts) to avoid timeouts
            response = await self.openai_client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=texts,
                encoding_format="float",  # Get raw floats, not base64
            )
            
            # Extract embeddings from response
            # Response contains list of embedding objects, each with .embedding
            embeddings = [item.embedding for item in response.data]
            embeddings_array = np.array(embeddings)
            
            # TODO: Cache for future use
            # await self.cache.set_embeddings(texts, embeddings_array)
            
            logger.debug(
                f"Generated embeddings: shape={embeddings_array.shape}, "
                f"tokens_used={response.usage.total_tokens}"
            )
            
            return embeddings_array
        
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise RuntimeError(f"Failed to generate embeddings: {e}")

    def _compute_similarity_matrix(
        self,
        requirement_embeddings: np.ndarray,
        evidence_embeddings: np.ndarray
    ) -> np.ndarray:
        """Compute cosine similarity matrix between requirements and evidence.
        
        Cosine similarity measures the angle between two vectors, ranging from
        -1 (opposite) to 1 (identical). For text embeddings, values typically
        range from 0 (unrelated) to 1 (very similar).
        
        The resulting matrix has shape (n_requirements, n_evidence) where
        matrix[i, j] is the similarity between requirement i and evidence j.
        
        Cosine similarity formula:
            similarity = (A · B) / (||A|| * ||B||)
        
        Args:
            requirement_embeddings: Shape (n_requirements, embedding_dim)
            evidence_embeddings: Shape (n_evidence, embedding_dim)
            
        Returns:
            Similarity matrix of shape (n_requirements, n_evidence)
        """
        # Normalize embeddings to unit length
        # This allows us to use simple dot product instead of full cosine formula
        req_normalized = requirement_embeddings / np.linalg.norm(
            requirement_embeddings, axis=1, keepdims=True
        )
        ev_normalized = evidence_embeddings / np.linalg.norm(
            evidence_embeddings, axis=1, keepdims=True
        )
        
        # Compute similarity as dot product (since vectors are normalized)
        # Result: (n_requirements, n_evidence) matrix
        similarity_matrix = np.dot(req_normalized, ev_normalized.T)
        
        # Clip to [0, 1] range (shouldn't be necessary but ensures valid scores)
        similarity_matrix = np.clip(similarity_matrix, 0.0, 1.0)
        
        logger.debug(
            f"Computed similarity matrix: shape={similarity_matrix.shape}, "
            f"mean={similarity_matrix.mean():.3f}, max={similarity_matrix.max():.3f}"
        )
        
        return similarity_matrix

    def _analyze_requirement_coverage(
        self,
        requirements: List[Requirement],
        evidence_items: List[EvidenceSpan],
        similarity_matrix: np.ndarray
    ) -> List[RequirementCoverage]:
        """Analyze coverage for each requirement.
        
        For each requirement, this function:
        1. Finds all evidence with similarity > weak_match threshold
        2. Ranks evidence by similarity score
        3. Determines if requirement is "covered" based on best match
        4. Calculates gap severity if not covered
        5. Suggests actions for gaps
        
        Coverage determination logic:
        - Must-have: Needs similarity ≥ 0.75 to be "covered"
        - Nice-to-have: Needs similarity ≥ 0.65 to be "covered"
        - Below thresholds = gap
        
        Args:
            requirements: List of job requirements
            evidence_items: List of profile evidence
            similarity_matrix: Similarity scores (requirements x evidence)
            
        Returns:
            List of RequirementCoverage objects with analysis
        """
        coverage_list: List[RequirementCoverage] = []
        
        for req_idx, requirement in enumerate(requirements):
            # Get similarity scores for this requirement vs all evidence
            req_similarities = similarity_matrix[req_idx, :]
            
            # Find evidence above weak match threshold
            # Below 0.5 is considered unrelated noise
            weak_threshold = SIMILARITY_THRESHOLDS["weak_match"]
            relevant_indices = np.where(req_similarities >= weak_threshold)[0]
            
            # Build list of evidence matches
            matched_evidence: List[EvidenceMatch] = []
            for ev_idx in relevant_indices:
                evidence = evidence_items[ev_idx]
                similarity = float(req_similarities[ev_idx])
                
                # Extract keywords that appear in both requirement and evidence
                # This helps explain WHY they matched
                keywords_matched = self._find_common_keywords(
                    requirement.text,
                    evidence.text
                )
                
                matched_evidence.append(
                    EvidenceMatch(
                        evidence_id=evidence.id,
                        evidence_text=evidence.text,
                        evidence_source=evidence.source_type,
                        evidence_source_id=evidence.source_id,
                        similarity_score=similarity,
                        keywords_matched=keywords_matched,
                    )
                )
            
            # Sort by similarity (best first)
            matched_evidence.sort(key=lambda x: x.similarity_score, reverse=True)
            
            # Determine coverage based on best match
            best_match_score = matched_evidence[0].similarity_score if matched_evidence else 0.0
            
            # Coverage thresholds depend on priority
            if requirement.priority == "must_have":
                coverage_threshold = SIMILARITY_THRESHOLDS["must_have_covered"]
            else:  # nice_to_have
                coverage_threshold = SIMILARITY_THRESHOLDS["nice_to_have_covered"]
            
            is_covered = best_match_score >= coverage_threshold
            
            # Calculate confidence in coverage determination
            # High confidence when best match is well above/below threshold
            # Low confidence when best match is near threshold (ambiguous)
            distance_from_threshold = abs(best_match_score - coverage_threshold)
            coverage_confidence = min(1.0, distance_from_threshold / 0.15)  # 0.15 = ambiguity window
            
            # Determine gap severity and suggested actions
            gap_severity = None
            suggested_actions = []
            
            if not is_covered:
                # Gap analysis
                if requirement.priority == "must_have":
                    gap_severity = "high"  # Critical gap
                    suggested_actions.append(
                        f"CRITICAL: Add evidence of '{requirement.text}' to your profile"
                    )
                else:
                    gap_severity = "medium" if best_match_score < 0.5 else "low"
                    suggested_actions.append(
                        f"Consider adding examples of '{requirement.text}' if applicable"
                    )
                
                # Suggest specific actions based on requirement category
                if requirement.category == "technical":
                    suggested_actions.append(
                        "Add projects, certifications, or work examples demonstrating this skill"
                    )
                elif requirement.category == "experience":
                    suggested_actions.append(
                        "Highlight any relevant experience, even if from different roles"
                    )
            
            coverage_list.append(
                RequirementCoverage(
                    requirement_text=requirement.text,
                    requirement_priority=requirement.priority,
                    requirement_keywords=requirement.keywords,
                    matched_evidence=matched_evidence,
                    best_match_score=best_match_score,
                    is_covered=is_covered,
                    coverage_confidence=coverage_confidence,
                    gap_severity=gap_severity,
                    suggested_actions=suggested_actions,
                )
            )
        
        return coverage_list

    def _build_coverage_map(
        self,
        job_id: str,
        profile_id: str,
        requirement_coverage_list: List[RequirementCoverage],
        evidence_items: List[EvidenceSpan],
        similarity_matrix: np.ndarray
    ) -> CoverageMap:
        """Build complete coverage map with aggregated scores.
        
        Aggregates per-requirement analysis into job-level metrics:
        - Overall coverage score (% of all requirements covered)
        - Must-have coverage score (% of must-haves covered)
        - Nice-to-have coverage score (% of nice-to-haves covered)
        - Top matching evidence (for bullet generation)
        - Critical gaps (for gap analysis)
        
        Args:
            job_id: Job identifier
            profile_id: Profile identifier
            requirement_coverage_list: Per-requirement analysis
            evidence_items: All evidence from profile
            similarity_matrix: Similarity scores
            
        Returns:
            Complete CoverageMap with all metrics
        """
        # Separate by priority
        must_have_coverage = [rc for rc in requirement_coverage_list if rc.requirement_priority == "must_have"]
        nice_to_have_coverage = [rc for rc in requirement_coverage_list if rc.requirement_priority == "nice_to_have"]
        
        # Calculate coverage scores
        def calc_coverage_pct(coverage_list: List[RequirementCoverage]) -> float:
            if not coverage_list:
                return 0.0
            covered_count = sum(1 for rc in coverage_list if rc.is_covered)
            return covered_count / len(coverage_list)
        
        must_have_score = calc_coverage_pct(must_have_coverage)
        nice_to_have_score = calc_coverage_pct(nice_to_have_coverage)
        
        # Overall score weights must-haves more heavily (70%) than nice-to-haves (30%)
        if must_have_coverage and nice_to_have_coverage:
            overall_score = (must_have_score * 0.7) + (nice_to_have_score * 0.3)
        elif must_have_coverage:
            overall_score = must_have_score
        elif nice_to_have_coverage:
            overall_score = nice_to_have_score
        else:
            overall_score = 0.0
        
        # Build summary lists
        covered_requirements = [rc.requirement_text for rc in requirement_coverage_list if rc.is_covered]
        gap_requirements = [rc.requirement_text for rc in requirement_coverage_list if not rc.is_covered]
        
        # Identify top matching evidence (for bullet generation)
        # We want the evidence with highest average similarity across all requirements
        evidence_avg_scores = similarity_matrix.max(axis=0)  # Max similarity per evidence
        top_indices = np.argsort(evidence_avg_scores)[::-1][:10]  # Top 10
        
        top_matching_evidence = []
        for ev_idx in top_indices:
            if evidence_avg_scores[ev_idx] >= SIMILARITY_THRESHOLDS["weak_match"]:
                evidence = evidence_items[ev_idx]
                # Find which requirement this evidence best matches
                best_req_idx = int(similarity_matrix[:, ev_idx].argmax())
                
                top_matching_evidence.append(
                    EvidenceMatch(
                        evidence_id=evidence.id,
                        evidence_text=evidence.text,
                        evidence_source=evidence.source_type,
                        evidence_source_id=evidence.source_id,
                        similarity_score=float(evidence_avg_scores[ev_idx]),
                        keywords_matched=[],  # Not relevant for top-level summary
                    )
                )
        
        # Identify critical gaps (must-haves that aren't covered)
        critical_gaps = [rc for rc in must_have_coverage if not rc.is_covered]
        
        return CoverageMap(
            job_id=job_id,
            profile_id=profile_id,
            requirement_coverage=requirement_coverage_list,
            covered_requirements=covered_requirements,
            gap_requirements=gap_requirements,
            overall_coverage_score=overall_score,
            must_have_coverage_score=must_have_score,
            nice_to_have_coverage_score=nice_to_have_score,
            top_matching_evidence=top_matching_evidence,
            critical_gaps=critical_gaps,
        )

    def _find_common_keywords(self, text1: str, text2: str) -> List[str]:
        """Find keywords that appear in both texts (case-insensitive).
        
        This provides explainability - shows user WHY two texts matched.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            List of common keywords (lowercase)
        """
        # Simple word-based matching
        # More sophisticated: use NLP tokenization, lemmatization
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        # Find intersection, filter out common stop words
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        common = (words1 & words2) - stop_words
        
        # Return as sorted list
        return sorted(list(common))

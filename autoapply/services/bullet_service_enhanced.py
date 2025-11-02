"""Enhanced Bullet Service with Provenance Tracking and Verification.

This is the enhanced version of the bullet service that integrates:
1. Coverage-driven generation (prioritizes covered requirements)
2. Provenance tracking (links bullets to evidence)
3. Verification integration (validates against evidence)
4. AMOT enforcement (ensures format compliance)

The service bridges the gap between coverage analysis and resume generation,
ensuring every bullet is:
- Relevant (addresses job requirements)
- Verifiable (backed by evidence)
- Compliant (follows AMOT format)
- Transparent (shows provenance chain)

Architecture:
    CoverageMap → Prioritized Requirements → For each requirement:
        ↓
    Get Top Evidence Matches (similarity scores)
        ↓
    Generate Bullet (Claude/GPT-4 with evidence context)
        ↓
    Link to Evidence IDs (provenance)
        ↓
    Verify Against Evidence (component-level)
        ↓
    If verified → Proposed | If not → Suggested Edit

This ensures users only see bullets they can trust, with full transparency
into what's verified and what needs their approval.
"""

import time
from uuid import uuid4
from typing import List, Dict, Optional, Tuple
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from autoapply.domain.coverage import CoverageMap, RequirementCoverage, EvidenceMatch
from autoapply.domain.profile import Profile, EvidenceSpan
from autoapply.domain.validators.amot import parse_amot
from autoapply.services.verification_service import (
    VerificationService,
    BulletVerificationResult,
)
from autoapply.config.env import get_openai_api_key, get_anthropic_api_key
from autoapply.util.logger import get_logger

logger = get_logger(__name__)

# Model selection for bullet generation
# Claude is preferred for creative writing with structure
GENERATION_MODEL_CLAUDE = "claude-3-5-sonnet-20241022"
GENERATION_MODEL_GPT = "gpt-4o"  # Fallback


class ProvenanceBullet:
    """A resume bullet with full provenance tracking.
    
    This class represents a generated bullet that maintains complete
    transparency about its origins:
    - Which job requirement it addresses
    - Which evidence from profile it's based on
    - Verification status for each component
    - Generation metadata (model used, timestamp, etc.)
    
    Provenance Chain Example:
        Job Requirement: "5+ years Python experience"
            ↓ Matched to
        Evidence: "Led Python team for 6 years" (similarity: 0.92)
            ↓ Generated
        Bullet: "Led Python development team of 8 engineers for 6 years..."
            ↓ Verified
        Components: Action ✓ | Metric ✓ | Outcome ✓ | Tool ✓
            ↓ Status
        Proposed (ready for resume)
    
    Attributes:
        id: Unique identifier for this bullet
        text: The actual bullet text (AMOT format)
        
        # Provenance
        requirement_text: Job requirement this addresses
        evidence_ids: List of evidence UUIDs supporting this bullet
        evidence_texts: The actual evidence texts (for display)
        similarity_scores: How well evidence matched requirement
        
        # AMOT Components
        action: Action verb (e.g., "Led")
        metric: Quantifiable measure (e.g., "35%")
        outcome: Result phrase (e.g., "resulting in $1.8M")
        tool: Method/technology (e.g., "via Salesforce")
        
        # Verification
        verification_result: Component-level verification details
        is_verified: Whether all components verified (4/4)
        verification_rate: Percentage verified (e.g., 0.75 for 3/4)
        
        # Status
        status: "proposed" (verified) | "suggested_edit" (needs approval)
        recommendation: Accept/flag/reject from verification
        
        # Metadata
        generated_by: Model used (e.g., "claude-3-5-sonnet")
        generated_at: Timestamp
    """
    
    def __init__(
        self,
        id: str,
        text: str,
        requirement_text: str,
        evidence_ids: List[str],
        evidence_texts: List[str],
        similarity_scores: List[float],
        action: str,
        metric: str,
        outcome: str,
        tool: str,
        verification_result: BulletVerificationResult,
        generated_by: str,
        generated_at: float,
    ):
        self.id = id
        self.text = text
        
        # Provenance
        self.requirement_text = requirement_text
        self.evidence_ids = evidence_ids
        self.evidence_texts = evidence_texts
        self.similarity_scores = similarity_scores
        
        # AMOT
        self.action = action
        self.metric = metric
        self.outcome = outcome
        self.tool = tool
        
        # Verification
        self.verification_result = verification_result
        self.is_verified = verification_result.is_fully_verified
        self.verification_rate = verification_result.overall_verification_rate
        
        # Status
        self.status = "proposed" if verification_result.is_acceptable else "suggested_edit"
        self.recommendation = verification_result.recommendation
        
        # Metadata
        self.generated_by = generated_by
        self.generated_at = generated_at
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage/serialization."""
        return {
            "id": self.id,
            "text": self.text,
            "requirement_text": self.requirement_text,
            "evidence_ids": self.evidence_ids,
            "evidence_texts": self.evidence_texts,
            "similarity_scores": self.similarity_scores,
            "action": self.action,
            "metric": self.metric,
            "outcome": self.outcome,
            "tool": self.tool,
            "is_verified": self.is_verified,
            "verification_rate": self.verification_rate,
            "status": self.status,
            "recommendation": self.recommendation,
            "generated_by": self.generated_by,
            "generated_at": self.generated_at,
        }


class BulletGenerationResult:
    """Result from bullet generation with categorization.
    
    Generated bullets are categorized based on verification status:
    - Proposed: Verified bullets ready for resume (user can use immediately)
    - Suggested Edits: Unverified bullets needing user approval
    
    This separation ensures users never unknowingly include unverifiable claims.
    
    Attributes:
        proposed_bullets: Verified bullets (ready for resume)
        suggested_edits: Unverified bullets (need user approval)
        generation_metadata: Stats for monitoring/debugging
    """
    
    def __init__(
        self,
        proposed_bullets: List[ProvenanceBullet],
        suggested_edits: List[ProvenanceBullet],
        generation_metadata: Dict,
    ):
        self.proposed_bullets = proposed_bullets
        self.suggested_edits = suggested_edits
        self.generation_metadata = generation_metadata
    
    def get_all_bullets(self) -> List[ProvenanceBullet]:
        """Get all bullets regardless of status."""
        return self.proposed_bullets + self.suggested_edits
    
    def get_verification_stats(self) -> Dict[str, float]:
        """Calculate verification statistics.
        
        Returns:
            Dict with:
            - total_bullets: Total generated
            - proposed_count: Number verified
            - suggested_edit_count: Number unverified
            - average_verification_rate: Mean verification %
            - fully_verified_rate: % with all components verified
        """
        all_bullets = self.get_all_bullets()
        
        if not all_bullets:
            return {
                "total_bullets": 0,
                "proposed_count": 0,
                "suggested_edit_count": 0,
                "average_verification_rate": 0.0,
                "fully_verified_rate": 0.0,
            }
        
        return {
            "total_bullets": len(all_bullets),
            "proposed_count": len(self.proposed_bullets),
            "suggested_edit_count": len(self.suggested_edits),
            "average_verification_rate": sum(
                b.verification_rate for b in all_bullets
            ) / len(all_bullets),
            "fully_verified_rate": sum(
                1 for b in all_bullets if b.is_verified
            ) / len(all_bullets),
        }


class EnhancedBulletService:
    """Enhanced bullet generation service with provenance and verification.
    
    This service orchestrates the complete bullet generation pipeline:
    1. Takes coverage map with prioritized requirements
    2. For each covered requirement:
       a. Gets top evidence matches (highest similarity)
       b. Generates AMOT bullet using evidence context
       c. Links bullet to evidence IDs (provenance)
       d. Verifies bullet against evidence
       e. Categorizes as proposed or suggested edit
    
    The service ensures:
    - Relevance: Bullets address job requirements
    - Verifiability: All claims backed by evidence
    - Transparency: Full provenance chain maintained
    - Quality: AMOT format enforced and verified
    
    Usage Example:
        service = EnhancedBulletService()
        result = await service.generate_with_provenance(
            coverage_map=coverage_map,
            profile=profile,
            max_bullets_per_role=5
        )
        
        # Use verified bullets
        for bullet in result.proposed_bullets:
            print(f"✓ {bullet.text}")
            print(f"  Based on: {bullet.evidence_texts[0]}")
            print(f"  Verified: {bullet.verification_rate:.0%}")
        
        # Review suggested edits
        for bullet in result.suggested_edits:
            print(f"⚠ {bullet.text}")
            print(f"  Issue: {bullet.verification_result.explanation}")
    """
    
    def __init__(self) -> None:
        """Initialize the enhanced bullet service.
        
        Sets up AI clients for generation and verification service.
        """
        # Initialize Claude client (primary for generation)
        anthropic_key = get_anthropic_api_key()
        self.claude_client = AsyncAnthropic(api_key=anthropic_key) if anthropic_key else None
        
        # Initialize OpenAI client (fallback)
        openai_key = get_openai_api_key()
        self.openai_client = AsyncOpenAI(api_key=openai_key) if openai_key else None
        
        # Initialize verification service
        self.verification_service = VerificationService()
        
        if not self.claude_client and not self.openai_client:
            logger.warning(
                "No AI provider keys configured. Bullet generation will fail. "
                "Set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env"
            )
    
    async def generate_with_provenance(
        self,
        coverage_map: CoverageMap,
        profile: Profile,
        max_bullets_per_role: int = 5,
        require_full_verification: bool = False,
    ) -> BulletGenerationResult:
        """Generate AMOT bullets with full provenance tracking.
        
        This is the main entry point for provenance-backed bullet generation.
        It implements the complete pipeline from coverage analysis to verified bullets.
        
        Process:
        1. Get prioritized requirements from coverage map
           (covered must-haves first, then nice-to-haves)
        2. For each requirement (up to max_bullets_per_role):
           a. Get top 3 evidence matches
           b. Generate bullet with Claude/GPT-4
           c. Link to evidence IDs
           d. Verify against evidence
           e. Categorize based on verification
        3. Return categorized bullets with metadata
        
        Generation Strategy:
        - Focus on covered requirements (where we have evidence)
        - Use strongest evidence matches (highest similarity scores)
        - Generate diverse bullets (avoid redundancy)
        - Verify before proposing (no unverifiable claims)
        
        Args:
            coverage_map: Complete coverage analysis for job-profile pair
            profile: Candidate profile (for evidence lookup)
            max_bullets_per_role: Maximum bullets to generate
            require_full_verification: If True, only accept 100% verified bullets
            
        Returns:
            BulletGenerationResult with proposed and suggested edit bullets
            
        Raises:
            ValueError: If coverage_map has no covered requirements
            RuntimeError: If generation fails and no fallback available
        """
        start_time = time.time()
        
        logger.info(
            f"Starting bullet generation: job_id={coverage_map.job_id}, "
            f"profile_id={coverage_map.profile_id}, max_bullets={max_bullets_per_role}"
        )
        
        # Step 1: Get prioritized requirements
        # Prioritization: covered must-haves > covered nice-to-haves > gaps
        prioritized_requirements = coverage_map.get_prioritized_requirements()
        
        # Filter to only covered requirements (we need evidence to generate)
        covered_requirements = [req for req in prioritized_requirements if req.is_covered]
        
        if not covered_requirements:
            raise ValueError(
                "No covered requirements found. Cannot generate bullets without evidence."
            )
        
        logger.info(
            f"Found {len(covered_requirements)} covered requirements "
            f"({len([r for r in covered_requirements if r.requirement_priority == 'must_have'])} must-have)"
        )
        
        # Step 2: Generate bullets for top requirements
        # Limit to max_bullets_per_role to avoid overwhelming the user
        requirements_to_use = covered_requirements[:max_bullets_per_role]
        
        # Extract all evidence from profile for verification
        all_evidence = self._extract_all_evidence(profile)
        
        generated_bullets: List[ProvenanceBullet] = []
        
        for req_coverage in requirements_to_use:
            try:
                # Generate one bullet for this requirement
                bullet = await self._generate_bullet_for_requirement(
                    requirement_coverage=req_coverage,
                    all_evidence=all_evidence,
                    require_full_verification=require_full_verification,
                )
                
                if bullet:
                    generated_bullets.append(bullet)
                    logger.info(
                        f"Generated bullet: verified={bullet.is_verified} "
                        f"({bullet.verification_rate:.0%}), "
                        f"requirement='{req_coverage.requirement_text[:50]}...'"
                    )
            
            except Exception as e:
                logger.error(
                    f"Failed to generate bullet for requirement "
                    f"'{req_coverage.requirement_text}': {e}"
                )
                # Continue with other requirements
                continue
        
        # Step 3: Categorize bullets
        proposed = [b for b in generated_bullets if b.status == "proposed"]
        suggested_edits = [b for b in generated_bullets if b.status == "suggested_edit"]
        
        # Calculate elapsed time
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        # Build metadata
        metadata = {
            "total_generated": len(generated_bullets),
            "proposed_count": len(proposed),
            "suggested_edit_count": len(suggested_edits),
            "generation_time_ms": elapsed_ms,
            "requirements_processed": len(requirements_to_use),
            "requirements_skipped": len(covered_requirements) - len(requirements_to_use),
        }
        
        logger.info(
            f"Bullet generation complete: {len(proposed)} proposed, "
            f"{len(suggested_edits)} suggested edits, time={elapsed_ms}ms"
        )
        
        return BulletGenerationResult(
            proposed_bullets=proposed,
            suggested_edits=suggested_edits,
            generation_metadata=metadata,
        )
    
    async def _generate_bullet_for_requirement(
        self,
        requirement_coverage: RequirementCoverage,
        all_evidence: List[EvidenceSpan],
        require_full_verification: bool,
    ) -> Optional[ProvenanceBullet]:
        """Generate a single bullet for a covered requirement.
        
        This method orchestrates generation for one requirement:
        1. Get top 3 evidence matches
        2. Call Claude/GPT-4 to generate bullet
        3. Parse AMOT components
        4. Verify against evidence
        5. Build ProvenanceBullet with metadata
        
        Args:
            requirement_coverage: Coverage analysis for this requirement
            all_evidence: All evidence from profile (for verification)
            require_full_verification: Only accept 100% verified bullets
            
        Returns:
            ProvenanceBullet if generation successful, None otherwise
        """
        # Get top 3 evidence matches for this requirement
        top_evidence = requirement_coverage.get_top_evidence(n=3)
        
        if not top_evidence:
            logger.warning(f"No evidence matches for requirement: {requirement_coverage.requirement_text}")
            return None
        
        # Extract evidence details for generation
        evidence_texts = [match.evidence_text for match in top_evidence]
        evidence_ids = [match.evidence_id for match in top_evidence]
        similarity_scores = [match.similarity_score for match in top_evidence]
        
        # Generate bullet text with AI
        try:
            bullet_text, model_used = await self._call_generation_api(
                requirement=requirement_coverage.requirement_text,
                evidence_texts=evidence_texts,
            )
        except Exception as e:
            logger.error(f"Generation API failed: {e}")
            return None
        
        # Parse AMOT components
        try:
            amot_parts = parse_amot(bullet_text)
        except Exception as e:
            logger.error(f"AMOT parsing failed for bullet '{bullet_text}': {e}")
            return None
        
        # Verify against evidence
        verification_result = await self.verification_service.verify_bullet(
            bullet_text=bullet_text,
            evidence_items=all_evidence,
            evidence_ids_claimed=evidence_ids,
        )
        
        # Check if verification meets requirements
        if require_full_verification and not verification_result.is_fully_verified:
            logger.info(
                f"Bullet not fully verified ({verification_result.overall_verification_rate:.0%}), "
                f"skipping due to require_full_verification=True"
            )
            return None
        
        # Build ProvenanceBullet
        bullet = ProvenanceBullet(
            id=str(uuid4()),
            text=bullet_text,
            requirement_text=requirement_coverage.requirement_text,
            evidence_ids=evidence_ids,
            evidence_texts=evidence_texts,
            similarity_scores=similarity_scores,
            action=amot_parts["action"],
            metric=amot_parts["metric"],
            outcome=amot_parts["outcome"],
            tool=amot_parts["tool"],
            verification_result=verification_result,
            generated_by=model_used,
            generated_at=time.time(),
        )
        
        return bullet
    
    async def _call_generation_api(
        self,
        requirement: str,
        evidence_texts: List[str],
    ) -> Tuple[str, str]:
        """Call AI API to generate bullet with evidence context.
        
        Uses Claude as primary, GPT-4 as fallback.
        
        The prompt emphasizes:
        1. Use ONLY information from provided evidence
        2. Follow AMOT format strictly
        3. Be specific and quantitative
        4. Don't invent or exaggerate
        
        Args:
            requirement: Job requirement to address
            evidence_texts: Evidence from profile to base bullet on
            
        Returns:
            Tuple of (bullet_text, model_used)
            
        Raises:
            RuntimeError: If both providers fail
        """
        # Build generation prompt
        prompt = self._build_generation_prompt(requirement, evidence_texts)
        
        # Try Claude first
        if self.claude_client:
            try:
                response = await self.claude_client.messages.create(
                    model=GENERATION_MODEL_CLAUDE,
                    max_tokens=200,
                    temperature=0.7,  # Some creativity but not too much
                    system="You are an expert resume writer who creates AMOT-formatted bullets.",
                    messages=[{"role": "user", "content": prompt}]
                )
                
                bullet_text = response.content[0].text.strip()
                return bullet_text, GENERATION_MODEL_CLAUDE
            
            except Exception as e:
                logger.error(f"Claude generation failed: {e}")
        
        # Try GPT-4 fallback
        if self.openai_client:
            try:
                response = await self.openai_client.chat.completions.create(
                    model=GENERATION_MODEL_GPT,
                    messages=[
                        {"role": "system", "content": "You are an expert resume writer."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=200,
                )
                
                bullet_text = response.choices[0].message.content.strip()
                return bullet_text, GENERATION_MODEL_GPT
            
            except Exception as e:
                logger.error(f"GPT-4 generation failed: {e}")
        
        # Both failed
        raise RuntimeError("Failed to generate bullet: no AI providers available")
    
    def _build_generation_prompt(
        self,
        requirement: str,
        evidence_texts: List[str]
    ) -> str:
        """Build prompt for bullet generation.
        
        The prompt is carefully crafted to:
        1. Emphasize using ONLY provided evidence
        2. Require AMOT format (all 4 components)
        3. Encourage specificity and quantification
        4. Prevent invention or exaggeration
        
        Args:
            requirement: Job requirement to address
            evidence_texts: Evidence to base bullet on
            
        Returns:
            Generation prompt
        """
        evidence_str = "\n".join(f"- {text}" for text in evidence_texts)
        
        return f"""Generate a resume bullet that addresses this job requirement:

Requirement: {requirement}

Use ONLY information from this evidence:
{evidence_str}

CRITICAL RULES:
1. Use AMOT format: Action + Metric + Outcome + Tool
   - Action: Strong verb (Led, Drove, Increased, Built, etc.)
   - Metric: Specific number, percentage, or currency
   - Outcome: Result phrase (resulting in, leading to, achieving, driving)
   - Tool: Method or technology (via X, using Y, through Z)

2. Use ONLY facts from the evidence provided
3. Do NOT invent numbers, tools, or achievements
4. Do NOT exaggerate or embellish
5. Be specific and quantitative

Example AMOT bullets:
- "Drove 35% pipeline growth resulting in $1.8M ARR via MEDDICC methodology"
- "Led team of 8 engineers through Agile transformation achieving 40% faster delivery"
- "Increased system reliability to 99.9% uptime leading to $500K cost savings using AWS"

Generate ONE bullet (nothing else):"""
    
    def _extract_all_evidence(self, profile: Profile) -> List[EvidenceSpan]:
        """Extract all evidence spans from profile.
        
        This is a helper that collects all evidence for verification purposes.
        
        Args:
            profile: Candidate profile
            
        Returns:
            List of all evidence spans
        """
        evidence = []
        
        # From experiences
        for exp in profile.experiences:
            for i, bullet in enumerate(exp.bullets):
                evidence_id = (
                    exp.evidence_ids[i]
                    if i < len(exp.evidence_ids)
                    else f"{exp.id}-bullet-{i}"
                )
                evidence.append(
                    EvidenceSpan(
                        id=evidence_id,
                        source_type="experience",
                        source_id=exp.id,
                        text=bullet,
                        category="work_achievement",
                    )
                )
        
        # From projects
        for project in profile.projects:
            evidence.append(
                EvidenceSpan(
                    id=f"{project.id}-desc",
                    source_type="project",
                    source_id=project.id,
                    text=project.description,
                    category="project_description",
                )
            )
            
            for i, achievement in enumerate(project.achievements):
                evidence_id = (
                    project.evidence_ids[i]
                    if i < len(project.evidence_ids)
                    else f"{project.id}-achievement-{i}"
                )
                evidence.append(
                    EvidenceSpan(
                        id=evidence_id,
                        source_type="project",
                        source_id=project.id,
                        text=achievement,
                        category="project_achievement",
                    )
                )
        
        # From education
        for edu in profile.education:
            evidence.append(
                EvidenceSpan(
                    id=f"{edu.id}-degree",
                    source_type="education",
                    source_id=edu.id,
                    text=f"{edu.degree} from {edu.institution}",
                    category="education_credential",
                )
            )
        
        return evidence

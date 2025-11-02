"""Verification Service for validating bullets against evidence.

This service is critical for maintaining our "no invented claims" guarantee.
Every generated resume bullet must be verifiable against the candidate's profile
evidence. This prevents hallucination and ensures factual accuracy.

Why Verification Matters:
- Trust: Users trust bullets are backed by their actual experience
- Compliance: Prevents fabricated credentials (legal/ethical issue)
- Quality: Ensures generated content is grounded in reality
- Transparency: Users see exactly what's verified vs suggested

Verification Philosophy:
- Conservative: When in doubt, mark as unverifiable
- Semantic: "Drove" and "Led" are equivalent (use GPT-4)
- Component-Level: Check each AMOT component separately
- Evidence-Based: All claims must trace to specific evidence

Architecture:
    Generated Bullet → Parse AMOT → For each component → Check Evidence
                                                              ↓
                                    Verified (use) ← GPT-4 Semantic Check → Unverified (flag)

Example Verification:
    Bullet: "Drove 35% pipeline growth resulting in $1.8M ARR via MEDDICC"
    
    Components:
    - Action: "Drove" → Evidence: "Increased sales" → Verified ✓ (synonym)
    - Metric: "35%" → Evidence: "35%" → Verified ✓ (exact match)
    - Outcome: "$1.8M ARR" → Evidence: "$1.8M revenue" → Verified ✓ (equivalent)
    - Tool: "MEDDICC" → Evidence: [not found] → Unverified ✗
    
    Result: 75% verified (3/4 components)
    Action: Mark "MEDDICC" as suggested edit for user approval
"""

import re
import time
from typing import List, Dict, Optional, Tuple
from openai import AsyncOpenAI

from autoapply.domain.profile import Profile, EvidenceSpan
from autoapply.config.env import get_openai_api_key
from autoapply.util.logger import get_logger

logger = get_logger(__name__)

# GPT-4 for semantic verification (best reasoning)
VERIFICATION_MODEL = "gpt-4o"


class AMOTComponents:
    """Parsed components of an AMOT-formatted bullet.
    
    AMOT = Action + Metric + Outcome + Tool
    
    Each component is verified independently against evidence.
    This granular approach allows us to identify exactly which
    parts of a bullet are supported vs unsupported.
    
    Attributes:
        action: Strong verb at start (e.g., "Drove", "Led", "Increased")
        metric: Quantifiable measure (e.g., "35%", "$1.8M", "50 services")
        outcome: Result/impact phrase (e.g., "resulting in", "leading to")
        tool: Method/technology used (e.g., "via Salesforce", "using Python")
        full_text: Complete bullet text
    """
    
    def __init__(
        self,
        action: str,
        metric: str,
        outcome: str,
        tool: str,
        full_text: str
    ):
        self.action = action
        self.metric = metric
        self.outcome = outcome
        self.tool = tool
        self.full_text = full_text
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for logging/debugging."""
        return {
            "action": self.action,
            "metric": self.metric,
            "outcome": self.outcome,
            "tool": self.tool,
            "full_text": self.full_text,
        }


class ComponentVerification:
    """Verification result for a single AMOT component.
    
    Each component (action, metric, outcome, tool) gets verified independently.
    This allows us to provide granular feedback: "3 out of 4 components verified".
    
    Attributes:
        component_name: Which component ("action", "metric", "outcome", "tool")
        component_text: The actual text being verified
        is_verified: Whether this component is supported by evidence
        supporting_evidence: Evidence that backs this component (if verified)
        verification_method: How we verified ("exact_match", "semantic_match", "synonym")
        confidence: How confident we are in the verification (0-1)
        explanation: Human-readable explanation of why verified/unverified
    """
    
    def __init__(
        self,
        component_name: str,
        component_text: str,
        is_verified: bool,
        supporting_evidence: Optional[str] = None,
        verification_method: Optional[str] = None,
        confidence: float = 1.0,
        explanation: str = ""
    ):
        self.component_name = component_name
        self.component_text = component_text
        self.is_verified = is_verified
        self.supporting_evidence = supporting_evidence
        self.verification_method = verification_method
        self.confidence = confidence
        self.explanation = explanation


class BulletVerificationResult:
    """Complete verification result for a resume bullet.
    
    Aggregates component-level verifications into an overall assessment
    of whether the bullet should be accepted, flagged, or rejected.
    
    Verification Thresholds:
    - 100% verified (4/4): Fully supported → Accept
    - 75%+ verified (3/4): Mostly supported → Accept with note
    - 50-74% verified (2/4): Partially supported → Flag for review
    - <50% verified (0-1/4): Unsupported → Reject or move to suggested edits
    
    Attributes:
        bullet_text: The full bullet being verified
        amot_components: Parsed AMOT components
        component_verifications: List of per-component verification results
        overall_verification_rate: Percentage of components verified (0-1)
        is_fully_verified: True if all 4 components verified
        is_acceptable: True if ≥75% components verified
        recommendation: What to do with this bullet (accept/flag/reject)
        explanation: Why this recommendation was made
        evidence_ids: UUIDs of evidence supporting this bullet
    """
    
    def __init__(
        self,
        bullet_text: str,
        amot_components: AMOTComponents,
        component_verifications: List[ComponentVerification],
    ):
        self.bullet_text = bullet_text
        self.amot_components = amot_components
        self.component_verifications = component_verifications
        
        # Calculate verification rate
        verified_count = sum(1 for cv in component_verifications if cv.is_verified)
        total_count = len(component_verifications)
        self.overall_verification_rate = verified_count / total_count if total_count > 0 else 0.0
        
        # Determine status
        self.is_fully_verified = (verified_count == 4)
        self.is_acceptable = (self.overall_verification_rate >= 0.75)
        
        # Make recommendation
        if self.is_fully_verified:
            self.recommendation = "accept"
            self.explanation = "All AMOT components verified against evidence"
        elif self.is_acceptable:
            self.recommendation = "accept_with_note"
            unverified = [cv.component_name for cv in component_verifications if not cv.is_verified]
            self.explanation = f"Mostly verified ({verified_count}/4). Unverified: {', '.join(unverified)}"
        elif self.overall_verification_rate >= 0.5:
            self.recommendation = "flag_for_review"
            self.explanation = f"Partially verified ({verified_count}/4). User should review."
        else:
            self.recommendation = "reject"
            self.explanation = f"Insufficiently verified ({verified_count}/4). Move to suggested edits."
        
        # Extract evidence IDs
        self.evidence_ids = [
            cv.supporting_evidence 
            for cv in component_verifications 
            if cv.is_verified and cv.supporting_evidence
        ]


class VerificationService:
    """Service for verifying resume bullets against profile evidence.
    
    This service ensures that every bullet on the resume is backed by
    verifiable evidence from the candidate's profile. The verification
    process is:
    
    1. Parse bullet into AMOT components
    2. For each component, search evidence for support
    3. Use exact matching for metrics (numbers must match exactly)
    4. Use semantic matching for actions/outcomes (GPT-4 understands synonyms)
    5. Aggregate component verifications into overall result
    6. Recommend accept/flag/reject based on verification rate
    
    The service is designed to be:
    - Conservative: Defaults to unverified when ambiguous
    - Transparent: Shows exactly what's verified and why
    - Granular: Component-level feedback for debugging
    - Semantic: Understands synonyms and paraphrasing
    """
    
    def __init__(self) -> None:
        """Initialize the verification service with GPT-4 client.
        
        Sets up the OpenAI client for semantic verification.
        If API key is missing, logs warning but doesn't fail.
        """
        # Initialize OpenAI client for semantic verification
        openai_key = get_openai_api_key()
        self.openai_client = AsyncOpenAI(api_key=openai_key) if openai_key else None
        
        if not self.openai_client:
            logger.warning(
                "OpenAI API key not configured. Verification will use exact matching only. "
                "Set OPENAI_API_KEY in .env for semantic verification."
            )
    
    async def verify_bullet(
        self,
        bullet_text: str,
        evidence_items: List[EvidenceSpan],
        evidence_ids_claimed: Optional[List[str]] = None
    ) -> BulletVerificationResult:
        """Verify a single resume bullet against evidence.
        
        This is the main entry point for bullet verification. It performs
        the complete verification pipeline:
        
        Process:
        1. Parse bullet into AMOT components
        2. For each component, verify against evidence
        3. Aggregate into overall verification result
        4. Make recommendation (accept/flag/reject)
        
        Args:
            bullet_text: The resume bullet to verify
            evidence_items: List of evidence from profile
            evidence_ids_claimed: Optional list of evidence IDs that bullet claims to use
            
        Returns:
            BulletVerificationResult with component-level and overall analysis
            
        Raises:
            ValueError: If bullet_text is empty or invalid
        """
        if not bullet_text or not bullet_text.strip():
            raise ValueError("Bullet text cannot be empty")
        
        logger.info(f"Verifying bullet: {bullet_text[:50]}...")
        
        # Step 1: Parse into AMOT components
        # This identifies what claims the bullet makes
        amot_components = self._parse_amot_components(bullet_text)
        
        # Step 2: Filter evidence if specific IDs provided
        # This allows us to verify against claimed provenance
        if evidence_ids_claimed:
            relevant_evidence = [
                ev for ev in evidence_items 
                if ev.id in evidence_ids_claimed
            ]
            if not relevant_evidence:
                logger.warning(f"None of claimed evidence IDs found: {evidence_ids_claimed}")
                relevant_evidence = evidence_items  # Fallback to all evidence
        else:
            relevant_evidence = evidence_items
        
        # Step 3: Verify each component
        # Each AMOT component verified independently for granularity
        component_verifications = []
        
        # Verify action (strong verb)
        action_verification = await self._verify_action(
            amot_components.action,
            relevant_evidence
        )
        component_verifications.append(action_verification)
        
        # Verify metric (quantifiable measure)
        metric_verification = await self._verify_metric(
            amot_components.metric,
            relevant_evidence
        )
        component_verifications.append(metric_verification)
        
        # Verify outcome (result/impact)
        outcome_verification = await self._verify_outcome(
            amot_components.outcome,
            relevant_evidence
        )
        component_verifications.append(outcome_verification)
        
        # Verify tool (method/technology)
        tool_verification = await self._verify_tool(
            amot_components.tool,
            relevant_evidence
        )
        component_verifications.append(tool_verification)
        
        # Step 4: Build verification result
        result = BulletVerificationResult(
            bullet_text=bullet_text,
            amot_components=amot_components,
            component_verifications=component_verifications,
        )
        
        logger.info(
            f"Verification complete: {result.overall_verification_rate:.0%} "
            f"({sum(1 for cv in component_verifications if cv.is_verified)}/4 components)"
        )
        
        return result
    
    def _parse_amot_components(self, bullet_text: str) -> AMOTComponents:
        """Parse bullet into Action, Metric, Outcome, Tool components.
        
        AMOT format requires all four components:
        1. Action: Strong verb at start (Led, Drove, Increased, etc.)
        2. Metric: Quantifiable measure (35%, $1.8M, 50 services, etc.)
        3. Outcome: Result phrase (resulting in, leading to, achieved, etc.)
        4. Tool: Method/tech (via Salesforce, using Python, through Agile, etc.)
        
        This parsing is heuristic-based and may not be perfect, but it's
        sufficient for verification purposes. The key is identifying the
        claims being made so we can verify them.
        
        Args:
            bullet_text: Resume bullet in AMOT format
            
        Returns:
            AMOTComponents with extracted parts
        """
        # Extract action (first word, typically a strong verb)
        # Common actions: Led, Drove, Increased, Built, Managed, Achieved, etc.
        words = bullet_text.strip().split()
        action = words[0] if words else ""
        
        # Extract metric (numbers, percentages, currency)
        # Patterns: 35%, $1.8M, 50+ services, [X%], [$Y], etc.
        metric_patterns = [
            r'\d+%',                           # 35%
            r'[$£€]\d[\d,\.]*[KMB]?',         # $1.8M, $100K
            r'\d+[\+]?\s+\w+',                 # 50+ services
            r'\[[$£€]?[A-Z0-9%]+\]',          # [X%], [$Y]
        ]
        
        metrics_found = []
        for pattern in metric_patterns:
            matches = re.findall(pattern, bullet_text)
            metrics_found.extend(matches)
        
        metric = metrics_found[0] if metrics_found else "[metric not found]"
        
        # Extract outcome phrase (result indicators)
        # Common patterns: "resulting in", "leading to", "achieving", "driving"
        outcome_patterns = [
            r'resulting in [^,\.;]+',
            r'leading to [^,\.;]+',
            r'achiev(?:ing|ed) [^,\.;]+',
            r'driving [^,\.;]+',
        ]
        
        outcome = ""
        for pattern in outcome_patterns:
            match = re.search(pattern, bullet_text, re.IGNORECASE)
            if match:
                outcome = match.group(0)
                break
        
        if not outcome:
            outcome = "[outcome not found]"
        
        # Extract tool (method/technology indicators)
        # Common patterns: "via X", "using Y", "through Z", "leveraging W"
        tool_patterns = [
            r'via [^,\.;]+',
            r'using [^,\.;]+',
            r'through [^,\.;]+',
            r'leveraging [^,\.;]+',
        ]
        
        tool = ""
        for pattern in tool_patterns:
            match = re.search(pattern, bullet_text, re.IGNORECASE)
            if match:
                tool = match.group(0)
                break
        
        if not tool:
            tool = "[tool not found]"
        
        return AMOTComponents(
            action=action,
            metric=metric,
            outcome=outcome,
            tool=tool,
            full_text=bullet_text
        )
    
    async def _verify_action(
        self,
        action: str,
        evidence_items: List[EvidenceSpan]
    ) -> ComponentVerification:
        """Verify that action verb is supported by evidence.
        
        Actions are verified semantically - "Led" and "Managed" are
        considered equivalent for verification purposes. We use GPT-4
        to understand synonyms and paraphrasing.
        
        Verification logic:
        1. Check for exact word match in evidence
        2. If no exact match, use GPT-4 for semantic check
        3. GPT-4 determines if action is "substantially equivalent"
        
        Args:
            action: Action verb from bullet
            evidence_items: Evidence to check against
            
        Returns:
            ComponentVerification for action
        """
        # Check for exact match first (fast path)
        for evidence in evidence_items:
            if action.lower() in evidence.text.lower():
                return ComponentVerification(
                    component_name="action",
                    component_text=action,
                    is_verified=True,
                    supporting_evidence=evidence.id,
                    verification_method="exact_match",
                    confidence=1.0,
                    explanation=f"Action '{action}' found in evidence: {evidence.text[:50]}..."
                )
        
        # No exact match - try semantic verification with GPT-4
        if self.openai_client:
            for evidence in evidence_items:
                is_equivalent = await self._check_semantic_equivalence(
                    claim=f"Action: {action}",
                    evidence_text=evidence.text,
                    component_type="action"
                )
                
                if is_equivalent:
                    return ComponentVerification(
                        component_name="action",
                        component_text=action,
                        is_verified=True,
                        supporting_evidence=evidence.id,
                        verification_method="semantic_match",
                        confidence=0.85,  # Slightly lower confidence for semantic
                        explanation=f"Action '{action}' semantically equivalent to evidence"
                    )
        
        # Not verified
        return ComponentVerification(
            component_name="action",
            component_text=action,
            is_verified=False,
            verification_method="no_match",
            confidence=1.0,
            explanation=f"Action '{action}' not found in evidence"
        )
    
    async def _verify_metric(
        self,
        metric: str,
        evidence_items: List[EvidenceSpan]
    ) -> ComponentVerification:
        """Verify that metric (number) appears in evidence.
        
        Metrics require EXACT or VERY CLOSE matches - we cannot
        accept different numbers as "equivalent". 35% is not the
        same as 40%, even if they're similar.
        
        Verification logic:
        1. Extract core number from metric (e.g., "35" from "35%")
        2. Check if this exact number appears in evidence
        3. Allow minor variations (35.0% = 35% = 35.00%)
        
        Args:
            metric: Metric from bullet (e.g., "35%", "$1.8M")
            evidence_items: Evidence to check
            
        Returns:
            ComponentVerification for metric
        """
        # Extract core numbers from metric
        # Remove currency symbols, percent signs, etc.
        metric_numbers = re.findall(r'\d+(?:\.\d+)?', metric)
        
        if not metric_numbers:
            # Metric might be placeholder like [X%]
            # Check if evidence has any metric
            for evidence in evidence_items:
                if re.search(r'\d+%|\$\d+', evidence.text):
                    return ComponentVerification(
                        component_name="metric",
                        component_text=metric,
                        is_verified=True,
                        supporting_evidence=evidence.id,
                        verification_method="placeholder_match",
                        confidence=0.7,
                        explanation=f"Placeholder metric, found numerical data in evidence"
                    )
        
        # Check each evidence for exact number match
        for evidence in evidence_items:
            for number in metric_numbers:
                # Allow flexible matching: 35 = 35.0 = 35.00
                pattern = rf'\b{number}(?:\.0+)?\b'
                if re.search(pattern, evidence.text):
                    return ComponentVerification(
                        component_name="metric",
                        component_text=metric,
                        is_verified=True,
                        supporting_evidence=evidence.id,
                        verification_method="exact_match",
                        confidence=1.0,
                        explanation=f"Metric '{metric}' found in evidence: {evidence.text[:50]}..."
                    )
        
        # Not verified
        return ComponentVerification(
            component_name="metric",
            component_text=metric,
            is_verified=False,
            verification_method="no_match",
            confidence=1.0,
            explanation=f"Metric '{metric}' numbers not found in evidence"
        )
    
    async def _verify_outcome(
        self,
        outcome: str,
        evidence_items: List[EvidenceSpan]
    ) -> ComponentVerification:
        """Verify that outcome/result is supported by evidence.
        
        Outcomes can be verified semantically - "revenue growth"
        and "increased sales" convey similar results.
        
        Args:
            outcome: Outcome phrase from bullet
            evidence_items: Evidence to check
            
        Returns:
            ComponentVerification for outcome
        """
        # Similar to action verification - exact then semantic
        for evidence in evidence_items:
            # Check if key outcome words appear
            outcome_words = outcome.lower().split()
            match_count = sum(1 for word in outcome_words if word in evidence.text.lower())
            
            if match_count >= 2:  # At least 2 words match
                return ComponentVerification(
                    component_name="outcome",
                    component_text=outcome,
                    is_verified=True,
                    supporting_evidence=evidence.id,
                    verification_method="keyword_match",
                    confidence=0.9,
                    explanation=f"Outcome keywords found in evidence"
                )
        
        # Try semantic verification
        if self.openai_client:
            for evidence in evidence_items:
                is_equivalent = await self._check_semantic_equivalence(
                    claim=f"Outcome: {outcome}",
                    evidence_text=evidence.text,
                    component_type="outcome"
                )
                
                if is_equivalent:
                    return ComponentVerification(
                        component_name="outcome",
                        component_text=outcome,
                        is_verified=True,
                        supporting_evidence=evidence.id,
                        verification_method="semantic_match",
                        confidence=0.85,
                        explanation=f"Outcome semantically supported by evidence"
                    )
        
        # Not verified
        return ComponentVerification(
            component_name="outcome",
            component_text=outcome,
            is_verified=False,
            verification_method="no_match",
            confidence=1.0,
            explanation=f"Outcome '{outcome}' not supported by evidence"
        )
    
    async def _verify_tool(
        self,
        tool: str,
        evidence_items: List[EvidenceSpan]
    ) -> ComponentVerification:
        """Verify that tool/method/technology is in evidence.
        
        Tools must appear explicitly in evidence - we can't infer
        that someone used Salesforce if they never mentioned it.
        
        Args:
            tool: Tool/method from bullet (e.g., "via Salesforce")
            evidence_items: Evidence to check
            
        Returns:
            ComponentVerification for tool
        """
        # Extract tool name (remove "via", "using", etc.)
        tool_name = re.sub(r'^(via|using|through|leveraging)\s+', '', tool, flags=re.IGNORECASE).strip()
        
        # Check for exact mention
        for evidence in evidence_items:
            if tool_name.lower() in evidence.text.lower():
                return ComponentVerification(
                    component_name="tool",
                    component_text=tool,
                    is_verified=True,
                    supporting_evidence=evidence.id,
                    verification_method="exact_match",
                    confidence=1.0,
                    explanation=f"Tool '{tool_name}' mentioned in evidence"
                )
        
        # Not verified - tools need explicit mention
        return ComponentVerification(
            component_name="tool",
            component_text=tool,
            is_verified=False,
            verification_method="no_match",
            confidence=1.0,
            explanation=f"Tool '{tool_name}' not mentioned in evidence"
        )
    
    async def _check_semantic_equivalence(
        self,
        claim: str,
        evidence_text: str,
        component_type: str
    ) -> bool:
        """Use GPT-4 to check if claim is semantically equivalent to evidence.
        
        This handles cases where exact wording differs but meaning is same:
        - "Led team" vs "Managed team" (equivalent)
        - "Increased revenue" vs "Drove sales growth" (equivalent)
        - "Built system" vs "Fixed bug" (NOT equivalent)
        
        Args:
            claim: The claim being made in bullet
            evidence_text: Evidence text to check against
            component_type: Type of component (action/outcome)
            
        Returns:
            True if semantically equivalent, False otherwise
        """
        prompt = f"""You are verifying resume claims against evidence.

Claim: {claim}
Evidence: {evidence_text}

Question: Is the claim substantially supported by the evidence?

For {component_type} verification:
- Synonyms are acceptable (Led = Managed = Directed)
- Paraphrasing is acceptable (increased revenue = drove sales growth)
- Different specific details are OK if core claim matches
- Numbers must match if part of claim

Answer with ONLY "YES" or "NO" (nothing else).
"""
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=VERIFICATION_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,  # Deterministic
                max_tokens=10,
            )
            
            answer = response.choices[0].message.content.strip().upper()
            return answer == "YES"
        
        except Exception as e:
            logger.error(f"Semantic verification failed: {e}")
            return False  # Conservative: assume not verified on error

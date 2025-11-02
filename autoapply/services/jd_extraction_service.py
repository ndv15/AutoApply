"""Job Description Extraction Service using Claude for structured parsing.

This service transforms unstructured job postings into structured ExtractedJD objects.
We use Claude (Anthropic) as the primary provider because it excels at:
1. Following complex structured output instructions
2. Conservative reasoning (doesn't hallucinate requirements)
3. Understanding nuance (can distinguish must-have from nice-to-have)

The extraction is critical because it drives the entire tailoring pipeline:
- Coverage mapping uses requirements to find matching evidence
- Bullet generation prioritizes addressing must-have requirements
- ATS optimization incorporates required keywords
- Gap analysis identifies missing qualifications

Architecture:
    JD Text → Claude Extraction → Structured ExtractedJD → Validation → Storage

Error Handling:
    - If Claude fails, we fall back to GPT-4
    - If both fail, we return a minimal ExtractedJD with raw text only
    - All errors are logged for monitoring and debugging
"""

import time
import json
from typing import Optional
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from autoapply.domain.job_description import (
    ExtractedJD,
    JDExtractionResult,
    Requirement,
    Responsibility,
    CompanyInfo,
)
from autoapply.config.env import get_anthropic_api_key, get_openai_api_key
from autoapply.util.logger import get_logger

logger = get_logger(__name__)

# Anthropic model selection - Claude 3.5 Sonnet is best for structured extraction
CLAUDE_MODEL = "claude-3-5-sonnet-20241022"  # Latest as of implementation
GPT_MODEL = "gpt-4o"  # Fallback model


class JDExtractionService:
    """Service for extracting structured data from job descriptions.
    
    This service orchestrates the extraction process:
    1. Prepares the extraction prompt with instructions and schema
    2. Calls Claude API with the job description text
    3. Parses Claude's response into ExtractedJD object
    4. Validates the extracted data
    5. Returns structured result with confidence scores
    
    The service is designed to be conservative - if something is unclear,
    it leaves it empty rather than guessing. This prevents downstream
    issues in coverage mapping and bullet generation.
    """

    def __init__(self) -> None:
        """Initialize the extraction service with API clients.
        
        Sets up both Claude and GPT-4 clients for primary/fallback operation.
        If API keys are missing, logs warnings but doesn't fail (allows testing).
        """
        # Initialize Claude client (primary)
        anthropic_key = get_anthropic_api_key()
        self.claude_client = AsyncAnthropic(api_key=anthropic_key) if anthropic_key else None
        
        # Initialize OpenAI client (fallback)
        openai_key = get_openai_api_key()
        self.openai_client = AsyncOpenAI(api_key=openai_key) if openai_key else None
        
        if not self.claude_client and not self.openai_client:
            logger.warning(
                "No AI provider keys configured. JD extraction will fail. "
                "Set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env"
            )

    async def extract_job_description(
        self,
        jd_text: str,
        use_fallback: bool = True
    ) -> JDExtractionResult:
        """Extract structured data from a job description.
        
        This is the main entry point for JD extraction. It handles the full
        extraction pipeline including error handling and fallback logic.
        
        Process:
        1. Validate input (ensure JD text is not empty)
        2. Build extraction prompt with instructions
        3. Call Claude API with structured output request
        4. Parse response into ExtractedJD
        5. Calculate confidence scores
        6. If extraction fails and fallback enabled, try GPT-4
        7. Return result with metadata
        
        Args:
            jd_text: Raw job description text from user
            use_fallback: If True, try GPT-4 if Claude fails
            
        Returns:
            JDExtractionResult with extracted data and metadata
            
        Raises:
            ValueError: If jd_text is empty or invalid
            RuntimeError: If extraction fails and no fallback available
        """
        # Validate input
        if not jd_text or not jd_text.strip():
            raise ValueError("Job description text cannot be empty")
        
        # Start timing for performance monitoring
        start_time = time.time()
        
        logger.info(f"Starting JD extraction (length: {len(jd_text)} chars)")
        
        try:
            # Try primary provider (Claude)
            if self.claude_client:
                logger.debug("Using Claude for JD extraction")
                extracted_jd = await self._extract_with_claude(jd_text)
                provider_used = CLAUDE_MODEL
            
            # If Claude not available, try fallback immediately
            elif use_fallback and self.openai_client:
                logger.debug("Claude unavailable, using GPT-4 fallback")
                extracted_jd = await self._extract_with_gpt4(jd_text)
                provider_used = GPT_MODEL
            
            else:
                # No providers available
                raise RuntimeError(
                    "No AI providers configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY"
                )
        
        except Exception as e:
            # Extraction failed with primary provider
            logger.error(f"Primary extraction failed: {e}")
            
            # Try fallback if enabled
            if use_fallback and self.openai_client and self.claude_client:
                logger.info("Attempting fallback to GPT-4")
                try:
                    extracted_jd = await self._extract_with_gpt4(jd_text)
                    provider_used = f"{GPT_MODEL} (fallback)"
                except Exception as fallback_error:
                    logger.error(f"Fallback also failed: {fallback_error}")
                    # Return minimal extraction with raw text only
                    extracted_jd = self._create_minimal_extraction(jd_text)
                    provider_used = "minimal (all failed)"
            else:
                # No fallback available, return minimal
                extracted_jd = self._create_minimal_extraction(jd_text)
                provider_used = "minimal (error)"
        
        # Calculate elapsed time
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        # Identify ambiguities and warnings
        ambiguities = self._identify_ambiguities(extracted_jd)
        warnings = self._identify_warnings(extracted_jd)
        
        logger.info(
            f"JD extraction complete: {len(extracted_jd.must_have_requirements)} must-have, "
            f"{len(extracted_jd.nice_to_have_requirements)} nice-to-have requirements, "
            f"time={elapsed_ms}ms, provider={provider_used}"
        )
        
        return JDExtractionResult(
            extracted_jd=extracted_jd,
            provider_used=provider_used,
            extraction_time_ms=elapsed_ms,
            ambiguities=ambiguities,
            warnings=warnings,
        )

    async def _extract_with_claude(self, jd_text: str) -> ExtractedJD:
        """Extract JD using Claude with structured output.
        
        Claude excels at following complex instructions and producing
        structured JSON output. We use a detailed system prompt that:
        1. Explains the task and its importance
        2. Defines the output schema with examples
        3. Emphasizes conservative extraction (don't guess)
        4. Provides extraction guidelines for each field
        
        The prompt is designed to maximize extraction quality while
        minimizing hallucination risk.
        
        Args:
            jd_text: Job description text to extract
            
        Returns:
            ExtractedJD object with structured data
            
        Raises:
            RuntimeError: If Claude API call fails or response is invalid
        """
        # Build the extraction prompt
        # This is a critical component - the quality of extraction depends heavily
        # on prompt quality. We use a few-shot approach with examples.
        system_prompt = self._build_claude_extraction_prompt()
        
        # User message with the actual JD
        user_message = f"""Extract structured information from this job description:

<job_description>
{jd_text}
</job_description>

Return your extraction as valid JSON following the schema provided. Be conservative - if you're unsure about something, leave it empty rather than guessing."""
        
        try:
            # Call Claude API
            # We use a relatively high max_tokens to accommodate detailed extractions
            # Temperature is low (0.3) for consistent, factual extraction
            response = await self.claude_client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=4000,
                temperature=0.3,  # Low temperature for factual extraction
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )
            
            # Extract text from Claude's response
            # Claude returns content blocks, we take the first text block
            response_text = response.content[0].text
            
            logger.debug(f"Claude response length: {len(response_text)} chars")
            
            # Parse JSON response
            # Claude is instructed to return pure JSON, but we handle markdown wrapping
            extracted_data = self._parse_json_response(response_text)
            
            # Convert to ExtractedJD object with validation
            # Pydantic will validate all fields and raise errors if schema violated
            extracted_jd = self._convert_to_extracted_jd(extracted_data, jd_text)
            
            return extracted_jd
        
        except Exception as e:
            logger.error(f"Claude extraction failed: {e}")
            raise RuntimeError(f"Failed to extract JD with Claude: {e}")

    async def _extract_with_gpt4(self, jd_text: str) -> ExtractedJD:
        """Extract JD using GPT-4 as fallback.
        
        GPT-4 is our fallback when Claude is unavailable or fails.
        The prompt structure is similar to Claude's, adapted for OpenAI's format.
        
        Args:
            jd_text: Job description text
            
        Returns:
            ExtractedJD object
            
        Raises:
            RuntimeError: If extraction fails
        """
        system_prompt = self._build_gpt4_extraction_prompt()
        
        user_message = f"""Extract structured information from this job description and return as JSON:

{jd_text}"""
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3,
                max_tokens=4000,
            )
            
            response_text = response.choices[0].message.content
            extracted_data = self._parse_json_response(response_text)
            extracted_jd = self._convert_to_extracted_jd(extracted_data, jd_text)
            
            return extracted_jd
        
        except Exception as e:
            logger.error(f"GPT-4 extraction failed: {e}")
            raise RuntimeError(f"Failed to extract JD with GPT-4: {e}")

    def _build_claude_extraction_prompt(self) -> str:
        """Build the system prompt for Claude extraction.
        
        This prompt is critical for extraction quality. It:
        1. Explains the task and why it matters (context for better performance)
        2. Defines the output schema with clear field descriptions
        3. Provides examples of good extractions
        4. Emphasizes conservative extraction (anti-hallucination)
        
        Returns:
            System prompt for Claude
        """
        return """You are an expert at analyzing job descriptions and extracting structured information.

Your task is to parse a job description and extract:
1. Basic info (title, seniority, location, company)
2. Requirements (split into must-have vs nice-to-have)
3. Responsibilities (day-to-day duties)
4. Keywords for ATS optimization
5. Any red flags (e.g., unpaid, commission-only)

**CRITICAL RULES:**
- Be CONSERVATIVE - if something is unclear, leave it empty rather than guessing
- Distinguish must-have from nice-to-have based on language: "required", "must have" = must-have; "preferred", "nice to have", "bonus" = nice-to-have
- Extract keywords from requirements for semantic matching (e.g., "Python", "AWS", "Agile")
- Flag any concerning language as red flags

**OUTPUT SCHEMA:**
Return valid JSON with this structure:
{
  "title": "Job title",
  "seniority": "entry|mid|senior|staff|principal|unknown",
  "company": {"name": "...", "industry": "...", "size": "...", "stage": "..."},
  "location": "...",
  "employment_type": "full_time|part_time|contract|internship",
  "salary_range": "...",
  "must_have_requirements": [
    {"text": "...", "category": "technical|soft_skill|experience|certification|other", "keywords": ["..."]}
  ],
  "nice_to_have_requirements": [...],
  "responsibilities": [{"text": "...", "keywords": ["..."]}],
  "required_keywords": ["..."],
  "bonus_keywords": ["..."],
  "red_flags": ["..."],
  "confidence_scores": {"seniority": 0.9, "requirements": 0.85}
}

**EXAMPLE EXTRACTION:**

Input: "Senior Software Engineer at TechCorp. Must have: 5+ years Python, AWS experience. Nice to have: React knowledge. $120K-$180K."

Output:
{
  "title": "Senior Software Engineer",
  "seniority": "senior",
  "company": {"name": "TechCorp"},
  "salary_range": "$120K-$180K",
  "must_have_requirements": [
    {"text": "5+ years Python experience", "category": "technical", "keywords": ["Python", "5 years"]},
    {"text": "AWS experience", "category": "technical", "keywords": ["AWS"]}
  ],
  "nice_to_have_requirements": [
    {"text": "React knowledge", "category": "technical", "keywords": ["React"]}
  ],
  "required_keywords": ["Python", "AWS"],
  "bonus_keywords": ["React"],
  "confidence_scores": {"seniority": 1.0, "requirements": 0.9}
}

Now extract the provided job description following these rules."""

    def _build_gpt4_extraction_prompt(self) -> str:
        """Build system prompt for GPT-4 (similar to Claude's).
        
        Returns:
            System prompt for GPT-4
        """
        return """You are an expert job description analyzer. Extract structured information and return as JSON.

Be conservative - only extract what's clearly stated. Distinguish must-have (required) from nice-to-have (preferred).

Return JSON with: title, seniority, must_have_requirements, nice_to_have_requirements, responsibilities, keywords, red_flags."""

    def _parse_json_response(self, response_text: str) -> dict:
        """Parse JSON from LLM response, handling markdown wrappers.
        
        LLMs sometimes wrap JSON in markdown code blocks like:
        ```json
        {...}
        ```
        
        This function strips those wrappers and parses the JSON.
        
        Args:
            response_text: Raw text from LLM
            
        Returns:
            Parsed dict
            
        Raises:
            ValueError: If JSON is invalid
        """
        # Remove markdown code block if present
        text = response_text.strip()
        if text.startswith("```json"):
            text = text[7:]  # Remove ```json
        if text.startswith("```"):
            text = text[3:]  # Remove ```
        if text.endswith("```"):
            text = text[:-3]  # Remove trailing ```
        
        text = text.strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}\nResponse: {text[:200]}...")
            raise ValueError(f"Invalid JSON response from LLM: {e}")

    def _convert_to_extracted_jd(self, data: dict, raw_text: str) -> ExtractedJD:
        """Convert raw dict to ExtractedJD with validation.
        
        This function:
        1. Maps dict fields to ExtractedJD schema
        2. Validates all fields via Pydantic
        3. Adds the raw text for reference
        4. Handles missing fields gracefully
        
        Args:
            data: Extracted data dict from LLM
            raw_text: Original JD text
            
        Returns:
            Validated ExtractedJD object
        """
        # Add raw text
        data["raw_text"] = raw_text
        
        # Set defaults for missing fields
        data.setdefault("seniority", "unknown")
        data.setdefault("employment_type", "full_time")
        data.setdefault("must_have_requirements", [])
        data.setdefault("nice_to_have_requirements", [])
        data.setdefault("responsibilities", [])
        data.setdefault("required_keywords", [])
        data.setdefault("bonus_keywords", [])
        data.setdefault("red_flags", [])
        data.setdefault("confidence_scores", {})
        
        # Convert nested dicts to Pydantic models
        if "company" in data and isinstance(data["company"], dict):
            data["company"] = CompanyInfo(**data["company"])
        
        # Convert requirement lists
        for req_type in ["must_have_requirements", "nice_to_have_requirements"]:
            if req_type in data:
                data[req_type] = [
                    Requirement(**req) if isinstance(req, dict) else req
                    for req in data[req_type]
                ]
        
        # Convert responsibility lists
        if "responsibilities" in data:
            data["responsibilities"] = [
                Responsibility(**resp) if isinstance(resp, dict) else resp
                for resp in data["responsibilities"]
            ]
        
        # Validate and create ExtractedJD
        return ExtractedJD(**data)

    def _create_minimal_extraction(self, jd_text: str) -> ExtractedJD:
        """Create minimal ExtractedJD when extraction fails.
        
        This ensures the system can still function even if AI extraction
        completely fails. We return an ExtractedJD with just the raw text
        and marked as low confidence.
        
        Args:
            jd_text: Original JD text
            
        Returns:
            Minimal ExtractedJD
        """
        return ExtractedJD(
            title="Unknown",
            seniority="unknown",
            raw_text=jd_text,
            confidence_scores={"overall": 0.0}
        )

    def _identify_ambiguities(self, extracted_jd: ExtractedJD) -> List[str]:
        """Identify fields that may need user review.
        
        Checks for:
        - Unknown seniority
        - No requirements found
        - Low confidence scores
        
        Args:
            extracted_jd: Extracted data
            
        Returns:
            List of ambiguity warnings
        """
        ambiguities = []
        
        if extracted_jd.seniority == "unknown":
            ambiguities.append("Could not determine seniority level")
        
        if not extracted_jd.must_have_requirements:
            ambiguities.append("No must-have requirements identified")
        
        if extracted_jd.calculate_overall_confidence() < 0.6:
            ambiguities.append("Low confidence in extraction quality")
        
        return ambiguities

    def _identify_warnings(self, extracted_jd: ExtractedJD) -> List[str]:
        """Identify non-critical issues.
        
        Args:
            extracted_jd: Extracted data
            
        Returns:
            List of warnings
        """
        warnings = []
        
        if not extracted_jd.salary_range:
            warnings.append("Salary range not specified in JD")
        
        if extracted_jd.has_red_flags():
            warnings.append(f"Red flags detected: {', '.join(extracted_jd.red_flags)}")
        
        return warnings

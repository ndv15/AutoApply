"""
Google Gemini provider adapter.
"""
import os
from typing import Dict, Optional
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class GeminiProvider:
    """Wrapper for Google Gemini API."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-1.5-flash"):
        """Initialize with API key from env or parameter."""
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment")

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model)

    def generate(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.7
    ) -> str:
        """
        Generate text completion.

        Args:
            prompt: User prompt
            max_tokens: Max tokens to generate
            temperature: Sampling temperature

        Returns:
            Generated text
        """
        try:
            generation_config = {
                "max_output_tokens": max_tokens,
                "temperature": temperature,
            }

            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )

            return response.text

        except Exception as e:
            print(f"Gemini API error: {e}")
            raise

    def generate_bullet(
        self,
        role_context: Dict,
        jd_text: str,
        research_context: Dict,
        bias: str = "balanced"
    ) -> str:
        """
        Generate a single resume bullet (tie-breaker perspective).

        Args:
            role_context: Dict with role_id, company, title, etc.
            jd_text: Job description text
            research_context: Research context
            bias: "modern", "traditional", or "balanced"

        Returns:
            Generated bullet text
        """
        if bias == "modern":
            style_instruction = "Emphasize innovation, technology, and forward-thinking approaches."
        elif bias == "traditional":
            style_instruction = "Emphasize reliability, proven methods, and solid fundamentals."
        else:
            style_instruction = "Combine innovative thinking with proven execution."

        keywords = research_context.get('keywords', [])
        skills = research_context.get('required_skills', [])

        keyword_list = ", ".join([k['keyword'] for k in keywords[:10]]) if keywords else "N/A"
        skills_list = ", ".join(skills) if skills else "N/A"

        prompt = f"""Create ONE quantified achievement bullet for:

Position: {role_context.get('title', 'Unknown')}
Company: {role_context.get('company', 'Unknown')}
Duration: {role_context.get('start', 'Unknown')} to {role_context.get('end', 'Present')}

Target Job Keywords: {keyword_list}
Required Skills: {skills_list}

Writing Style: {style_instruction}

STRICT REQUIREMENTS (NON-NEGOTIABLE):
1. MUST include ALL FOUR AMOT components:
   - ACTION: Strong verb (Led, Drove, Increased, Closed, Built, Achieved)
   - METRIC: Quantified outcome (%, $, numbers, or placeholders)
   - OUTCOME: Business impact phrase ("resulting in", "achieving", "leading to", "driving")
   - TOOL: Specific method/platform ("via MEDDICC", "using Salesforce", "through...")

2. Quantified metrics (MANDATORY):
   - Percentage: "35%", "↑40%", "increased by [X]%"
   - Dollar: "$2.5M ARR", "+$1.8M revenue", "[$Y] pipeline"
   - Count: "15 enterprise deals", "50+ logos", "[N] accounts"

   **IF EXACT UNKNOWN**: Use clean placeholders [X%], [$Y], [N deals]
   **FORBIDDEN**: "significant", "substantial", "proven track record"

3. Format: 1-2 lines max (under 200 chars)

GOOD EXAMPLES (all have A+M+O+T):
✅ "Drove [X%] quota attainment across [$Y] territory by implementing MEDDICC qualification, resulting in [N] new enterprise logos"
✅ "Increased win rate from 18% to 31% (+13pp) via SPIN discovery framework, achieving $2.1M incremental ARR"
✅ "Closed $2.4M in Q1 (140% of quota) by targeting Fortune 500 CxOs with tailored ROI presentations using Salesforce CPQ"

BAD EXAMPLES (will be rejected):
❌ "Proven track record of increasing revenue" → No metric, forbidden phrase
❌ "Responsible for managing accounts and driving growth" → Vague, no quantification
❌ "Achieved substantial improvement" → No number/placeholder

Return only the bullet text, no explanation."""

        return self.generate(
            prompt=prompt,
            max_tokens=200,
            temperature=0.8
        )

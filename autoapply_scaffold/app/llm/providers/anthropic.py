"""
Anthropic Claude provider adapter.
"""
import os
from typing import Dict, List, Optional
import anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class AnthropicProvider:
    """Wrapper for Anthropic Claude API."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with API key from env or parameter."""
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-3-5-sonnet-20241022"

    def generate(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.7,
        system: Optional[str] = None
    ) -> str:
        """
        Generate text completion.

        Args:
            prompt: User prompt
            max_tokens: Max tokens to generate
            temperature: Sampling temperature
            system: System prompt (optional)

        Returns:
            Generated text
        """
        try:
            messages = [{"role": "user", "content": prompt}]

            kwargs = {
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages
            }

            if system:
                kwargs["system"] = system

            response = self.client.messages.create(**kwargs)
            return response.content[0].text

        except Exception as e:
            print(f"Anthropic API error: {e}")
            raise

    def generate_bullet(
        self,
        role_context: Dict,
        jd_text: str,
        research_context: Dict,
        bias: str = "balanced"
    ) -> str:
        """
        Generate a single resume bullet.

        Args:
            role_context: Dict with role_id, company, title, etc.
            jd_text: Job description text
            research_context: Research context from Perplexity
            bias: "modern", "traditional", or "balanced"

        Returns:
            Generated bullet text
        """
        if bias == "modern":
            style_instruction = "Emphasize cutting-edge methodologies, data-driven approaches, and modern tools/technologies."
        elif bias == "traditional":
            style_instruction = "Emphasize proven best practices, established methodologies, and core competencies."
        else:
            style_instruction = "Balance modern innovation with proven traditional approaches."

        keywords = research_context.get('keywords', [])
        skills = research_context.get('required_skills', [])

        keyword_list = ", ".join([k['keyword'] for k in keywords[:10]]) if keywords else "N/A"
        skills_list = ", ".join(skills) if skills else "N/A"

        prompt = f"""Generate ONE quantified, achievement-focused resume bullet for this role:

Role: {role_context.get('title', 'Unknown')} at {role_context.get('company', 'Unknown')}
Dates: {role_context.get('start', 'Unknown')} - {role_context.get('end', 'Present')}

Target Job Keywords: {keyword_list}
Required Skills: {skills_list}

Style: {style_instruction}

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

Return ONLY the bullet text, no explanation."""

        return self.generate(
            prompt=prompt,
            max_tokens=200,
            temperature=0.8,
            system="You are an expert resume writer specializing in ATS-optimized, achievement-focused bullet points."
        )

    def judge_bullets(
        self,
        bullets: List[Dict],
        jd_text: str,
        research_context: Dict
    ) -> Dict:
        """
        Judge multiple bullet variants and choose the best.

        Args:
            bullets: List of dicts with 'text' and 'source' keys
            jd_text: Job description text
            research_context: Research context

        Returns:
            Dict with 'winner', 'reason', 'winner_index'
        """
        bullet_list = "\n".join([
            f"VARIANT {i+1} ({bullet.get('source', 'unknown')}):\n{bullet['text']}\n"
            for i, bullet in enumerate(bullets)
        ])

        keywords = research_context.get('keywords', [])
        keyword_list = ", ".join([k['keyword'] for k in keywords[:10]])

        prompt = f"""Evaluate these resume bullet variants and choose the BEST one.

Target Job Keywords: {keyword_list}

Bullet Variants:
{bullet_list}

Evaluate each on:
1. Keyword alignment with target job
2. Specificity and quantifiable metrics
3. Strong action verb usage
4. Clarity and readability
5. Achievement focus

Choose the BEST variant.

Format your response EXACTLY as:
WINNER: [variant number 1-{len(bullets)}]
REASON: [1-2 sentence explanation]"""

        response = self.generate(
            prompt=prompt,
            max_tokens=150,
            temperature=0.3,
            system="You are an expert resume reviewer and ATS specialist."
        )

        # Parse response
        import re
        winner_match = re.search(r'WINNER:\s*(\d+)', response, re.IGNORECASE)
        reason_match = re.search(r'REASON:\s*(.+)', response, re.IGNORECASE | re.DOTALL)

        if winner_match:
            winner_idx = int(winner_match.group(1)) - 1
            if 0 <= winner_idx < len(bullets):
                return {
                    "winner": bullets[winner_idx]['text'],
                    "reason": reason_match.group(1).strip() if reason_match else "Selected as best match",
                    "winner_index": winner_idx,
                    "winner_source": bullets[winner_idx].get('source', 'unknown')
                }

        # Fallback to first bullet
        return {
            "winner": bullets[0]['text'],
            "reason": "Fallback selection",
            "winner_index": 0,
            "winner_source": bullets[0].get('source', 'unknown')
        }

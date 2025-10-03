"""
Dual sub-agent debate system for bullet proposal generation.
"""
import anthropic
import os
from typing import Dict, List


def generate_recency_biased_bullets(
    role_context: Dict,
    research_context: Dict,
    num_bullets: int = 3
) -> List[Dict]:
    """
    Generate bullets emphasizing recent trends and modern methodologies.

    Args:
        role_context: Dict with role_id, company, title, start, end, location
        research_context: Dict from researcher (keywords, skills, responsibilities, industry_terms)
        num_bullets: Number of bullet variants to generate

    Returns:
        List of dicts: [{"text": str, "source": "recency_biased"}, ...]
    """
    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY', ''))

    # Extract key info
    keywords = research_context.get('keywords', [])
    skills = research_context.get('required_skills', [])
    responsibilities = research_context.get('key_responsibilities', [])
    industry_terms = research_context.get('industry_terms', [])

    keyword_list = ", ".join([k['keyword'] for k in keywords[:10]])
    skills_list = ", ".join(skills)
    resp_list = ", ".join(responsibilities)
    terms_list = ", ".join(industry_terms)

    prompt = f"""You are a modern resume bullet writer emphasizing cutting-edge methodologies and recent trends.

Role: {role_context['title']} at {role_context['company']} ({role_context['start']} - {role_context.get('end', 'Present')})

Target Job Keywords: {keyword_list}
Required Skills: {skills_list}
Key Responsibilities: {resp_list}
Industry Terms: {terms_list}

Write {num_bullets} achievement-focused bullet points that:
1. Emphasize modern, data-driven approaches
2. Use metrics and quantifiable results
3. Highlight innovative tools, technologies, or methodologies
4. Match the target job keywords naturally
5. Start with strong action verbs (Led, Drove, Implemented, Engineered, etc.)

Format: Return ONLY the bullet points, one per line, starting with "•"

Example style:
• Drove 34% increase in enterprise pipeline by implementing MEDDIC qualification framework across 12-person sales team
• Engineered automated CRM workflow reducing sales cycle by 18 days through Salesforce integration with Outreach.io"""

    try:
        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = message.content[0].text
        bullets = []
        for line in response_text.split('\n'):
            line = line.strip()
            if line.startswith('•'):
                text = line[1:].strip()
                bullets.append({"text": text, "source": "recency_biased"})
            elif line and not line.startswith('#'):
                # Handle bullets without bullet character
                bullets.append({"text": line.strip(), "source": "recency_biased"})

        return bullets[:num_bullets]

    except Exception as e:
        print(f"Warning: Recency-biased generation failed: {e}")
        return []


def generate_standards_biased_bullets(
    role_context: Dict,
    research_context: Dict,
    num_bullets: int = 3
) -> List[Dict]:
    """
    Generate bullets emphasizing proven best practices and industry standards.

    Args:
        role_context: Dict with role_id, company, title, start, end, location
        research_context: Dict from researcher (keywords, skills, responsibilities, industry_terms)
        num_bullets: Number of bullet variants to generate

    Returns:
        List of dicts: [{"text": str, "source": "standards_biased"}, ...]
    """
    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY', ''))

    # Extract key info
    keywords = research_context.get('keywords', [])
    skills = research_context.get('required_skills', [])
    responsibilities = research_context.get('key_responsibilities', [])
    industry_terms = research_context.get('industry_terms', [])

    keyword_list = ", ".join([k['keyword'] for k in keywords[:10]])
    skills_list = ", ".join(skills)
    resp_list = ", ".join(responsibilities)
    terms_list = ", ".join(industry_terms)

    prompt = f"""You are a traditional resume bullet writer emphasizing proven methodologies and industry best practices.

Role: {role_context['title']} at {role_context['company']} ({role_context['start']} - {role_context.get('end', 'Present')})

Target Job Keywords: {keyword_list}
Required Skills: {skills_list}
Key Responsibilities: {resp_list}
Industry Terms: {terms_list}

Write {num_bullets} achievement-focused bullet points that:
1. Emphasize established, reliable methodologies
2. Use clear metrics and proven outcomes
3. Highlight core competencies and foundational skills
4. Match the target job keywords naturally
5. Start with strong action verbs (Managed, Achieved, Established, Delivered, etc.)

Format: Return ONLY the bullet points, one per line, starting with "•"

Example style:
• Managed $2.4M territory achieving 112% of quota through consistent prospecting and relationship building with C-suite executives
• Established enterprise sales process increasing close rate from 18% to 27% across 45+ opportunities"""

    try:
        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = message.content[0].text
        bullets = []
        for line in response_text.split('\n'):
            line = line.strip()
            if line.startswith('•'):
                text = line[1:].strip()
                bullets.append({"text": text, "source": "standards_biased"})
            elif line and not line.startswith('#'):
                # Handle bullets without bullet character
                bullets.append({"text": line.strip(), "source": "standards_biased"})

        return bullets[:num_bullets]

    except Exception as e:
        print(f"Warning: Standards-biased generation failed: {e}")
        return []


def run_debate(role_context: Dict, research_context: Dict) -> List[Dict]:
    """
    Run both sub-agents and return all proposed bullets.

    Returns:
        List of all bullets from both agents with source attribution
    """
    recency_bullets = generate_recency_biased_bullets(role_context, research_context, num_bullets=2)
    standards_bullets = generate_standards_biased_bullets(role_context, research_context, num_bullets=2)

    return recency_bullets + standards_bullets

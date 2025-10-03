"""
Generate Executive Summary and Statement of Qualifications based on JD analysis.
Produces multi-sentence summaries and 4-6 outcome-focused bullets.
"""
import re
from collections import Counter


def extract_top_keywords(jd: str, top_n: int = 8) -> list:
    """Extract top keywords from job description."""
    # Remove common words
    stopwords = {
        'the', 'and', 'or', 'is', 'are', 'was', 'were', 'will', 'be', 'to', 'of', 'in', 'for',
        'on', 'with', 'at', 'by', 'from', 'as', 'an', 'a', 'this', 'that', 'these', 'those',
        'our', 'we', 'you', 'your', 'have', 'has', 'can', 'should', 'would', 'could', 'may'
    }

    # Tokenize and clean
    words = re.findall(r'\b[a-zA-Z]{3,}\b', jd.lower())
    filtered = [w for w in words if w not in stopwords]

    # Count and return top keywords
    counter = Counter(filtered)
    return [word for word, count in counter.most_common(top_n)]


def generate_exec_and_soq(jd: str, company: str):
    """
    Generate Executive Summary (3-4 sentences) and Statement of Qualifications (4-6 bullets).

    Args:
        jd: Job description text
        company: Company name

    Returns:
        tuple: (exec_summary: str, soq: list of str)
    """
    # Extract top themes from JD
    keywords = extract_top_keywords(jd, top_n=8)

    # Build executive summary with JD themes
    themes_text = ", ".join(keywords[:4]) if len(keywords) >= 4 else "product strategy and execution"

    exec_summary = (
        f"Product leader with 6+ years driving measurable business outcomes in high-growth technology environments. "
        f"Proven expertise in {themes_text}, combining analytical rigor with cross-functional leadership. "
        f"Seeking to bring this experience to {company} to deliver data-informed product decisions and accelerate team velocity. "
        f"Track record of increasing key metrics through systematic experimentation and customer-centric design."
    )

    # Generate Statement of Qualifications (outcome-focused bullets)
    soq = [
        "Increased user activation by 18% through systematic onboarding optimization and A/B testing framework",
        "Reduced customer churn 12% YoY by building product-led customer success workflows and retention analytics",
        "Delivered 8 major roadmap initiatives on time by implementing agile ceremonies and OKR alignment across 3 teams",
        "Built end-to-end analytics infrastructure (Amplitude, SQL, dashboards) enabling real-time decision-making",
        "Led discovery and validation for $2M+ feature set through user research, prototyping, and stakeholder alignment",
        "Drove 25% improvement in team velocity by establishing clear prioritization framework and removing blockers"
    ]

    return exec_summary, soq

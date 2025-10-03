"""
JD keyword extraction and context research for bullet generation.
"""
import re
from collections import Counter
from typing import Dict, List
import anthropic
import os


STOP_WORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
    'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
    'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might',
    'must', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she',
    'it', 'we', 'they', 'what', 'which', 'who', 'when', 'where', 'why', 'how'
}


def extract_keywords(jd_text: str, top_n: int = 20) -> List[Dict[str, any]]:
    """
    Extract top keywords from JD text with importance scoring.

    Returns:
        List of dicts: [{"keyword": str, "weight": float, "count": int}, ...]
    """
    # Clean and tokenize
    text_lower = jd_text.lower()
    # Extract words and multi-word phrases
    words = re.findall(r'\b[a-z]{3,}\b', text_lower)

    # Filter stop words
    filtered = [w for w in words if w not in STOP_WORDS]

    # Count frequency
    word_counts = Counter(filtered)

    # Also extract common phrases (2-3 words)
    phrases = []
    words_list = text_lower.split()
    for i in range(len(words_list) - 1):
        two_word = f"{words_list[i]} {words_list[i+1]}"
        if all(w not in STOP_WORDS for w in two_word.split()):
            phrases.append(two_word)

    for i in range(len(words_list) - 2):
        three_word = f"{words_list[i]} {words_list[i+1]} {words_list[i+2]}"
        if all(w not in STOP_WORDS for w in three_word.split()):
            phrases.append(three_word)

    phrase_counts = Counter(phrases)

    # Combine and score
    all_terms = {}
    for word, count in word_counts.most_common(top_n):
        all_terms[word] = {"keyword": word, "count": count, "weight": count / len(filtered)}

    for phrase, count in phrase_counts.most_common(top_n // 2):
        if count >= 2:  # Only include phrases that appear at least twice
            all_terms[phrase] = {"keyword": phrase, "count": count, "weight": (count * 1.5) / len(filtered)}

    # Sort by weight
    sorted_terms = sorted(all_terms.values(), key=lambda x: x['weight'], reverse=True)
    return sorted_terms[:top_n]


def gather_research_context(jd_text: str, role_title: str, fast_model: str = "gpt-3.5-turbo") -> Dict:
    """
    Use fast LLM to extract structured context from JD.

    Returns:
        Dict with keys: keywords, required_skills, key_responsibilities, industry_terms
    """
    keywords = extract_keywords(jd_text, top_n=15)

    # Use LLM to extract structured information
    try:
        client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY', ''))

        prompt = f"""Analyze this job description for a {role_title} position and extract:

1. Top 5 required skills/qualifications
2. Top 5 key responsibilities
3. Industry-specific terms or methodologies mentioned

Job Description:
{jd_text[:2000]}

Return your analysis in this exact format:

SKILLS:
- skill 1
- skill 2
...

RESPONSIBILITIES:
- responsibility 1
- responsibility 2
...

INDUSTRY_TERMS:
- term 1
- term 2
..."""

        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = message.content[0].text

        # Parse response
        skills = []
        responsibilities = []
        industry_terms = []

        current_section = None
        for line in response_text.split('\n'):
            line = line.strip()
            if line.startswith('SKILLS:'):
                current_section = 'skills'
            elif line.startswith('RESPONSIBILITIES:'):
                current_section = 'responsibilities'
            elif line.startswith('INDUSTRY_TERMS:'):
                current_section = 'industry_terms'
            elif line.startswith('- '):
                item = line[2:].strip()
                if current_section == 'skills':
                    skills.append(item)
                elif current_section == 'responsibilities':
                    responsibilities.append(item)
                elif current_section == 'industry_terms':
                    industry_terms.append(item)

    except Exception as e:
        print(f"Warning: Research context extraction failed: {e}")
        skills = []
        responsibilities = []
        industry_terms = []

    return {
        "keywords": keywords,
        "required_skills": skills[:5],
        "key_responsibilities": responsibilities[:5],
        "industry_terms": industry_terms[:5]
    }

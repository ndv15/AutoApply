"""
Judge module for evaluating and selecting best bullet variants.
"""
import anthropic
import os
import re
from typing import Dict, List


def calculate_keyword_match(bullet_text: str, research_context: Dict) -> float:
    """
    Calculate keyword overlap score between bullet and JD keywords.

    Returns:
        Float between 0 and 1
    """
    keywords = research_context.get('keywords', [])
    if not keywords:
        return 0.0

    bullet_lower = bullet_text.lower()
    matched_count = 0
    total_weight = 0.0

    for kw_dict in keywords[:15]:  # Top 15 keywords
        keyword = kw_dict['keyword'].lower()
        weight = kw_dict['weight']
        total_weight += weight

        if keyword in bullet_lower:
            matched_count += weight

    return min(1.0, matched_count / total_weight) if total_weight > 0 else 0.0


def judge_bullets(bullet_variants: List[Dict], research_context: Dict, premium_model: str) -> Dict:
    """
    Use premium LLM to evaluate bullets and choose the best one.

    Args:
        bullet_variants: List of dicts with 'text' and 'source' keys
        research_context: Dict from researcher
        premium_model: Model ID for premium LLM

    Returns:
        Dict: {"winner": str, "reason": str, "keyword_scores": {...}, "votes": {...}}
    """
    if not bullet_variants:
        return {"winner": "", "reason": "No variants provided", "keyword_scores": {}, "votes": {}}

    # Calculate keyword match scores for each variant
    keyword_scores = {}
    for i, bullet in enumerate(bullet_variants):
        score = calculate_keyword_match(bullet['text'], research_context)
        keyword_scores[f"variant_{i}"] = score

    # Format bullets for judging
    bullet_list = "\n".join([
        f"VARIANT {i+1} ({bullet['source']}):\n{bullet['text']}\n"
        for i, bullet in enumerate(bullet_variants)
    ])

    # Extract research context
    keywords = research_context.get('keywords', [])
    skills = research_context.get('required_skills', [])
    responsibilities = research_context.get('key_responsibilities', [])

    keyword_list = ", ".join([k['keyword'] for k in keywords[:10]])
    skills_list = ", ".join(skills)
    resp_list = ", ".join(responsibilities)

    prompt = f"""You are an expert resume reviewer. Evaluate these bullet point variants and choose the BEST one.

Target Job Requirements:
- Keywords: {keyword_list}
- Skills: {skills_list}
- Responsibilities: {resp_list}

Bullet Variants:
{bullet_list}

Evaluate each variant on:
1. Keyword alignment with target job
2. Specificity and quantifiable metrics
3. Strong action verb usage
4. Clarity and readability
5. Achievement focus (not just responsibilities)

Choose the BEST variant and explain why in 1-2 sentences.

Format your response EXACTLY as:
WINNER: [variant number 1-{len(bullet_variants)}]
REASON: [your explanation]"""

    try:
        client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY', ''))
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = message.content[0].text

        # Parse response
        winner_match = re.search(r'WINNER:\s*(\d+)', response_text, re.IGNORECASE)
        reason_match = re.search(r'REASON:\s*(.+)', response_text, re.IGNORECASE | re.DOTALL)

        if winner_match:
            winner_idx = int(winner_match.group(1)) - 1
            if 0 <= winner_idx < len(bullet_variants):
                winner_text = bullet_variants[winner_idx]['text']
                reason = reason_match.group(1).strip() if reason_match else "Selected as best match"

                return {
                    "winner": winner_text,
                    "reason": reason,
                    "keyword_scores": keyword_scores,
                    "votes": {
                        "winner_index": winner_idx,
                        "winner_source": bullet_variants[winner_idx]['source']
                    }
                }

        # Fallback: Choose highest keyword score
        best_idx = max(range(len(bullet_variants)), key=lambda i: keyword_scores.get(f"variant_{i}", 0))
        return {
            "winner": bullet_variants[best_idx]['text'],
            "reason": "Selected based on keyword match score",
            "keyword_scores": keyword_scores,
            "votes": {
                "winner_index": best_idx,
                "winner_source": bullet_variants[best_idx]['source']
            }
        }

    except Exception as e:
        print(f"Warning: Judge evaluation failed: {e}")
        # Fallback to keyword-based selection
        best_idx = max(range(len(bullet_variants)), key=lambda i: keyword_scores.get(f"variant_{i}", 0))
        return {
            "winner": bullet_variants[best_idx]['text'],
            "reason": f"Fallback selection (error: {str(e)[:50]})",
            "keyword_scores": keyword_scores,
            "votes": {
                "winner_index": best_idx,
                "winner_source": bullet_variants[best_idx]['source']
            }
        }

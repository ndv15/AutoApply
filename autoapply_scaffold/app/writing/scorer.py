"""
Bullet scoring module: combines keyword and embedding similarity into 1-10 score.
"""
import re
from typing import Dict


def calculate_keyword_score(bullet_text: str, research_context: Dict) -> float:
    """
    Calculate keyword overlap score (0-1) based on weighted JD keywords.

    Args:
        bullet_text: The bullet text to score
        research_context: Dict from researcher with 'keywords' list

    Returns:
        Float between 0 and 1
    """
    keywords = research_context.get('keywords', [])
    if not keywords:
        return 0.5  # Neutral score if no keywords

    bullet_lower = bullet_text.lower()
    matched_weight = 0.0
    total_weight = 0.0

    for kw_dict in keywords[:15]:  # Top 15 keywords
        keyword = kw_dict['keyword'].lower()
        weight = kw_dict['weight']
        total_weight += weight

        # Check for exact match or word boundary match
        if keyword in bullet_lower:
            # Bonus for word boundary match (not just substring)
            if re.search(r'\b' + re.escape(keyword) + r'\b', bullet_lower):
                matched_weight += weight
            else:
                matched_weight += (weight * 0.7)  # Partial credit for substring match

    return min(1.0, matched_weight / total_weight) if total_weight > 0 else 0.5


def calculate_embedding_score(bullet_text: str, jd_text: str) -> float:
    """
    Calculate embedding similarity score (0-1).
    Currently returns neutral score since embeddings are disabled.

    Args:
        bullet_text: The bullet text to score
        jd_text: The job description text

    Returns:
        Float between 0 and 1 (currently always 0.5)
    """
    # TODO: Implement when embeddings are enabled in config
    # For now, return neutral score
    return 0.5


def calculate_final_score(
    bullet_text: str,
    jd_text: str,
    research_context: Dict,
    use_embeddings: bool = False,
    weights: Dict = None
) -> int:
    """
    Calculate final 1-10 compatibility score.

    Args:
        bullet_text: The bullet to score
        jd_text: The job description text
        research_context: Dict from researcher
        use_embeddings: Whether to use embedding similarity
        weights: Dict with 'keywords' and 'embeddings' weights (default: 0.6, 0.4)

    Returns:
        Integer score from 1 to 10
    """
    if weights is None:
        weights = {'keywords': 0.6, 'embeddings': 0.4}

    # Calculate component scores
    keyword_score = calculate_keyword_score(bullet_text, research_context)

    if use_embeddings:
        embed_score = calculate_embedding_score(bullet_text, jd_text)
        final_score = (
            weights['keywords'] * keyword_score +
            weights['embeddings'] * embed_score
        )
    else:
        # If embeddings disabled, use keyword score only
        final_score = keyword_score

    # Map 0-1 score to 1-10 scale
    score_1_10 = max(1, round(final_score * 10))
    return min(10, score_1_10)  # Cap at 10


def score_bullet(
    bullet_text: str,
    jd_text: str,
    research_context: Dict,
    config: Dict = None
) -> Dict:
    """
    Score a bullet and return detailed breakdown.

    Args:
        bullet_text: The bullet to score
        jd_text: The job description text
        research_context: Dict from researcher
        config: Dict with 'use_embeddings' and 'weights' keys

    Returns:
        Dict: {
            "score_1_10": int,
            "keyword_score": float,
            "embedding_score": float (if enabled),
            "details": str
        }
    """
    if config is None:
        config = {'use_embeddings': False, 'weights': {'keywords': 0.6, 'embeddings': 0.4}}

    keyword_score = calculate_keyword_score(bullet_text, research_context)
    use_embeddings = config.get('use_embeddings', False)
    weights = config.get('weights', {'keywords': 0.6, 'embeddings': 0.4})

    result = {
        "keyword_score": round(keyword_score, 2),
        "details": f"Keyword match: {int(keyword_score * 100)}%"
    }

    if use_embeddings:
        embed_score = calculate_embedding_score(bullet_text, jd_text)
        result["embedding_score"] = round(embed_score, 2)
        result["details"] += f" | Embedding similarity: {int(embed_score * 100)}%"

    final_score = calculate_final_score(
        bullet_text,
        jd_text,
        research_context,
        use_embeddings,
        weights
    )

    result["score_1_10"] = final_score
    return result

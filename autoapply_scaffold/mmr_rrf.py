"""
MMR (Maximal Marginal Relevance) and RRF (Reciprocal Rank Fusion) for diverse suggestion ranking.

MMR ensures diversity by penalizing candidates similar to already-selected ones.
RRF fuses multiple ranking signals (Cohere semantic, keyword match, etc.) into single score.
"""
import re
from typing import List, Dict, Tuple, Callable
from collections import Counter


def compute_trigram_similarity(text1: str, text2: str) -> float:
    """
    Calculate Jaccard similarity of character trigrams.

    Args:
        text1: First text
        text2: Second text

    Returns:
        Similarity score 0.0-1.0
    """
    def get_trigrams(s: str) -> set:
        s = s.lower().strip()
        return {s[i:i+3] for i in range(len(s)-2)}

    t1 = get_trigrams(text1)
    t2 = get_trigrams(text2)

    if not t1 or not t2:
        return 0.0

    intersection = len(t1 & t2)
    union = len(t1 | t2)

    return intersection / union if union > 0 else 0.0


def compute_mmr(
    candidates: List[Dict],
    lambda_param: float = 0.7,
    sim_threshold: float = 0.90,
    max_results: int = 10
) -> List[Dict]:
    """
    Apply Maximal Marginal Relevance to get diverse suggestions.

    MMR formula: MMR(D_i) = λ * Rel(D_i) - (1-λ) * max_j∈S Sim(D_i, D_j)
    where S is the set of already-selected documents.

    Args:
        candidates: List of dicts with 'text' and 'score' fields
        lambda_param: Trade-off between relevance (1.0) and diversity (0.0)
        sim_threshold: Minimum similarity to consider for penalty
        max_results: Maximum number of results to return

    Returns:
        Reranked list of candidates (most diverse first)
    """
    if not candidates:
        return []

    # Normalize scores to 0-1 range
    max_score = max(c.get('score', 0) for c in candidates)
    min_score = min(c.get('score', 0) for c in candidates)
    score_range = max_score - min_score if max_score > min_score else 1.0

    for c in candidates:
        raw_score = c.get('score', 0)
        c['_normalized_score'] = (raw_score - min_score) / score_range if score_range > 0 else 0.5

    selected = []
    remaining = candidates[:]

    while remaining and len(selected) < max_results:
        best_candidate = None
        best_mmr_score = -float('inf')

        for candidate in remaining:
            # Relevance component
            relevance = candidate['_normalized_score']

            # Diversity component (penalty for similarity to selected)
            max_similarity = 0.0
            if selected:
                for selected_doc in selected:
                    sim = compute_trigram_similarity(
                        candidate.get('text', ''),
                        selected_doc.get('text', '')
                    )
                    if sim > sim_threshold:
                        max_similarity = max(max_similarity, sim)

            # MMR score
            mmr_score = lambda_param * relevance - (1 - lambda_param) * max_similarity

            if mmr_score > best_mmr_score:
                best_mmr_score = mmr_score
                best_candidate = candidate

        if best_candidate:
            selected.append(best_candidate)
            remaining.remove(best_candidate)
            best_candidate['mmr_score'] = best_mmr_score

    return selected


def compute_rrf(
    rankings: List[Tuple[str, List[Dict]]],
    k: int = 60
) -> List[Dict]:
    """
    Reciprocal Rank Fusion - combines multiple ranking signals.

    RRF formula: RRF(d) = Σ_r 1 / (k + rank_r(d))
    where r ranges over all ranking sources.

    Args:
        rankings: List of (source_name, ranked_list) tuples
                 Each ranked_list is list of dicts with 'text' field
        k: Constant for RRF formula (default 60)

    Returns:
        Fused ranking (highest RRF score first)
    """
    # Build RRF scores (use text as key since we don't have stable IDs yet)
    rrf_scores = {}
    all_candidates = {}

    for source_name, ranked_list in rankings:
        for rank, candidate in enumerate(ranked_list, start=1):
            # Use text as unique key
            cand_key = candidate.get('text', '')[:100]  # Use first 100 chars as key

            # Store candidate
            if cand_key not in all_candidates:
                all_candidates[cand_key] = candidate

            # Add RRF score
            if cand_key not in rrf_scores:
                rrf_scores[cand_key] = 0.0

            rrf_scores[cand_key] += 1.0 / (k + rank)

    # Sort by RRF score
    sorted_keys = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

    # Build result list
    result = []
    for cand_key in sorted_keys:
        candidate = all_candidates[cand_key].copy()
        candidate['rrf_score'] = rrf_scores[cand_key]
        result.append(candidate)

    return result


def extract_keywords(text: str, top_n: int = 10) -> List[str]:
    """
    Extract top keywords from text for keyword-weighted ranking.

    Args:
        text: Input text
        top_n: Number of top keywords to return

    Returns:
        List of keywords sorted by frequency
    """
    # Stopwords
    stopwords = {
        'the', 'and', 'or', 'is', 'are', 'was', 'were', 'will', 'be', 'to', 'of', 'in', 'for',
        'on', 'with', 'at', 'by', 'from', 'as', 'an', 'a', 'this', 'that', 'these', 'those',
        'it', 'its', 'they', 'them', 'their', 'we', 'our', 'you', 'your'
    }

    # Extract words (4+ chars, alphanumeric)
    words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
    filtered = [w for w in words if w not in stopwords]

    # Count and return top N
    counter = Counter(filtered)
    return [word for word, count in counter.most_common(top_n)]


def compute_keyword_match_score(bullet_text: str, jd_keywords: List[str]) -> float:
    """
    Calculate keyword match score for a bullet against JD keywords.

    Args:
        bullet_text: Bullet text
        jd_keywords: List of important JD keywords

    Returns:
        Match score 0.0-1.0
    """
    if not jd_keywords:
        return 0.5

    bullet_lower = bullet_text.lower()
    matches = sum(1 for kw in jd_keywords if kw.lower() in bullet_lower)

    return matches / len(jd_keywords)

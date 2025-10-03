"""
Propose experience bullets for a given job based on employment history and JD.
All bullets default to PENDING status. User must explicitly approve.
"""
import re
import uuid
import json
import hashlib
from pathlib import Path
from collections import Counter
from typing import Dict, List, Optional
from ..llm.router import LLMRouter
from ..ranking.providers.cohere import score_bullets
from ...mmr_rrf import compute_mmr, compute_rrf, extract_keywords, compute_keyword_match_score
from ..research.cache import get_cached_research, save_cached_research


def extract_jd_themes(jd: str, top_n: int = 5) -> list:
    """Extract key themes from job description."""
    stopwords = {
        'the', 'and', 'or', 'is', 'are', 'was', 'were', 'will', 'be', 'to', 'of', 'in', 'for',
        'on', 'with', 'at', 'by', 'from', 'as', 'an', 'a', 'this', 'that'
    }
    words = re.findall(r'\b[a-zA-Z]{4,}\b', jd.lower())
    filtered = [w for w in words if w not in stopwords]
    counter = Counter(filtered)
    return [word for word, count in counter.most_common(top_n)]


def extract_metrics(text: str) -> List[str]:
    """Extract numeric metrics from text."""
    patterns = [
        r'\$[\d,]+(?:\s*-\s*\$[\d,]+)?',  # Currency ranges
        r'\d+(?:\.\d+)?%(?:\s*-\s*\d+(?:\.\d+)?%)?',  # Percentage ranges
        r'\d+(?:\s*-\s*\d+)?(?=\s+(?:users|customers|clients|deals|sales|leads))',  # Count ranges
    ]
    metrics = []
    for pattern in patterns:
        metrics.extend(re.findall(pattern, text))
    return metrics

def has_amot_format(text: str, return_reason: bool = False):
    """
    Check if text follows Action-Metric-Outcome-Tool format.

    Args:
        text: Bullet text to validate
        return_reason: If True, returns (bool, str) with failure reason

    Returns:
        bool if return_reason=False, else (bool, str) tuple
    """
    failures = []

    # Action: Starts with strong verb
    if not re.match(r'^(?:Led|Drove|Increased|Implemented|Developed|Created|Built|Managed|Achieved|Generated|Closed|Expanded)', text):
        failures.append("Missing strong action verb")

    # Metric: Contains at least one numeric value
    if not extract_metrics(text):
        failures.append("No quantified metric (%, $, count)")

    # Outcome: Contains business impact words
    impact_words = ['resulting', 'leading to', 'achieving', 'generating', 'improving', 'reducing', 'driving']
    if not any(word in text.lower() for word in impact_words):
        failures.append("No outcome phrase (resulting/achieving/driving)")

    # Tool/Context: Contains specific platform/tool/method
    tools_pattern = r'using|via|through|leveraging|with'
    if not re.search(tools_pattern, text, re.IGNORECASE):
        failures.append("No tool/method mentioned")

    if return_reason:
        return (len(failures) == 0, "; ".join(failures) if failures else "PASS")

    return len(failures) == 0

def inject_metrics(text: str) -> str:
    """Insert placeholder metrics if none exist."""
    if extract_metrics(text):
        return text
        
    # Common metric patterns to inject
    patterns = [
        (r'(increased|improved|enhanced|grew)\s+(\w+)', r'\1 \2 by X-Y%'),
        (r'(generated|created|produced)\s+(\w+)', r'\1 $A-$B in \2'),
        (r'(managed|led|supervised)\s+team', r'\1 team of X-Y members'),
    ]
    
    for pattern, replacement in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            
    return text

def generate_next_suggestion(job_id: str, role_key: str, jd_text: str, role_context: Dict) -> Optional[Dict]:
    """
    Generate next suggestion for review using full pipeline:
    1. Over-generate 20-30 candidates
    2. Score with Cohere rerank
    3. Apply MMR for diversity
    4. Apply RRF with keyword weighting
    5. Return top 1
    """
    router = LLMRouter()

    # Step 1: Over-generate candidates (20-30)
    # Note: Research is handled internally by router.generate_suggestions()
    candidates = []
    for _ in range(3):  # Try up to 3 rounds
        new_candidates = router.generate_suggestions(
            role_context=role_context,
            jd_text=jd_text,
            research_context={},  # Router will handle Perplexity research
            n=10
        )

        # Enhance with metrics + STRICT validation
        for c in new_candidates:
            text = c.get("text", "")

            # Try to inject metrics if missing
            if not has_amot_format(text):
                text = inject_metrics(text)
                c["text"] = text

            # Re-validate - only accept AMOT-compliant bullets
            is_valid, reason = has_amot_format(text, return_reason=True)
            if is_valid:
                candidates.append(c)
            else:
                # Reject non-AMOT with reason
                print(f"[REJECTED NON-AMOT] {text[:60]}... ({reason})")

        if len(candidates) >= 20:
            break

    if not candidates:
        return None

    # Step 2: Score with Cohere rerank
    scored_candidates = score_bullets(jd_text, candidates)

    # Step 3: Apply MMR for diversity
    mmr_candidates = compute_mmr(
        scored_candidates,
        lambda_param=0.7,
        sim_threshold=0.90,
        max_results=10
    )

    # Step 4: Apply RRF with keyword weighting
    jd_keywords = extract_keywords(jd_text, top_n=15)

    # Build keyword-weighted ranking
    keyword_ranked = sorted(
        mmr_candidates,
        key=lambda x: compute_keyword_match_score(x.get('text', ''), jd_keywords),
        reverse=True
    )

    # Fuse Cohere + keyword rankings using RRF
    rankings = [
        ('cohere_mmr', mmr_candidates),
        ('keyword_match', keyword_ranked)
    ]

    fused = compute_rrf(rankings, k=60)

    # Step 5: Return top candidate
    if fused:
        suggestion = fused[0]
        suggestion['id'] = str(uuid.uuid4())
        suggestion['role_key'] = role_key
        suggestion['created_at'] = str(uuid.uuid1().time)
        return suggestion

    return None

def get_role_quota(role_key: str) -> int:
    """Get the target number of bullets for a role."""
    quotas = {
        'ccs': 4,
        'brightspeed_ii': 4,
        'brightspeed_i': 4,
        'virsatel': 3
    }
    return quotas.get(role_key, 3)  # Default to 3

def propose_experience_bullets(history, jd):
    """
    Generate experience bullets for each role in employment history.

    All bullets start with status='PENDING'. User must explicitly approve.
    Bullets with inferred metrics are marked synth_metric=True.

    Args:
        history: List of employment history dicts with role_id, company, title
        jd: Job description text

    Returns:
        dict: {role_id: [bullet_dict, ...]}
              Each bullet_dict has: id, text, synth_metric, status, confidence
    """
    themes = extract_jd_themes(jd, top_n=5)
    theme_keywords = themes[:3]

    results = {}
    for role in history:
        role_id = role['role_id']
        company = role.get('company', '')
        title = role.get('title', '')
        
        # Role-specific bullet templates based on job title
        if 'Sales Manager' in title:
            bullets = [
                {
                    'id': f'{role_id}-b1',
                    'text': f'Led team of 8 Sales Representatives achieving 115% of team quota through strategic territory planning and deal coaching',
                    'synth_metric': True,
                    'status': 'PENDING',
                    'confidence': 0.92
                },
                {
                    'id': f'{role_id}-b2',
                    'text': f'Implemented enhanced MEDDIC qualification process improving win rates by 22% and reducing sales cycle by 45 days',
                    'synth_metric': True,
                    'status': 'PENDING',
                    'confidence': 0.89
                },
                {
                    'id': f'{role_id}-b3',
                    'text': f'Established new partner channel program generating $2.5M in incremental pipeline within first 6 months',
                    'synth_metric': True,
                    'status': 'PENDING',
                    'confidence': 0.87
                }
            ]
        elif 'Enterprise Account Manager' in title:
            bullets = [
                {
                    'id': f'{role_id}-b1',
                    'text': f'Exceeded annual quota 125% managing $12M territory through strategic account planning and C-level relationships',
                    'synth_metric': True,
                    'status': 'PENDING',
                    'confidence': 0.94
                },
                {
                    'id': f'{role_id}-b2',
                    'text': f'Closed largest deal in company history ($2.8M) through multi-threaded approach and executive sponsorship',
                    'synth_metric': True,
                    'status': 'PENDING',
                    'confidence': 0.91
                },
                {
                    'id': f'{role_id}-b3',
                    'text': f'Built $8M+ pipeline from outbound prospecting leveraging industry insights and personalized account strategies',
                    'synth_metric': True,
                    'status': 'PENDING',
                    'confidence': 0.88
                }
            ]
            if 'II' in title:  # Additional bullet for senior level
                bullets.append({
                    'id': f'{role_id}-b4',
                    'text': f'Mentored 4 new Account Executives achieving 85%+ quota attainment through deal strategy and MEDDIC coaching',
                    'synth_metric': True,
                    'status': 'PENDING',
                    'confidence': 0.86
                })
        else:  # Account Executive
            bullets = [
                {
                    'id': f'{role_id}-b1',
                    'text': f'Ranked #1 Account Executive achieving 147% of quota ($3.2M) through consultative enterprise sales approach',
                    'synth_metric': True,
                    'status': 'PENDING',
                    'confidence': 0.93
                },
                {
                    'id': f'{role_id}-b2',
                    'text': f'Generated 60% of opportunities through strategic prospecting and industry-focused outbound campaigns',
                    'synth_metric': True,
                    'status': 'PENDING',
                    'confidence': 0.89
                },
                {
                    'id': f'{role_id}-b3',
                    'text': f'Maintained 92% customer retention rate through quarterly business reviews and proactive account management',
                    'synth_metric': True,
                    'status': 'PENDING',
                    'confidence': 0.87
                }
            ]

        # Add awards if present
        if role.get('awards'):
            award_text = ' | '.join(role['awards'])
            bullets.insert(0, {
                'id': f'{role_id}-awards',
                'text': f'🏆 {award_text}',
                'synth_metric': False,
                'status': 'PENDING',
                'confidence': 1.0
            })

        results[role_id] = bullets

    return results


def _get_suggestion_history_path(job_id: str, role_id: str) -> Path:
    """Get path to suggestion history file."""
    history_dir = Path("out/suggestion_history")
    history_dir.mkdir(parents=True, exist_ok=True)
    return history_dir / f"{job_id}_{role_id}.json"


def _load_suggestion_history(job_id: str, role_id: str) -> set:
    """Load set of previously generated suggestion texts."""
    history_path = _get_suggestion_history_path(job_id, role_id)
    if history_path.exists():
        data = json.loads(history_path.read_text())
        return set(data.get('suggestions', []))
    return set()


def _save_suggestion(job_id: str, role_id: str, suggestion_text: str):
    """Save a new suggestion to history."""
    history_path = _get_suggestion_history_path(job_id, role_id)
    history = _load_suggestion_history(job_id, role_id)
    history.add(suggestion_text)
    history_path.write_text(json.dumps({
        'suggestions': list(history)
    }, indent=2))


def generate_suggestions(
    job_id: str,
    role_key: str,
    jd_text: str,
    role_context: Dict,
    existing_bullets: list = None,
    config: Dict = None,
    n: int = 3
) -> List[Dict]:
    """
    Multi-LLM pipeline to generate N bullet suggestions using LLMRouter.

    Pipeline: perplexity → claude → gpt → judge → gemini? → cohere

    Args:
        job_id: Job ID for tracking
        role_key: Role identifier (e.g., 'ccs-2025')
        jd_text: Full job description text
        role_context: Dict with role_id, company, title, start, end, location
        existing_bullets: List of already approved bullets for this role
        config: Full config dict from config.yaml
        n: Number of suggestions to generate (default 3)

    Returns:
        List[Dict]: [
            {
                "id": str,
                "text": str,
                "score_1_10": int,
                "model_used": str,
                "citations": List[str],
                "source": {...}
            },
            ...
        ]
    """
    if config is None:
        from ..config import load_settings
        config = load_settings().dict()

    try:
        # Initialize LLMRouter (loads config from environment)
        router = LLMRouter()

        # Load suggestion history to avoid repeats
        history = _load_suggestion_history(job_id, role_key)

        # Generate suggestions using router
        suggestions = router.generate_suggestions(
            role_context=role_context,
            jd_text=jd_text,
            research_context=None,  # Router handles research internally
            n=n,
            use_perplexity=config.get('research', {}).get('perplexity', {}).get('enabled', True)
        )

        # Filter out any duplicates from history
        filtered_suggestions = []
        for sugg in suggestions:
            if sugg['text'] not in history:
                filtered_suggestions.append(sugg)
                _save_suggestion(job_id, role_key, sugg['text'])

        # If we filtered too many, generate more
        while len(filtered_suggestions) < n and len(filtered_suggestions) < len(suggestions) * 2:
            additional = router.generate_suggestions(
                role_context=role_context,
                jd_text=jd_text,
                research_context=None,
                n=1,
                use_perplexity=False  # Skip research on retry
            )
            for sugg in additional:
                if sugg['text'] not in history:
                    filtered_suggestions.append(sugg)
                    _save_suggestion(job_id, role_key, sugg['text'])
                    if len(filtered_suggestions) >= n:
                        break

        return filtered_suggestions[:n]

    except Exception as e:
        print(f"Error in generate_suggestions: {e}")
        import traceback
        traceback.print_exc()

        # Fallback suggestions
        fallback = []
        for i in range(n):
            fallback.append({
                "id": str(uuid.uuid4())[:8],
                "text": "Achieved significant results through strategic planning and execution",
                "score_1_10": 5,
                "model_used": "fallback",
                "citations": [],
                "source": {
                    "error": str(e)[:100]
                }
            })
        return fallback


def generate_suggestion(
    job_id: str,
    role_key: str,
    jd_text: str,
    role_context: Dict,
    existing_bullets: list = None,
    fast_model: str = "gpt-3.5-turbo",
    premium_model: str = "claude-3-5-sonnet-20241022",
    config: Dict = None
) -> Dict:
    """
    Legacy single-suggestion generator for backwards compatibility.
    Now wraps generate_suggestions() and returns first result.
    """
    suggestions = generate_suggestions(
        job_id=job_id,
        role_key=role_key,
        jd_text=jd_text,
        role_context=role_context,
        existing_bullets=existing_bullets,
        config=config,
        n=1
    )
    return suggestions[0] if suggestions else {
        "id": str(uuid.uuid4())[:8],
        "text": "Achieved significant results through strategic planning and execution",
        "score_1_10": 5,
        "model_used": "fallback",
        "citations": [],
        "source": {"error": "No suggestions generated"}
    }

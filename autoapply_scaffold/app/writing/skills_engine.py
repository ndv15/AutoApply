"""
Skills suggestion engine with focus on sales and business skills.
Auto-approval only for exact matches above threshold from config.
"""
import re
from typing import Dict, List, Set, Tuple
from pathlib import Path
import yaml


def extract_skills_from_jd(jd: str) -> Set[str]:
    """Extract potential skill phrases from job description."""
    # Match multi-word skills (2-4 words) and single words (3+ chars)
    skill_patterns = [
        r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}\b',  # Multi-word capitalized phrases
        r'\b[A-Z]{2,}\b',  # Acronyms
        r'\b[A-Za-z]+(?:[/-][A-Za-z]+)+\b',  # Hyphenated/slashed terms
        r'\b[A-Za-z]{3,}\b'  # Single words
    ]
    
    skills = set()
    for pattern in skill_patterns:
        matches = re.findall(pattern, jd)
        skills.update(matches)
    return skills


def propose_skills(jd: str, registry: dict) -> Tuple[List, List[Dict]]:
    """
    Propose skills based on JD analysis and registry.
    Auto-approve only exact registry matches above threshold from config.

    Args:
        jd: Job description text
        registry: Dict with approved/rejected skills, aliases, and metadata

    Returns:
        tuple: (auto_added: list of skills, needs_confirmation: list of dicts)
        Each needs_confirmation item has: skill, reason, match_type, confidence
    """
    # Load thresholds from config
    config_path = Path("config.yaml")
    thresholds = {'auto_approve_skill': 0.95}
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f)
            thresholds = config.get('thresholds', thresholds)

    approved = set(registry.get('approved', []))
    rejected = set(registry.get('rejected', []))
    aliases = registry.get('aliases', {})

    auto_added = []

    # Extract skills from JD
    jd_skills = extract_skills_from_jd(jd)
    
    # Sales-specific skill categories
    skill_categories = {
        'methodology': {
            'MEDDIC', 'MEDDICC', 'SPIN', 'Challenger', 'Solution Selling',
            'Account Planning', 'Territory Planning'
        },
        'tools': {
            'Salesforce', 'SFDC', 'CRM', 'Outreach', 'SalesLoft', 'LinkedIn Sales Navigator',
            'DocuSign', 'CPQ', 'Slack'
        },
        'metrics': {
            'Quota', 'Pipeline', 'Revenue', 'ARR', 'MRR', 'ACV', 'TCV',
            'Win Rate', 'Conversion Rate', 'Churn Rate'
        },
        'activities': {
            'Enterprise Sales', 'Account Management', 'Solution Architecture',
            'Contract Negotiation', 'RFP', 'POC', 'Executive Presentations'
        }
    }

    suggestions = []

    # 1. Check direct matches from JD
    for skill in jd_skills:
        if skill not in approved and skill not in rejected:
            # Check if skill is in registry - if yes, auto-approve with high confidence
            if skill in registry.get('approved', []):
                confidence = 1.0  # Exact match from registry
                if confidence >= thresholds.get('auto_approve_skill', 0.95):
                    auto_added.append(skill)
                    continue

            # Determine category for context
            category = next(
                (cat for cat, skills in skill_categories.items() if skill in skills),
                'general'
            )
            suggestions.append({
                'skill': skill,
                'reason': f'Required in job description ({category})',
                'match_type': 'direct',
                'confidence': 0.95
            })

    # 2. Check alias matches
    for skill_key, skill_aliases in aliases.items():
        if skill_key not in approved and skill_key not in rejected:
            for alias in skill_aliases:
                if alias.lower() in jd.lower():
                    suggestions.append({
                        'skill': skill_key,
                        'reason': f'Matched alternative term: {alias}',
                        'match_type': 'alias',
                        'confidence': 0.85
                    })
                    break

    # 3. Suggest complementary skills based on role patterns
    role_indicators = {
        'manager': {'Leadership', 'Team Development', 'Performance Management'},
        'enterprise': {'C-Level Selling', 'Complex Deal Strategy', 'Executive Presence'},
        'sales': {'Pipeline Management', 'Revenue Forecasting', 'Account Strategy'}
    }

    for role, skills in role_indicators.items():
        if role.lower() in jd.lower():
            for skill in skills:
                if skill not in approved and skill not in rejected:
                    suggestions.append({
                        'skill': skill,
                        'reason': f'Common requirement for {role.title()} roles',
                        'match_type': 'inferred',
                        'confidence': 0.75
                    })

    # Deduplicate and sort by confidence
    seen = set(auto_added)  # Don't re-suggest auto-added skills
    unique_suggestions = []
    for sugg in sorted(suggestions, key=lambda x: x['confidence'], reverse=True):
        if sugg['skill'] not in seen and sugg['skill'] not in rejected:
            seen.add(sugg['skill'])
            unique_suggestions.append(sugg)

    # Limit to most relevant suggestions
    needs_confirmation = unique_suggestions[:12]

    return auto_added, needs_confirmation


def format_skills_for_resume(skills: list, jd_text: str = "", max_categories: int = 4) -> list:
    """
    Format skills into 3-4 category lines with pipe separators.

    Args:
        skills: List of skill strings
        jd_text: Job description (for keyword extraction)
        max_categories: Max lines to output (default 4)

    Returns:
        List of formatted lines: ["Category: skill1 | skill2", ...]
    """
    from collections import defaultdict

    # Auto-categorize skills
    categorized = defaultdict(list)

    for skill in skills:
        skill_lower = skill.lower()

        # Sales methodologies
        if any(term in skill_lower for term in ['meddic', 'spin', 'challenger', 'sandler', 'qualification', 'forecasting', 'territory', 'pipeline', 'prospecting', 'negotiation']):
            categorized['Sales Methodologies & Strategy'].append(skill)

        # CRM/Tech tools
        elif any(term in skill_lower for term in ['salesforce', 'crm', 'hubspot', 'outreach', 'salesloft', 'sql', 'amplitude', 'analytics']):
            categorized['CRM Systems & Digital Prospecting Tools'].append(skill)

        # Business/Leadership
        elif any(term in skill_lower for term in ['leadership', 'executive', 'team', 'coaching', 'training', 'management']):
            categorized['Leadership & Business Development'].append(skill)

        # Catchall
        else:
            categorized['Core Sales Competencies'].append(skill)

    # Build lines (max 4 categories)
    lines = []
    for category, items in list(categorized.items())[:max_categories]:
        if items:
            lines.append(f"{category}: {' | '.join(sorted(items))}")

    return lines

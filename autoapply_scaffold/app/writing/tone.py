"""
Tone critic for human-friendly rewrites and variety.
"""
import anthropic
import os
from typing import Dict, Set


# Track verbs used across all bullets to ensure variety
_USED_VERBS: Set[str] = set()


def reset_verb_tracking():
    """Reset verb tracking (call at start of new job review)."""
    global _USED_VERBS
    _USED_VERBS = set()


def extract_first_verb(bullet_text: str) -> str:
    """Extract the first word (action verb) from bullet text."""
    words = bullet_text.strip().split()
    return words[0] if words else ""


def polish_tone(bullet_text: str, premium_model: str, existing_bullets: list = None) -> str:
    """
    Use premium LLM to rewrite bullet for clarity, human tone, and variety.

    Args:
        bullet_text: The bullet text to polish
        premium_model: Model ID for premium LLM
        existing_bullets: List of other approved bullets to avoid repetition

    Returns:
        Polished bullet text
    """
    global _USED_VERBS

    # Track verb from input bullet
    current_verb = extract_first_verb(bullet_text)

    # Build list of verbs to avoid
    verbs_to_avoid = list(_USED_VERBS)
    if existing_bullets:
        for bullet in existing_bullets:
            if isinstance(bullet, dict):
                text = bullet.get('text', '')
            else:
                text = str(bullet)
            verb = extract_first_verb(text)
            if verb:
                verbs_to_avoid.append(verb)

    avoid_list = ", ".join(verbs_to_avoid[:10]) if verbs_to_avoid else "none"

    prompt = f"""You are a professional resume editor. Polish this bullet point for maximum clarity and human readability.

Original bullet:
{bullet_text}

Requirements:
1. Keep the same core achievement and metrics
2. Use clear, professional language (avoid jargon unless industry-standard)
3. Ensure strong action verb start
4. Avoid these already-used verbs: {avoid_list}
5. Keep it concise (under 150 characters if possible)
6. Make it sound natural and achievement-focused

Return ONLY the polished bullet text, no explanations."""

    try:
        client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY', ''))
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        )

        polished_text = message.content[0].text.strip()

        # Remove bullet character if LLM added it
        if polished_text.startswith('•'):
            polished_text = polished_text[1:].strip()
        if polished_text.startswith('-'):
            polished_text = polished_text[1:].strip()

        # Track the new verb
        new_verb = extract_first_verb(polished_text)
        if new_verb:
            _USED_VERBS.add(new_verb)

        return polished_text

    except Exception as e:
        print(f"Warning: Tone polishing failed: {e}")
        # Return original if polishing fails
        if current_verb:
            _USED_VERBS.add(current_verb)
        return bullet_text

"""
Multi-LLM orchestration router.

Flow: Claude (primary) -> GPT (counter) -> Judge -> optional Gemini (tie-breaker)
Scoring: 0.5xCohere-Rerank + 0.2xkeyword + 0.2xreadability + 0.1xcitations
"""
import uuid
from typing import Dict, List, Optional
from .providers.anthropic import AnthropicProvider
from .providers.openai import OpenAIProvider
from .providers.gemini import GeminiProvider
from ..research.providers.perplexity import PerplexityProvider
from ..research.cache import get_cached_research, save_cached_research
from ..ranking.providers.cohere import CohereProvider


class LLMRouter:
    """Orchestrates multiple LLM providers for bullet generation."""

    def __init__(self):
        """Initialize all providers."""
        try:
            self.claude = AnthropicProvider()
        except:
            self.claude = None
            print("Warning: Claude provider not available")

        try:
            self.gpt = OpenAIProvider()
        except:
            self.gpt = None
            print("Warning: OpenAI provider not available")

        try:
            self.gemini = GeminiProvider()
        except:
            self.gemini = None
            print("Warning: Gemini provider not available")

        try:
            self.perplexity = PerplexityProvider()
        except:
            self.perplexity = None
            print("Warning: Perplexity provider not available")

        try:
            self.cohere = CohereProvider()
        except:
            self.cohere = None
            print("Warning: Cohere provider not available")

        # Track which provider was used for each suggestion
        self.provider_history = []

    def generate_suggestions(
        self,
        role_context: Dict,
        jd_text: str,
        research_context: Dict,
        n: int = 3,
        use_perplexity: bool = True
    ) -> List[Dict]:
        """
        Generate N bullet suggestions using multi-LLM flow.

        Flow:
        1. Optional: Perplexity research for context
        2. Claude generates primary bullet
        3. GPT generates counter-perspective bullet
        4. Claude judges and picks winner
        5. If scores are close/low, Gemini provides tie-breaker
        6. Cohere ranks all bullets
        7. Return top N with scores

        Args:
            role_context: Dict with role info
            jd_text: Job description
            research_context: Existing research context
            n: Number of suggestions to return
            use_perplexity: Whether to use Perplexity research

        Returns:
            List of suggestion dicts with text, score_1_10, source, citations
        """
        # Step 1: Enhance research with Perplexity (optional, with caching)
        # IMPORTANT: Cache by JD hash to share research across all roles for same job
        citations = []
        if use_perplexity and self.perplexity:
            try:
                # Try to get from cache first (keyed by JD, not role)
                cached_result = get_cached_research(jd_text, cache_ttl=3600)

                if cached_result:
                    print(f"✓ Using cached Perplexity research (shared across all roles)")
                    research_context['perplexity_insights'] = cached_result.get('answer', '')
                    citations = cached_result.get('citations', [])
                else:
                    # Use generic job market research instead of role-specific
                    # This allows all 4 roles to share the same Perplexity call
                    print("-> Calling Perplexity API for job description research...")
                    perp_result = self.perplexity.research_role_metrics(jd_text[:500])  # Use JD snippet, not role title
                    research_context['perplexity_insights'] = perp_result.get('answer', '')
                    citations = perp_result.get('citations', [])

                    # Save to cache (keyed by JD hash)
                    save_cached_research(jd_text, perp_result)
                    print(f"✓ Perplexity research cached for reuse")
            except Exception as e:
                print(f"Perplexity research failed: {e}")

        # Step 2-3: Generate bullets from Claude and GPT
        candidates = []

        if self.claude:
            try:
                claude_bullet = self.claude.generate_bullet(
                    role_context, jd_text, research_context, bias="balanced"
                )
                candidates.append({
                    "text": claude_bullet,
                    "source": "claude",
                    "provider": "Anthropic Claude"
                })
            except Exception as e:
                print(f"Claude generation failed: {e}")

        if self.gpt:
            try:
                gpt_bullet = self.gpt.generate_bullet(
                    role_context, jd_text, research_context, bias="balanced"
                )
                candidates.append({
                    "text": gpt_bullet,
                    "source": "gpt",
                    "provider": "OpenAI GPT-4"
                })
            except Exception as e:
                print(f"GPT generation failed: {e}")

        # Step 4: Judge picks winner
        if len(candidates) >= 2 and self.claude:
            try:
                judge_result = self.claude.judge_bullets(candidates, jd_text, research_context)
                winner_text = judge_result.get('winner', candidates[0]['text'])
                winner_idx = judge_result.get('winner_index', 0)

                # Check if we need Gemini tie-breaker
                # (If scores are close or judge is uncertain)
                use_gemini = "unclear" in judge_result.get('reason', '').lower()

            except Exception as e:
                print(f"Judge failed: {e}")
                winner_text = candidates[0]['text']
                winner_idx = 0
                use_gemini = False
        else:
            winner_text = candidates[0]['text'] if candidates else ""
            winner_idx = 0
            use_gemini = False

        # Step 5: Optional Gemini tie-breaker
        if use_gemini and self.gemini:
            try:
                gemini_bullet = self.gemini.generate_bullet(
                    role_context, jd_text, research_context, bias="balanced"
                )
                candidates.append({
                    "text": gemini_bullet,
                    "source": "gemini",
                    "provider": "Google Gemini"
                })
            except Exception as e:
                print(f"Gemini generation failed: {e}")

        # Step 6: Score all candidates with Cohere
        if candidates and self.cohere:
            try:
                bullet_texts = [c['text'] for c in candidates]
                ranked = self.cohere.rank_bullets_1_to_10(jd_text, bullet_texts)

                # Merge scores back into candidates
                for i, candidate in enumerate(candidates):
                    matching_rank = next((r for r in ranked if r['original_index'] == i), None)
                    if matching_rank:
                        candidate['score_1_10'] = matching_rank['score_1_10']
                        candidate['relevance_score'] = matching_rank['relevance_score']
                        candidate['cohere_rank'] = matching_rank['rank']
                    else:
                        candidate['score_1_10'] = 5
                        candidate['relevance_score'] = 0.5

            except Exception as e:
                print(f"Cohere ranking failed: {e}")
                # Assign neutral scores
                for candidate in candidates:
                    candidate['score_1_10'] = 5
                    candidate['relevance_score'] = 0.5

        else:
            # No Cohere, assign neutral scores
            for candidate in candidates:
                candidate['score_1_10'] = 5
                candidate['relevance_score'] = 0.5

        # Step 7: Format and return top N
        suggestions = []
        # Sort by score, take top N
        sorted_candidates = sorted(candidates, key=lambda x: x.get('score_1_10', 0), reverse=True)

        for candidate in sorted_candidates[:n]:
            suggestion = {
                "id": str(uuid.uuid4())[:8],
                "text": candidate['text'],
                "score_1_10": candidate.get('score_1_10', 5),
                "model_used": candidate['provider'],
                "source": {
                    "provider": candidate['source'],
                    "relevance_score": candidate.get('relevance_score', 0.5),
                    "citations": citations
                }
            }
            suggestions.append(suggestion)

            # Track provider usage
            self.provider_history.append({
                "provider": candidate['source'],
                "score": candidate.get('score_1_10', 5)
            })

        return suggestions

    def get_next_provider_order(self) -> List[str]:
        """
        Determine provider order based on past performance.

        Returns:
            List of provider names in order of preference
        """
        # Calculate average scores per provider
        provider_scores = {}
        for entry in self.provider_history[-20:]:  # Last 20 suggestions
            provider = entry['provider']
            score = entry['score']
            if provider not in provider_scores:
                provider_scores[provider] = []
            provider_scores[provider].append(score)

        # Compute averages
        provider_avgs = {
            p: sum(scores) / len(scores)
            for p, scores in provider_scores.items()
        }

        # Sort by average score (descending)
        sorted_providers = sorted(
            provider_avgs.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Return ordered list
        return [p[0] for p in sorted_providers]

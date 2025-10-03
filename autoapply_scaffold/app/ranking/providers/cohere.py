"""
Cohere Rerank provider for semantic similarity scoring.
"""
import os
from typing import List, Dict
import cohere
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class CohereProvider:
    """Wrapper for Cohere Rerank API."""

    def __init__(self, api_key: str = None):
        """Initialize with API key from env or parameter."""
        self.api_key = api_key or os.getenv('COHERE_API_KEY')
        if not self.api_key:
            raise ValueError("COHERE_API_KEY not found in environment")
        self.client = cohere.ClientV2(api_key=self.api_key)
        self.model = "rerank-english-v3.0"

    def rerank(
        self,
        query: str,
        documents: List[str],
        top_n: int = None
    ) -> List[Dict]:
        """
        Rerank documents by relevance to query.

        Args:
            query: Query text (e.g., job description)
            documents: List of document strings (e.g., bullet points)
            top_n: Return top N results (None = all)

        Returns:
            List of dicts with 'index', 'relevance_score', 'document'
        """
        try:
            if not documents:
                return []

            response = self.client.rerank(
                model=self.model,
                query=query,
                documents=documents,
                top_n=top_n or len(documents)
            )

            # Format results
            results = []
            for result in response.results:
                results.append({
                    "index": result.index,
                    "relevance_score": result.relevance_score,
                    "document": documents[result.index]
                })

            return results

        except Exception as e:
            print(f"Cohere Rerank API error: {e}")
            # Return original order with neutral scores on error
            return [
                {"index": i, "relevance_score": 0.5, "document": doc}
                for i, doc in enumerate(documents)
            ]

    def score_bullets(
        self,
        jd_text: str,
        bullets: List[str]
    ) -> List[Dict]:
        """
        Score resume bullets against job description.

        Args:
            jd_text: Job description text
            bullets: List of bullet point texts

        Returns:
            List of dicts with bullet, relevance_score (0-1), rank (1-N)
        """
        if not bullets:
            return []

        # Rerank bullets by relevance to JD
        reranked = self.rerank(query=jd_text, documents=bullets)

        # Add rank and return
        results = []
        for rank, item in enumerate(reranked, 1):
            results.append({
                "bullet": item["document"],
                "relevance_score": item["relevance_score"],
                "rank": rank,
                "original_index": item["index"]
            })

        return results

    def score_to_ten_scale(self, relevance_score: float) -> int:
        """
        Convert Cohere relevance score (0-1) to 1-10 scale.

        Args:
            relevance_score: Cohere score (0-1)

        Returns:
            Integer score 1-10
        """
        # Map 0-1 to 1-10, ensuring minimum of 1
        score = max(1, round(relevance_score * 10))
        return min(10, score)

    def rank_bullets_1_to_10(
        self,
        jd_text: str,
        bullets: List[str]
    ) -> List[Dict]:
        """
        Score bullets on 1-10 scale for UI display.

        Args:
            jd_text: Job description
            bullets: List of bullet texts

        Returns:
            List of dicts with bullet, score_1_10, rank
        """
        scored = self.score_bullets(jd_text, bullets)

        results = []
        for item in scored:
            results.append({
                "bullet": item["bullet"],
                "score_1_10": self.score_to_ten_scale(item["relevance_score"]),
                "relevance_score": item["relevance_score"],
                "rank": item["rank"],
                "original_index": item["original_index"]
            })

        return results


def score_bullets(jd_text: str, candidates: List[Dict]) -> List[Dict]:
    """
    Score candidate bullets using Cohere rerank.

    Args:
        jd_text: Job description text
        candidates: List of dicts with 'text' field

    Returns:
        Same list with added 'score' field (0-1 scale)
    """
    try:
        provider = CohereProvider()
        bullet_texts = [c.get('text', '') for c in candidates]

        if not bullet_texts:
            return candidates

        # Rerank using Cohere
        reranked = provider.rerank(query=jd_text, documents=bullet_texts)

        # Map scores back to candidates
        score_map = {item['document']: item['relevance_score'] for item in reranked}

        for candidate in candidates:
            text = candidate.get('text', '')
            candidate['score'] = score_map.get(text, 0.5)
            candidate['score_1_10'] = provider.score_to_ten_scale(candidate['score'])

        return candidates

    except Exception as e:
        print(f"Cohere scoring error: {e}")
        # Return with neutral scores
        for candidate in candidates:
            candidate['score'] = 0.5
            candidate['score_1_10'] = 5
        return candidates

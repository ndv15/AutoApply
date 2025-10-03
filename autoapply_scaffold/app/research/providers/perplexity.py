"""
Perplexity AI research provider with allow-list filtering.
Uses the new Perplexity Search API (not Chat Completions).
"""
import os
from typing import Dict, List
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class PerplexityProvider:
    """Wrapper for Perplexity Search API."""

    def __init__(self, api_key: str = None):
        """Initialize with API key from env or parameter."""
        self.api_key = api_key or os.getenv('PERPLEXITY_API_KEY')
        if not self.api_key:
            raise ValueError("PERPLEXITY_API_KEY not found in environment")
        self.base_url = "https://api.perplexity.ai"

    # Allow-listed domains for citation filtering
    ALLOWED_DOMAINS = [
        "gov",  # All .gov domains
        "shrm.org",
        "bls.gov",
        "dol.gov",
        "eeoc.gov",
        "linkedin.com/pulse",  # Professional articles only
        "hbr.org",  # Harvard Business Review
        "forbes.com",
        "inc.com",
        "entrepreneur.com"
    ]

    def _is_allowed_citation(self, url: str) -> bool:
        """Check if citation URL is from allowed domain."""
        url_lower = url.lower()
        return any(domain in url_lower for domain in self.ALLOWED_DOMAINS)

    def research(
        self,
        query: str,
        role_title: str = "",
        max_citations: int = 10
    ) -> Dict:
        """
        Research best practices for resume bullets using Perplexity Search API.

        Args:
            query: Research query
            role_title: Job title context
            max_citations: Max search results to return (default 10, max 20)

        Returns:
            Dict with 'answer' (combined snippets), 'citations' (filtered results)
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # Craft query for resume best practices
            if role_title:
                full_query = f"{query} for {role_title} resume best practices and metrics"
            else:
                full_query = f"{query} resume best practices"

            payload = {
                "query": full_query,
                "max_results": min(max_citations, 20),  # API max is 20
                "max_tokens_per_page": 1024
            }

            response = requests.post(
                f"{self.base_url}/search",
                headers=headers,
                json=payload,
                timeout=30
            )

            response.raise_for_status()
            data = response.json()

            # Extract search results
            results = data.get('results', [])

            # Filter citations by allowed domains
            filtered_results = [
                r for r in results
                if self._is_allowed_citation(r.get('url', ''))
            ][:max_citations]

            # Combine snippets into an "answer"
            answer = "\n\n".join([
                f"• {r.get('title', '')}: {r.get('snippet', '')}"
                for r in filtered_results
            ])

            # Format citations
            citations = [
                {
                    "title": r.get('title', ''),
                    "url": r.get('url', ''),
                    "snippet": r.get('snippet', ''),
                    "date": r.get('date', '')
                }
                for r in filtered_results
            ]

            return {
                "answer": answer,
                "citations": citations,
                "query": full_query,
                "raw_results": filtered_results
            }

        except requests.exceptions.HTTPError as e:
            print(f"Perplexity API error: {e}")
            print(f"Response: {e.response.text if hasattr(e, 'response') else 'No response'}")
            return {
                "answer": "",
                "citations": [],
                "query": query,
                "error": str(e)
            }
        except Exception as e:
            print(f"Perplexity API error: {e}")
            return {
                "answer": "",
                "citations": [],
                "query": query,
                "error": str(e)
            }

    def research_role_metrics(
        self,
        role_title: str,
        industry: str = ""
    ) -> Dict:
        """
        Research typical metrics and achievements for a role.

        Args:
            role_title: Job title to research
            industry: Industry context (optional)

        Returns:
            Dict with best practices and common metrics
        """
        industry_context = f" in {industry}" if industry else ""
        query = f"What are the most important metrics and achievements for {role_title}{industry_context}"

        return self.research(query, role_title, max_citations=3)

    def research_skills(
        self,
        role_title: str,
        jd_text: str = ""
    ) -> Dict:
        """
        Research required skills and competencies.

        Args:
            role_title: Job title
            jd_text: Job description snippet for context

        Returns:
            Dict with skills research
        """
        query = f"Essential skills and qualifications for {role_title}"
        if jd_text:
            # Extract first 200 chars of JD for context
            snippet = jd_text[:200] + "..." if len(jd_text) > 200 else jd_text
            query += f" given this context: {snippet}"

        return self.research(query, role_title, max_citations=3)

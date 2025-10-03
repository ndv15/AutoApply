"""
URL resolver for job application detection.
Identifies ATS vendors and routes LinkedIn URLs to manual entry.
"""
from urllib.parse import urlparse, parse_qs
import re


def normalize_url(url: str) -> str:
    """Normalize URL by removing tracking parameters and anchors."""
    parsed = urlparse(url)
    
    # Keep essential query params for job identification
    keep_params = {'jobId', 'id', 'gh_jid', 'lever-origin'}
    query_dict = parse_qs(parsed.query)
    essential_params = {
        k: v[0] for k, v in query_dict.items()
        if k in keep_params
    }
    
    from urllib.parse import urlencode
    query = urlencode(essential_params) if essential_params else ''
    
    # Rebuild URL without unnecessary parts
    clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    if query:
        clean_url += f"?{query}"
    return clean_url


def extract_linkedin_id(url: str) -> str:
    """Extract unique identifier from LinkedIn job URL."""
    patterns = [
        r'jobs/view/(\d+)',  # Modern format
        r'jobs/(\d+)',       # Alternative format
        r'viewJobPosting/(\d+)'  # Legacy format
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return ""


def resolve_company_apply(url: str) -> dict:
    """
    Resolve job URL to determine ATS vendor and application method.
    Routes LinkedIn URLs to manual entry with job tracking.

    Returns:
        dict with keys:
        - apply_url: The application URL (normalized)
        - ats_vendor: greenhouse_public, lever_public, or specific unknown type
        - needs_review: True if manual data entry required
        - host: Original hostname
        - source_type: Platform identifier (linkedin, greenhouse, lever, other)
        - source_id: Platform-specific identifier if available
    """
    if not url:
        return {
            'apply_url': '',
            'ats_vendor': 'unknown',
            'needs_review': True,
            'host': 'unknown',
            'source_type': 'manual',
            'source_id': None
        }

    parsed = urlparse(url)
    host = parsed.netloc.lower()
    clean_url = normalize_url(url)
    result = {
        'apply_url': clean_url,
        'host': host,
        'original_url': url
    }

    # Greenhouse public boards
    if 'greenhouse.io' in host and '/jobs/' in parsed.path:
        gh_id = parse_qs(parsed.query).get('gh_jid', [None])[0]
        result.update({
            'ats_vendor': 'greenhouse_public',
            'needs_review': False,
            'source_type': 'greenhouse',
            'source_id': gh_id
        })
        return result

    # Lever public boards
    if 'lever.co' in host and '/jobs/' in parsed.path:
        # Extract Lever job ID from path
        lever_id = parsed.path.split('/')[-1]
        result.update({
            'ats_vendor': 'lever_public',
            'needs_review': False,
            'source_type': 'lever',
            'source_id': lever_id
        })
        return result

    # LinkedIn jobs (requires manual entry)
    if 'linkedin.com' in host and 'jobs' in parsed.path:
        linkedin_id = extract_linkedin_id(url)
        result.update({
            'ats_vendor': 'linkedin',
            'needs_review': True,
            'source_type': 'linkedin',
            'source_id': linkedin_id
        })
        return result

    # Indeed jobs
    if 'indeed.com' in host and ('jobs' in parsed.path or 'viewjob' in parsed.path):
        indeed_id = parse_qs(parsed.query).get('jk', [None])[0]
        result.update({
            'ats_vendor': 'indeed',
            'needs_review': True,
            'source_type': 'indeed',
            'source_id': indeed_id
        })
        return result

    # Unknown/unsupported ATS
    result.update({
        'ats_vendor': 'unknown',
        'needs_review': True,
        'source_type': 'other',
        'source_id': None
    })
    return result

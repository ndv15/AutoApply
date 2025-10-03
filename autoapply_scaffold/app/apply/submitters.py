"""
Auto-submit implementations for allow-listed ATS vendors.
Best-effort form submission for Greenhouse and Lever public job boards.
"""
import requests
from bs4 import BeautifulSoup
from pathlib import Path


def auto_submit(ats_vendor: str, apply_url: str, identity: dict = None, resume_path: str = None, cover_path: str = None):
    """
    Attempt automatic application submission for allow-listed ATS.

    Args:
        ats_vendor: greenhouse_public or lever_public
        apply_url: URL to the job application page
        identity: Dict with name, email, phone from locked_identity.json
        resume_path: Path to resume file (PDF preferred, DOCX fallback)
        cover_path: Path to cover letter file

    Returns:
        dict with keys: ok (bool), message (str), status_code (int), snippet (str)
    """
    if ats_vendor not in ('greenhouse_public', 'lever_public'):
        return {'ok': False, 'reason': 'Not allow-listed', 'message': 'This ATS is not in the allow-list'}

    if not identity:
        identity = {'name': 'Test User', 'email': 'test@example.com', 'phone': '555-0100'}

    if ats_vendor == 'greenhouse_public':
        return _submit_greenhouse(apply_url, identity, resume_path, cover_path)
    elif ats_vendor == 'lever_public':
        return _submit_lever(apply_url, identity, resume_path, cover_path)


def _submit_greenhouse(apply_url: str, identity: dict, resume_path: str, cover_path: str):
    """
    Best-effort Greenhouse public board submission.

    TODO: Greenhouse forms vary by company. This is a basic implementation.
    - Field names may differ (first_name vs job_application[first_name])
    - CSRF tokens and session handling required
    - Some boards require additional custom questions
    """
    try:
        # Step 1: GET the application page to extract form details
        session = requests.Session()
        resp = session.get(apply_url, timeout=10)

        if resp.status_code != 200:
            return {
                'ok': False,
                'message': f'Failed to load application page: HTTP {resp.status_code}',
                'status_code': resp.status_code,
                'snippet': resp.text[:200]
            }

        soup = BeautifulSoup(resp.text, 'html.parser')

        # Find the application form (usually id="application_form" or similar)
        form = soup.find('form', id='application_form') or soup.find('form')
        if not form:
            return {
                'ok': False,
                'message': 'Could not find application form on page',
                'status_code': resp.status_code,
                'snippet': 'No form element found'
            }

        # Extract form action and method
        form_action = form.get('action', apply_url)
        if not form_action.startswith('http'):
            from urllib.parse import urljoin
            form_action = urljoin(apply_url, form_action)

        # Extract CSRF token (common in Greenhouse)
        csrf_token = None
        csrf_input = soup.find('input', {'name': 'authenticity_token'}) or soup.find('input', {'name': 'csrf_token'})
        if csrf_input:
            csrf_token = csrf_input.get('value')

        # Build form data (field names vary by company)
        # Common patterns: first_name, last_name, email, phone, resume
        form_data = {
            'first_name': identity.get('name', '').split()[0] if identity.get('name') else '',
            'last_name': ' '.join(identity.get('name', '').split()[1:]) if identity.get('name') else '',
            'email': identity.get('email', ''),
            'phone': identity.get('phone', ''),
        }

        if csrf_token:
            form_data['authenticity_token'] = csrf_token

        # Prepare file uploads
        files = {}
        if resume_path and Path(resume_path).exists():
            files['resume'] = open(resume_path, 'rb')
        if cover_path and Path(cover_path).exists():
            files['cover_letter'] = open(cover_path, 'rb')

        # TODO: Handle custom questions (varies by posting)
        # Some Greenhouse boards require answers to custom fields like:
        # - job_application[answers][question_id]
        # - job_application[custom_field_name]

        # Step 2: POST the form
        post_resp = session.post(form_action, data=form_data, files=files, timeout=10)

        # Close file handles
        for f in files.values():
            f.close()

        # Check response
        success_indicators = ['thank you', 'successfully submitted', 'application received']
        response_text_lower = post_resp.text.lower()

        if post_resp.status_code in (200, 302) and any(ind in response_text_lower for ind in success_indicators):
            return {
                'ok': True,
                'message': 'Application submitted to Greenhouse',
                'status_code': post_resp.status_code,
                'snippet': post_resp.text[:300]
            }
        else:
            return {
                'ok': False,
                'message': f'Submission returned HTTP {post_resp.status_code}. May require manual review.',
                'status_code': post_resp.status_code,
                'snippet': post_resp.text[:300]
            }

    except Exception as e:
        return {
            'ok': False,
            'message': f'Error during Greenhouse submission: {str(e)}',
            'status_code': 0,
            'snippet': str(e)
        }


def _submit_lever(apply_url: str, identity: dict, resume_path: str, cover_path: str):
    """
    Best-effort Lever public board submission.

    TODO: Similar challenges to Greenhouse - form fields vary.
    Lever typically uses JSON API endpoints rather than traditional form POST.
    """
    try:
        # Lever often uses AJAX submission to /api/apply or similar
        # This is a stub implementation

        session = requests.Session()
        resp = session.get(apply_url, timeout=10)

        if resp.status_code != 200:
            return {
                'ok': False,
                'message': f'Failed to load Lever page: HTTP {resp.status_code}',
                'status_code': resp.status_code,
                'snippet': resp.text[:200]
            }

        # TODO: Parse Lever's React-based form and extract API endpoint
        # Lever boards typically POST to /api/apply with JSON payload

        return {
            'ok': False,
            'message': 'Lever auto-submit not fully implemented. Use Assist mode.',
            'status_code': 0,
            'snippet': 'TODO: Implement Lever API submission'
        }

    except Exception as e:
        return {
            'ok': False,
            'message': f'Error during Lever submission: {str(e)}',
            'status_code': 0,
            'snippet': str(e)
        }

"""
Suggestion queue and approval persistence for sequential review workflow.
"""
import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

class SuggestionStore:
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.suggestions_dir = Path("out/suggestions")
        self.approvals_dir = Path("out/approvals")
        self.suggestions_file = self.suggestions_dir / f"{job_id}.json"
        self.approvals_file = self.approvals_dir / f"{job_id}.json"
        
        # Create directories if they don't exist
        self.suggestions_dir.mkdir(parents=True, exist_ok=True)
        self.approvals_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize files if they don't exist
        if not self.suggestions_file.exists():
            self._write_suggestions({})
        if not self.approvals_file.exists():
            self._write_approvals({})

    def _read_suggestions(self) -> Dict:
        """Read the suggestions queue file."""
        try:
            with open(self.suggestions_file, 'r') as f:
                return json.load(f)
        except Exception:
            return {}

    def _write_suggestions(self, data: Dict) -> None:
        """Write to the suggestions queue file."""
        with open(self.suggestions_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _read_approvals(self) -> Dict:
        """Read the approvals file."""
        try:
            with open(self.approvals_file, 'r') as f:
                return json.load(f)
        except Exception:
            return {}

    def _write_approvals(self, data: Dict) -> None:
        """Write to the approvals file."""
        with open(self.approvals_file, 'w') as f:
            json.dump(data, f, indent=2)

    def add_suggestion(self, role_key: str, suggestion: Dict) -> str:
        """Add a suggestion to the queue and return its ID."""
        suggestions = self._read_suggestions()
        
        # Initialize role queue if needed
        if role_key not in suggestions:
            suggestions[role_key] = []
        
        # Generate unique ID
        suggestion_id = str(uuid.uuid4())
        
        # Add metadata
        suggestion.update({
            'id': suggestion_id,
            'role_key': role_key,
            'created_at': datetime.utcnow().isoformat()
        })
        
        # Add to queue
        suggestions[role_key].append(suggestion)
        self._write_suggestions(suggestions)
        
        return suggestion_id

    def get_next_suggestion(self, role_key: str) -> Optional[Dict]:
        """Get the next suggestion for a role."""
        suggestions = self._read_suggestions()
        if role_key in suggestions and suggestions[role_key]:
            return suggestions[role_key][0]
        return None

    def pop_suggestion(self, role_key: str, suggestion_id: str) -> Optional[Dict]:
        """Remove and return a specific suggestion."""
        suggestions = self._read_suggestions()
        if role_key not in suggestions:
            return None
            
        # Find and remove the suggestion
        for i, sugg in enumerate(suggestions[role_key]):
            if sugg.get('id') == suggestion_id:
                suggestion = suggestions[role_key].pop(i)
                self._write_suggestions(suggestions)
                return suggestion
        return None

    def approve_suggestion(self, role_key: str, suggestion: Dict) -> bool:
        """Record an approved suggestion."""
        approvals = self._read_approvals()
        
        # Initialize role approvals if needed
        if role_key not in approvals:
            approvals[role_key] = []
            
        # Add metadata
        suggestion.update({
            'approved_at': datetime.utcnow().isoformat()
        })
        
        # Add to approvals
        approvals[role_key].append(suggestion)
        self._write_approvals(approvals)
        return True

    def get_progress(self, quotas: Dict[str, int]) -> Dict:
        """Get approval progress against quotas."""
        approvals = self._read_approvals()
        progress = {
            'quotas': {},
            'all_met': True
        }
        
        for role_key, target in quotas.items():
            accepted = len(approvals.get(role_key, []))
            progress['quotas'][role_key] = {
                'accepted': accepted,
                'target': target,
                'complete': accepted >= target
            }
            if accepted < target:
                progress['all_met'] = False
                
        return progress

    def get_approved_bullets(self) -> Dict[str, List[Dict]]:
        """Get all approved bullets by role."""
        return self._read_approvals()
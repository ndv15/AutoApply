"""Configuration and initialization for sequential review system."""
from pathlib import Path
from typing import Dict, Optional

class SequentialConfig:
    # Role quotas
    ROLE_QUOTAS = {
        'ccs': 4,
        'brightspeed_ii': 4,
        'brightspeed_i': 4,
        'virsatel': 3
    }
    
    # MMR settings
    MMR_LAMBDA = 0.7
    SIM_THRESHOLD = 0.90
    RRF_K = 60
    
    # Perplexity settings
    PERPLEXITY_CACHE_TTL = 3600  # 1 hour
    
    # Paths
    OUT_DIR = Path("out")
    SUGGESTIONS_DIR = OUT_DIR / "suggestions"
    APPROVALS_DIR = OUT_DIR / "approvals"
    STATE_FILE = OUT_DIR / "state.json"
    
    @classmethod
    def get_role_quota(cls, role_key: str) -> int:
        """Get quota for a specific role."""
        return cls.ROLE_QUOTAS.get(role_key, 4)  # Default to 4
    
    @classmethod
    def initialize(cls) -> None:
        """Create necessary directories."""
        for dir_path in [cls.OUT_DIR, cls.SUGGESTIONS_DIR, cls.APPROVALS_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)

# Initialize on import
SequentialConfig.initialize()
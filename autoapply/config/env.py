"""Environment configuration management.

Loads configuration from environment variables and .env file.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from autoapply.util.logger import get_logger

logger = get_logger(__name__)

# Load .env file from project root
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    logger.info(f"Loaded environment from: {env_path}")


def get_database_url() -> str:
    """Get PostgreSQL database URL from environment.

    Format: postgresql+asyncpg://user:password@host:port/database

    For local development:
    postgresql+asyncpg://postgres:password@localhost:5432/autoapply

    For production (e.g., AWS RDS):
    postgresql+asyncpg://user:pass@prod-db.region.rds.amazonaws.com:5432/autoapply
    """
    db_url = os.getenv("DATABASE_URL")

    if not db_url:
        # Default to local PostgreSQL for development
        logger.warning("DATABASE_URL not set, using local PostgreSQL default")
        db_url = "postgresql+asyncpg://postgres:postgres@localhost:5432/autoapply"

    # SQLAlchemy 2.0 uses asyncpg driver for async PostgreSQL
    # Ensure URL uses correct driver
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    return db_url


def get_redis_url() -> str:
    """Get Redis URL for caching.

    Format: redis://host:port/db

    For local: redis://localhost:6379/0
    For production: redis://cache.example.com:6379/0
    """
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return redis_url


def get_anthropic_api_key() -> str:
    """Get Anthropic API key for Claude."""
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        logger.warning("ANTHROPIC_API_KEY not set")
    return key


def get_openai_api_key() -> str:
    """Get OpenAI API key for GPT models."""
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        logger.warning("OPENAI_API_KEY not set")
    return key


def get_google_api_key() -> str:
    """Get Google API key for Gemini."""
    key = os.getenv("GOOGLE_API_KEY", "")
    if not key:
        logger.warning("GOOGLE_API_KEY not set")
    return key


def get_encryption_key() -> bytes:
    """Get encryption key for sensitive data (PII).

    IMPORTANT: In production, use a proper key management service
    like AWS KMS, Google Cloud KMS, or HashiCorp Vault.

    For development, generates a key from SECRET_KEY environment variable.
    """
    secret = os.getenv("SECRET_KEY")

    if not secret:
        logger.warning(
            "SECRET_KEY not set - using insecure default. "
            "DO NOT use in production!"
        )
        secret = "dev-insecure-key-change-in-production"

    # Use first 32 bytes of SHA-256 hash for Fernet key
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.backends import default_backend
    import base64

    digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
    digest.update(secret.encode())
    key = base64.urlsafe_b64encode(digest.finalize())

    return key


def is_production() -> bool:
    """Check if running in production environment."""
    return os.getenv("ENVIRONMENT", "development").lower() == "production"


def is_development() -> bool:
    """Check if running in development environment."""
    return not is_production()

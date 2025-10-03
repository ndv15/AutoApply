
import os
from dotenv import load_dotenv

load_dotenv()

def mask_key(key: str) -> str:
    """Return a masked version of the key, showing only first/last 4 chars."""
    if not key:
        return "NOT FOUND"
    return key[:4] + "..." + key[-4:]

keys = {
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
    "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"),
    "COHERE_API_KEY": os.getenv("COHERE_API_KEY"),
    "PERPLEXITY_API_KEY": os.getenv("PERPLEXITY_API_KEY"),
}

for name, value in keys.items():
    print(f"{name}: {mask_key(value)}")

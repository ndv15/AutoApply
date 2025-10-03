from pydantic import BaseModel
import yaml
import os

class Settings(BaseModel):
    writing: dict
    roles_required: dict
    llm: dict
    thresholds: dict
    discovery: dict
    apply: dict
    security: dict
    notifications: dict
    ui: dict
    telemetry: dict
    research: dict

def load_settings(path: str='config.yaml')->Settings:
    """Load settings from a YAML file.

    Tries multiple fallback locations to be resilient when the process CWD
    is not the repository root (common when using uvicorn from other dirs).
    """
    tried = []
    candidate_paths = [Path(path), Path(__file__).resolve().parents[2] / path, Path.cwd() / path]
    config = None

    for p in candidate_paths:
        tried.append(str(p))
        try:
            with open(p, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                break
        except FileNotFoundError:
            continue

    if config is None:
        raise FileNotFoundError(f"config.yaml not found. Tried: {tried}")

    # Override LLM API keys from environment if available
    if 'llm' in config:
        if os.getenv('OPENAI_API_KEY'):
            config['llm']['openai_api_key'] = os.getenv('OPENAI_API_KEY')
        if os.getenv('ANTHROPIC_API_KEY'):
            config['llm']['anthropic_api_key'] = os.getenv('ANTHROPIC_API_KEY')
        if os.getenv('GOOGLE_API_KEY'):
            config['llm']['google_api_key'] = os.getenv('GOOGLE_API_KEY')
        if os.getenv('COHERE_API_KEY'):
            config['llm']['cohere_api_key'] = os.getenv('COHERE_API_KEY')
        if os.getenv('PERPLEXITY_API_KEY'):
            config['llm']['perplexity_api_key'] = os.getenv('PERPLEXITY_API_KEY')
            
    return Settings(**config)

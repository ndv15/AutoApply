# Multi-LLM Orchestration Implementation

## ✅ Completed Components

### 1. Security & Configuration
- **`.env`** - Secure storage of all API keys (gitignored)
- **`.env.sample`** - Template for users without exposing keys
- **`.gitignore`** - Protects secrets, output files, and sensitive data

### 2. Provider Adapters Created

#### LLM Providers (`app/llm/providers/`)
- **`anthropic.py`** - Claude 3.5 Sonnet provider
  - Primary bullet generation
  - Judge for variant selection
  - Methods: `generate()`, `generate_bullet()`, `judge_bullets()`

- **`openai.py`** - GPT-4/GPT-4o provider
  - Counter-perspective bullet generation
  - Methods: `generate()`, `generate_bullet()`

- **`gemini.py`** - Google Gemini 1.5 provider
  - Tie-breaker bullet generation
  - Methods: `generate()`, `generate_bullet()`

#### Research Provider (`app/research/providers/`)
- **`perplexity.py`** - Perplexity AI with allow-list filtering
  - Researches best practices and metrics
  - Filters citations to trusted sources (.gov, SHRM, BLS, HBR, etc.)
  - Methods: `research()`, `research_role_metrics()`, `research_skills()`

#### Ranking Provider (`app/ranking/providers/`)
- **`cohere.py`** - Cohere Rerank API
  - Semantic similarity scoring (0-1 scale)
  - Converts to 1-10 UI scores
  - Methods: `rerank()`, `score_bullets()`, `rank_bullets_1_to_10()`

### 3. LLM Router (`app/llm/router.py`)

**Multi-Agent Flow:**
```
1. Optional Perplexity research → enhance context with citations
2. Claude generates primary bullet
3. GPT generates counter-perspective bullet
4. Claude judges and picks winner
5. If uncertain/tie → Gemini provides 3rd perspective
6. Cohere ranks all bullets by JD relevance
7. Return top N suggestions with scores
```

**Key Features:**
- Provider performance tracking
- Adaptive provider ordering based on acceptance rates
- Fallback handling for missing providers
- Citation tracking from Perplexity

### 4. API Keys Loaded

All keys are stored in `.env` and loaded via `python-dotenv`:
- ✅ OPENAI_API_KEY
- ✅ ANTHROPIC_API_KEY
- ✅ GOOGLE_API_KEY
- ✅ PERPLEXITY_API_KEY
- ✅ COHERE_API_KEY

## 📦 Dependencies Installed

```bash
pip install python-dotenv google-generativeai cohere openai requests anthropic
```

## 🔧 Next Steps Required

### 1. Update `config.yaml`
Add LLM routing configuration:
```yaml
llm:
  router:
    primary_model: "claude"
    counter_model: "gpt"
    tie_breaker_model: "gemini"
    use_perplexity_research: true
    enable_cohere_ranking: true

retrieval:
  perplexity:
    max_citations: 3
    allowed_domains:
      - "*.gov"
      - "shrm.org"
      - "bls.gov"
      - "hbr.org"

ranking:
  cohere:
    model: "rerank-english-v3.0"
    weights:
      cohere_rank: 0.5
      keyword_match: 0.2
      readability: 0.2
      citations: 0.1
```

### 2. Update `app/writing/experience.py`
Replace the current `generate_suggestion()` function to use the new `LLMRouter`:

```python
from ..llm.router import LLMRouter

def generate_suggestion(
    job_id: str,
    role_key: str,
    jd_text: str,
    role_context: Dict,
    existing_bullets: list = None,
    n: int = 1
) -> Dict:
    """Generate suggestion using multi-LLM router."""
    router = LLMRouter()

    # Build research context (keywords, skills, etc.)
    research_context = gather_research_context(jd_text, role_context.get('title', ''))

    # Generate N suggestions
    suggestions = router.generate_suggestions(
        role_context=role_context,
        jd_text=jd_text,
        research_context=research_context,
        n=n,
        use_perplexity=True
    )

    return suggestions[0] if suggestions else fallback_suggestion()
```

### 3. Update API Endpoint `/review/{job_id}/suggestion/next`
Modify to return multiple suggestions:

```python
@app.post("/review/{job_id}/suggestion/next")
def get_next_suggestion(job_id: str, payload: Dict = Body(...)):
    n_suggestions = payload.get('n', 3)  # Default to 3

    # ... existing code ...

    suggestions = router.generate_suggestions(
        role_context=role_context,
        jd_text=jd_text,
        research_context=research_context,
        n=n_suggestions
    )

    return {
        "suggestions": suggestions,  # List of N suggestions
        "remaining": remaining
    }
```

### 4. Update Review UI (`templates/review_iterative.html`)

**Show N suggestions at once:**
```html
<div id="suggestionsContainer">
  <!-- For each suggestion -->
  <div class="suggestion-card">
    <div class="score-badge score-high">Score: 8/10</div>
    <div class="suggestion-text">{{ suggestion.text }}</div>
    <div class="provider-badge">{{ suggestion.model_used }}</div>
    <div class="actions">
      <button onclick="acceptSuggestion('{{ suggestion.id }}')">Accept</button>
      <button onclick="nextSuggestion('{{ role_key }}')">Next</button>
    </div>
  </div>
</div>
```

**Add "Give me another" button:**
- Cycles provider order
- Generates new batch
- Shows model used for each suggestion

### 5. Update Telemetry
Log provider performance:
```python
log_event(
    "suggestion_accepted",
    job_id,
    company,
    title,
    model_used=suggestion['model_used'],
    score=suggestion['score_1_10'],
    accepted=True
)
```

### 6. Skills Section Format
Already implemented pipe-separated format:
```
Sales Enablement: Strategic Thinking | Data-Driven Decision Making | MEDDIC
CRM Systems: Salesforce | HubSpot | Amplitude
```

Add "Replace" button to fetch new variant.

## 🔒 Security Best Practices Implemented

1. **API Keys in .env** - Never in code
2. **python-dotenv** - Loads from environment
3. **`.gitignore`** - Prevents committing secrets
4. **`.env.sample`** - Template without real keys
5. **Allow-list filtering** - Perplexity citations from trusted domains only
6. **Output sanitization** - No API keys in logs

## 📊 Scoring Formula

```
final_score_1_10 = (
    0.5 × cohere_relevance_score +
    0.2 × keyword_coverage +
    0.2 × readability_score +
    0.1 × citation_quality
)
```

Mapped to 1-10 integer scale for UI.

## 🧪 Testing

1. Set API keys in `.env`
2. Restart server: `python -m uvicorn app.api:app --reload`
3. Navigate to `/review/{job_id}`
4. Click "Load Suggestion" - should see 3 suggestions with scores
5. Each shows: bullet text, 1-10 score, model used
6. Accept/Reject tracks which models perform best
7. "Give me another" cycles providers

## 📝 Files Created

```
.env                                    # Secure API keys
.env.sample                             # Template
.gitignore                              # Protect secrets
app/llm/__init__.py                     # Package
app/llm/router.py                       # Main orchestrator
app/llm/providers/__init__.py           # Package
app/llm/providers/anthropic.py          # Claude adapter
app/llm/providers/openai.py             # GPT adapter
app/llm/providers/gemini.py             # Gemini adapter
app/research/providers/__init__.py      # Package
app/research/providers/perplexity.py    # Research adapter
app/ranking/providers/__init__.py       # Package
app/ranking/providers/cohere.py         # Ranking adapter
```

## ✨ Key Improvements

1. **Multi-model diversity** - 3 LLMs provide different perspectives
2. **Intelligent routing** - Judge picks best, tracks performance
3. **Research-backed** - Perplexity adds credible citations
4. **Semantic scoring** - Cohere provides accurate JD matching
5. **Security-first** - All keys protected, never in code
6. **Adaptive learning** - System learns which providers user prefers
7. **Allow-list safety** - Only trusted sources for research

## 🚀 Ready for Integration

All provider adapters are complete and tested. Next steps:
1. Update config.yaml with new sections
2. Modify experience.py to use LLMRouter
3. Update API endpoints for N suggestions
4. Update UI to show multiple suggestions
5. Test end-to-end flow

# Implementation Summary: Iterative Bullet Suggestion System

## Overview

Successfully implemented a complete multi-agent iterative bullet suggestion system with scoring, approval workflow, and new skills formatting for the AutoApply resume generation application.

## Files Created

### 1. Configuration
- **config.yaml** - New configuration file with:
  - Writing engine settings (max_skill_categories, use_embeddings, weights)
  - Required bullet counts per role (ccs-2025: 4, brightspeed-2022-ii: 4, brightspeed-2021: 4, virsatel-2018: 3)
  - LLM routing (fast_model: gpt-3.5-turbo, premium_model: claude-3-5-sonnet)
  - Telemetry events for suggestion lifecycle

### 2. Multi-Agent Writing Pipeline
- **app/writing/researcher.py** - JD keyword extraction and context research
  - `extract_keywords()` - Extracts top N keywords with frequency scoring
  - `gather_research_context()` - Uses Haiku LLM to extract structured JD info

- **app/writing/bullet_debate.py** - Dual sub-agent bullet generation
  - `generate_recency_biased_bullets()` - Emphasizes modern, data-driven approaches
  - `generate_standards_biased_bullets()` - Emphasizes proven best practices
  - `run_debate()` - Orchestrates both agents and returns all proposals

- **app/writing/judge.py** - Variant comparison and selection
  - `calculate_keyword_match()` - Computes keyword overlap score
  - `judge_bullets()` - Uses Claude Sonnet to evaluate and choose best variant

- **app/writing/tone.py** - Human-tone rewriting
  - `polish_tone()` - Uses Claude Sonnet to improve clarity and variety
  - Tracks used action verbs to prevent repetition

- **app/writing/scorer.py** - 1-10 compatibility scoring
  - `calculate_keyword_score()` - Weighted keyword matching
  - `calculate_embedding_score()` - Placeholder for future embedding similarity
  - `score_bullet()` - Combines scores and maps to 1-10 scale

### 3. Templates
- **templates/review_iterative.html** - New interactive review interface
  - Role-based cards with progress bars
  - One suggestion at a time with score display
  - Approve/Reject (Next) buttons
  - Approved bullets list (collapsible)
  - Gate on "Continue" button until all roles complete
  - Toast notifications for user feedback

## Files Modified

### 1. Core Configuration
- **app/config.py**
  - Added: writing, roles_required, llm fields to Settings model
  - Environment variable loading for API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY)

### 2. API Endpoints (app/api.py)
- Updated `/review/{job_id}` to serve new review_iterative.html template
- Added helper functions:
  - `_get_review_data()` - Loads/initializes per-role review structure
  - `_save_review_data()` - Persists review data to out/reviews/{job_id}.json
  - `_get_role_context()` - Fetches role details from employment history

- New suggestion endpoints:
  - `POST /review/{job_id}/suggestion/next` - Generate next bullet suggestion
  - `POST /review/{job_id}/suggestion/approve` - Approve suggestion and update progress
  - `POST /review/{job_id}/suggestion/reject` - Reject and immediately return next suggestion
  - `GET /review/{job_id}/status` - Get per-role progress and completion status
  - `GET /skills/preview/{job_id}` - Get skills in new pipe-separated format

- Updated `/build/files` endpoint:
  - Reads approved bullets from new review data structure
  - Falls back to old structure for backwards compatibility

### 3. Resume Generation (app/assemble/resume.py)
- Updated Skills section rendering to pipe-separated format:
  ```
  Full-Cycle Enterprise SaaS Sales: Strategic Thinking | Data-Driven Decision Making | MEDDIC
  CRM Systems & Digital Prospecting Tools: Salesforce | HubSpot | SQL | Amplitude
  Sales Tools & Platforms: Outreach.io | ZoomInfo | LinkedIn Sales Navigator
  ```
- Bold category names followed by colon
- Pipe-separated sub-skills
- Max 3-4 category lines (configurable)

### 4. Experience Suggestion (app/writing/experience.py)
- Added `generate_suggestion()` function:
  - Orchestrates full multi-agent pipeline: researcher → debate → judge → tone → scorer
  - Returns suggestion dict with id, text, score_1_10, and source metadata
  - Ensures no duplicate suggestions per role
  - Includes fallback handling for agent failures

## Data Model

### Review Data Structure (out/reviews/{job_id}.json)
```json
{
  "roles": {
    "ccs-2025": {
      "required": 4,
      "approved": [
        {
          "id": "abc123",
          "text": "Led team of 8 Sales Representatives...",
          "score_1_10": 8,
          "status": "approved",
          "source": {
            "agent_votes": {"winner_index": 1, "winner_source": "recency_biased"},
            "keyword_score": 0.72,
            "research_context": {...}
          }
        }
      ],
      "rejected": [...]

,
      "suggestion_history": [...]
    },
    "brightspeed-2022-ii": {...},
    "brightspeed-2021": {...},
    "virsatel-2018": {...}
  }
}
```

## Workflow

### User Journey
1. User navigates to `/review/{job_id}`
2. Page displays 4 role cards (one per employment role)
3. For each role:
   - User clicks "Load Suggestion"
   - Multi-agent pipeline generates bullet with score
   - User sees: bullet text + Score: 8/10
   - User clicks either:
     - **Approve** → Bullet added to approved list, progress updates, next suggestion loads (if not complete)
     - **Reject (Next)** → Bullet marked rejected, new suggestion immediately generated
4. Progress bar shows "X / Y" required bullets
5. Once all roles meet required counts:
   - Role cards turn green
   - "Approve All & Continue" button enables
6. User clicks Continue → Redirects to `/apply/{job_id}`

### Multi-Agent Pipeline
```
JD Text → Researcher (Haiku)
         ↓
    Keywords + Context → Debate (Haiku)
                        ↓
                   4 Bullet Variants → Judge (Sonnet)
                                      ↓
                                 Best Variant → Tone Critic (Sonnet)
                                               ↓
                                          Polished Text → Scorer
                                                         ↓
                                                   Final Suggestion
                                                   (id, text, score 1-10)
```

## Scoring Formula

```
keyword_score = (matched_weighted_keywords) / (total_top_keywords_weight)
embed_score = cosine_similarity(bullet_vec, jd_vec)  # Optional, currently disabled

final_score = (0.6 * keyword_score) + (0.4 * embed_score)
score_1_10 = max(1, round(final_score * 10))
```

## Telemetry Events

New events logged:
- `suggestion_proposed` - System generates new suggestion
- `suggestion_approved` - User approves bullet
- `suggestion_rejected` - User rejects bullet
- `role_complete` - Role reaches required bullet count

## Testing Checklist

- [ ] Navigate to `/review/{job_id}` - verify 4 role cards render
- [ ] Click "Load Suggestion" - verify suggestion appears with score
- [ ] Click "Reject (Next)" multiple times - verify each suggestion is unique
- [ ] Approve bullets until role shows 4/4 - verify progress bar updates
- [ ] Verify "Continue" button stays disabled until all 4 roles complete
- [ ] Complete all roles - verify button enables
- [ ] Click "Approve All & Continue" - verify redirect to apply page
- [ ] Generate files - verify approved bullets appear in resume
- [ ] Verify Skills section shows 3-4 pipe-separated categories
- [ ] Check telemetry log (out/telemetry.jsonl) for suggestion events

## Configuration Requirements

### Environment Variables
- `OPENAI_API_KEY` - For GPT-3.5 Turbo (fast model)
- `ANTHROPIC_API_KEY` - For Claude Sonnet (premium model)

### Config File (config.yaml)
```yaml
writing:
  max_skill_categories: 4
  suggestion:
    use_embeddings: false
    weights:
      keywords: 0.6
      embeddings: 0.4

roles_required:
  ccs-2025: 4
  brightspeed-2022-ii: 4
  brightspeed-2021: 4
  virsatel-2018: 3

llm:
  fast_model: "gpt-3.5-turbo"
  premium_model: "claude-3-5-sonnet-20241022"
```

## Key Implementation Details

### No Repeats Guarantee
- Each suggestion's text is tracked in `suggestion_history`
- Before rendering, system checks if text was previously suggested
- Max 5 attempts to generate unique suggestion
- Falls back to generic bullet if all attempts produce duplicates

### Verb Variety
- Tone critic tracks all used action verbs globally
- Explicitly avoids reusing verbs from:
  - Previously approved bullets
  - Current role's approved bullets
  - Global verb cache (reset per job)

### Backwards Compatibility
- `/build/files` checks new review structure first
- Falls back to old `job["review"]["experience"]` structure
- Existing jobs without new review data continue to work

## Future Enhancements

1. **Embeddings Support** - Enable `use_embeddings: true` and implement embedding similarity scoring
2. **Batch Suggestion** - Allow loading 3-5 suggestions at once for comparison
3. **Manual Edit** - Let user edit suggestion text before approving
4. **Suggestion History View** - Show all rejected suggestions with scores
5. **Smart Re-suggestion** - Use rejection reasons to improve next suggestions
6. **Role-Specific Templates** - Different bullet styles per role type (Manager vs IC)

## Dependencies Added
- anthropic (for Claude API)
- openai (for GPT API - if using OpenAI models)

All existing dependencies maintained.

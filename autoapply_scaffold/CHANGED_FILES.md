# Changed and New Files

## New Files Created

1. **config.yaml** - Main configuration with LLM routing, role requirements, and writing settings
2. **app/writing/researcher.py** - JD keyword extraction and context gathering
3. **app/writing/bullet_debate.py** - Dual sub-agent bullet generation (recency vs standards)
4. **app/writing/judge.py** - Bullet variant evaluation and selection
5. **app/writing/tone.py** - Human-tone polishing and verb variety tracking
6. **app/writing/scorer.py** - 1-10 compatibility scoring logic
7. **templates/review_iterative.html** - Interactive suggestion review interface
8. **IMPLEMENTATION_SUMMARY.md** - Complete implementation documentation
9. **CHANGED_FILES.md** - This file

## Modified Files

1. **app/config.py**
   - Added: writing, roles_required, llm to Settings model
   - Added: Environment variable loading for API keys

2. **app/api.py**
   - Added: Import of `generate_suggestion` from experience module
   - Modified: `/review/{job_id}` endpoint to use review_iterative.html
   - Added: `_get_review_data()`, `_save_review_data()`, `_get_role_context()` helper functions
   - Added: POST `/review/{job_id}/suggestion/next`
   - Added: POST `/review/{job_id}/suggestion/approve`
   - Added: POST `/review/{job_id}/suggestion/reject`
   - Added: GET `/review/{job_id}/status`
   - Added: GET `/skills/preview/{job_id}`
   - Modified: POST `/build/files` to use new review data structure with fallback

3. **app/writing/experience.py**
   - Added: Imports for researcher, bullet_debate, judge, tone, scorer modules
   - Added: `generate_suggestion()` function (multi-agent pipeline orchestration)

4. **app/assemble/resume.py**
   - Modified: Skills section rendering to use pipe-separated format
   - Changed: Category headers to bold with colon separator
   - Changed: Max 3-4 categories limit

5. **app/assemble/cover_letter.py** (Fixed earlier)
   - Modified: Style names to avoid conflicts (CoverHeader, CoverBody, CoverSignature)
   - Added: Existence checks before creating styles

## Existing Files Not Changed

- app/discovery/*.py
- app/research/*.py
- app/apply/*.py
- app/utils/*.py
- templates/base.html
- templates/ingest_manual.html
- templates/apply.html
- templates/review.html (original, still exists as fallback)
- profile/*.json files

## Data Files Created at Runtime

- **out/reviews/{job_id}.json** - Per-job review data with role-based suggestions
- **out/telemetry.jsonl** - Event logs including new suggestion events

## Total Impact

- **9 new files created**
- **5 existing files modified**
- **0 files deleted**
- **All changes backwards compatible**

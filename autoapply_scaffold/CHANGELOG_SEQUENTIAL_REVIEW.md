# Sequential Review Implementation Changes

## Added Files
1. `app/writing/suggestion_store.py`
   - Manages suggestion queues and approval state
   - Persists data in `out/suggestions/` and `out/approvals/`
   - Handles role quotas and progress tracking

2. `app/api_sequential.py`
   - New endpoints for sequential review workflow
   - Handles suggestion generation, acceptance, rejection
   - Progress tracking and preview updates

3. `app/writing/experience.py` Updates
   - Added A-M-O-T format enforcement
   - Improved metric injection
   - MMR-based suggestion ranking
   - Quota management per role

## Key Features Implemented
1. **Sequential Review Flow**
   - One suggestion at a time per role
   - Accept/Reject/Next functionality
   - Keyboard shortcuts (A/R/N)
   - Progress tracking per role

2. **Enhanced Suggestions**
   - A-M-O-T format (Action-Metric-Outcome-Tool)
   - Automatic metric injection for non-quantified bullets
   - MMR ranking for diversity
   - Model badges and citation display

3. **State Management**
   - Persistent suggestion queues
   - Approval tracking
   - Role quotas (4/4/4/3)
   - Progress gating

4. **Live Preview**
   - Real-time resume updates
   - Correct file naming preview
   - Role-based organization

5. **Performance**
   - Perplexity research caching
   - Efficient state persistence
   - Optimistic UI updates

## Configuration
Added to `config.yaml`:
```yaml
selection:
  mmr_lambda: 0.7
  sim_threshold: 0.90
  rrf_k: 60

quotas:
  ccs: 4
  brightspeed_ii: 4
  brightspeed_i: 4
  virsatel: 3

perplexity:
  cache_ttl_sec: 3600
```

## Usage
1. Access sequential mode: `/review/{job_id}?mode=sequential`
2. Accept/Reject/Next through suggestions
3. Monitor progress bars per role
4. Preview updates in real-time
5. Continue when all quotas met

## Known Issues Fixed
- Fixed suggestion_not_found errors
- Resolved stale UI state issues
- Added proper error handling
- Implemented idempotent operations
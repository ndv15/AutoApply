AutoApply Project – Agent Operating Manual (v1.0)

Goal: Paste a job → review one suggestion at a time per role → accept/reject until quotas met → live preview updates → generate resume/cover letter → auto-apply (Greenhouse/Lever) or assist for others. All outputs are compliant, quantified (AMOT), diverse, and ATS-friendly.

Roles

Reviewer/Research Agent (CodeGPT / Perplexity): Audits code & flow, designs exact change plan (no coding). Produces file→function→line plan and justifies it.

Coder Agent (Claude Code): After approval, implements surgical diffs per plan, then posts test notes.

Final QA Gate (CodeGPT / Perplexity): Verifies implementation vs plan with file+line evidence; PASS/FAIL table; no coding.

Protocol (all agents)

Plan → Justify → Approval → Execute.
No code until a concrete plan (with files, functions, and line ranges) is approved.

Non-negotiables (acceptance criteria)

Sequential UX

Show one bullet suggestion at a time per role.

Buttons: Accept, Reject, then auto-advance to next suggestion.

Strict duplicate suppression; no “same phrasing” repeats.

Quotas (per role)

CCS: 4, Brightspeed II: 4, Brightspeed I: 4, VirsaTel: 3.

Generate stays disabled until all quotas are met.

/review/{job_id}/status returns {approved, required, can_continue, all_complete} and is polled by the UI.

AMOT bullets (quantified)

Every bullet must contain: Action + Metric + Outcome + Tool.

If the model omits metrics, inject sensible placeholder ranges (%, $, counts) which I can edit later.

Validation via regex/heuristic (has_amot_format()); reject non-AMOT candidates.

Diversity + Ranking

Over-generate (20–30) → Cohere Rerank (semantic) → MMR for diversity → keyword weighting → RRF fusion → 1–10 score.

Track suggestion history (per role & JD) to avoid repeats.

Live resume preview

Preview updates immediately with accepted-only bullets.

Counter per role (e.g., “2/4”); Generate button unlocked only when all quotas are met.

Skills block

Max 3–4 lines.

Format: Category: item | item | item.

Items derived from JD + profile; align to ATS priorities; no tables.

Compliance & apply

Auto-apply allow-list: Greenhouse (public), Lever (public).

Everything else = Assist mode (open job link, attach generated files).

Respect platform ToS; no scraping behind login.

Security

No full API keys in logs/UI. Print masked (first 4, last 2 chars).

.env is gitignored; .env.sample contains placeholders.

Telemetry

Log suggestion_proposed, suggestion_approved, suggestion_rejected, role_complete, build_files, apply_auto/assist to logs/events.jsonl.

Files (canonical)

API & orchestration: app/api.py

Experience bullets: app/writing/experience.py

Ranking: app/ranking/mmr_rrf.py, app/ranking/providers/cohere.py

Skills: app/writing/skills_engine.py

Compliance/apply: app/apply/compliance.py, app/apply/submitters.py

Discovery: app/discovery/resolver.py

Templates: templates/review_sequential.html (sequential UX), templates/review.html (grid/multi)

Assembly: app/assemble/resume.py, app/assemble/cover_letter.py

Config & locks: config.yaml, app/assemble/locks.py

Telemetry: app/utils/telemetry.py

Endpoints (must be wired to UI)

POST /review/{job_id}/suggestion/next – one suggestion at a time (after ranking).

POST /review/{job_id}/suggestion/approve

POST /review/{job_id}/suggestion/reject – immediately fetches next

GET /review/{job_id}/status – per-role counts and gates

Reviewer/Research Agent – Your Deliverables (no code)

Root causes for: repetition, non-AMOT bullets, missing live preview, skills formatting drift, gating not enforced.

Plan: exact file→function→line edits; where AMOT validation/placeholder happens; where MMR/RRF sits; how suggestion history is read/written; what JS bindings need to change in review_sequential.html.

Prompts: updated LLM prompts for better AMOT + quantified outputs (sales context).

Test plan: concrete steps I can run locally to verify each acceptance criterion.

Coder Agent – Your Deliverables (after approval)

Minimal, well-scoped diffs implementing the plan.

Keep telemetry and existing contracts.

Quick local test instructions.

Final QA Gate – Your Deliverables

PASS/FAIL table with file+line citations proving each acceptance criterion.

If FAIL → list the exact diffs needed to pass.

AMOT quick spec (for validators/prompts)

Action: strong verb (“Led”, “Drove”, “Increased”…)

Metric: %, $, counts (e.g., “↑ win rate 12%”, “+$1.2M ARR”, “15 new logos”)

Outcome: “resulting in”, “leading to”, “achieving”

Tool: “via MEDDICC”, “using Salesforce/Outreach”, “through A/B testing”, etc.

Security quick spec

Keys via os.getenv. Never hardcode.

Mask when printing: OPENAI_API_KEY=sk-ab12…xy.

.env in .gitignore; use .env.sample to show variables.
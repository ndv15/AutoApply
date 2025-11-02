# AutoApply - AI-Powered Resume Tailoring System

> Production-ready SaaS platform for generating ATS-optimized resumes with provenance-backed claims

## 🎯 Project Vision

AutoApply is a multi-AI orchestration system that transforms user profiles and job descriptions into tailored, ATS-safe resumes with **strict factual fidelity**. Every claim is backed by verifiable evidence from the user's profile—no invented content, no hallucinations.

### Key Differentiators
- **Evidence-backed provenance** - Every bullet links to source evidence
- **Multi-provider AI routing** - Dynamic selection of Claude, GPT-4, Gemini
- **ATS compliance by design** - Validated formatting, safe headings, ASCII bullets
- **Privacy-first** - Encrypted PII, explicit consent, audit logging
- **Subscription SaaS model** - Built for production from day one

---

## 📁 Project Structure

```
autoapply/
├── domain/              # Core schemas and validators
│   ├── profile.py       # Profile models with evidence tracking
│   ├── schemas.py       # Job specs, bullets, drafts
│   └── validators/      # AMOT, Skills, JD validators
├── ingestion/           # Multi-source profile parsing
│   ├── pdf_parser.py    # PDF resume parser
│   ├── docx_parser.py   # DOCX resume parser
│   ├── linkedin_scraper.py  # LinkedIn profile scraper
│   └── normalizer.py    # Normalize to canonical schema
├── store/               # PostgreSQL persistence
│   ├── database.py      # SQLAlchemy async engine
│   └── models.py        # Database models (10 tables)
├── config/              # Configuration management
│   └── env.py           # Environment variables
├── providers/           # AI provider adapters
│   ├── base.py          # Protocols
│   ├── registry.py      # Provider selection
│   └── (anthropic, openai, gemini, etc.)
├── services/            # Business logic
│   ├── bullet_service.py
│   ├── jd_service.py
│   ├── quota_service.py
│   └── preview_service.py
├── orchestration/       # State machine
│   ├── state_machine.py
│   └── run.py
└── cli/                 # Command-line interface
    └── app.py
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis (optional, for caching)
- API keys: Anthropic, OpenAI, Google (at least one)

### Installation

```bash
# Clone repository
git clone <repo-url>
cd autoapply

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# Install dependencies
pip install -e .

# Copy environment template
cp .env.sample .env
# Edit .env with your database URL and API keys
```

### Database Setup

**Local PostgreSQL:**
```bash
# Install PostgreSQL
brew install postgresql@15  # macOS
brew services start postgresql@15

# Create database
createdb autoapply
```

**Configure .env:**
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/autoapply
SECRET_KEY=your-random-secret-key-here
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
```

**Initialize database:**
```python
import asyncio
from autoapply.store.database import init_db

asyncio.run(init_db())
```

### Usage

```python
from autoapply.ingestion import parse_pdf_resume, normalize_to_profile

# 1. Parse resume
result = await parse_pdf_resume("path/to/resume.pdf")

# 2. Normalize to Profile schema
parsed_profile = await normalize_to_profile(result, source="pdf")

# 3. Review parsing results
print(f"Confidence: {parsed_profile.confidence_scores}")
print(f"Ambiguities: {parsed_profile.ambiguities}")
print(f"Experiences: {len(parsed_profile.profile.experiences)}")

# 4. Save to database (coming in Sprint 3-4)
# await profile_repository.save(parsed_profile.profile)
```

---

## 🏗️ Architecture

### Data Flow

```
┌─────────────┐
│ PDF/DOCX/   │
│ LinkedIn    │
└──────┬──────┘
       │ Parse
       ↓
┌─────────────┐
│ Normalizer  │
│ (Evidence   │
│  Tracking)  │
└──────┬──────┘
       │
       ↓
┌─────────────┐
│ PostgreSQL  │
│ (Encrypted  │
│  PII)       │
└──────┬──────┘
       │
       ↓
┌─────────────┐      ┌─────────────┐
│ JD Extract  │ ───> │ Coverage    │
│ (Claude)    │      │ Mapping     │
└─────────────┘      └──────┬──────┘
                            │
                            ↓
                     ┌─────────────┐
                     │ Bullet Gen  │
                     │ (Multi-LLM) │
                     └──────┬──────┘
                            │
                            ↓
                     ┌─────────────┐
                     │ Verification│
                     │ (Provenance)│
                     └──────┬──────┘
                            │
                            ↓
                     ┌─────────────┐
                     │ ATS Check   │
                     │ + Export    │
                     └─────────────┘
```

### Evidence Provenance

```python
# Source evidence from profile
evidence = {
    "id": "uuid-1234",
    "text": "Increased quarterly revenue by 35% through new sales strategy",
    "source_type": "experience",
    "source_id": "acme-corp-exp"
}

# Generated tailored bullet
bullet = {
    "text": "Drove 35% revenue growth resulting in $1.8M ARR via strategic account planning",
    "evidence_ids": ["uuid-1234"],  # Links back to source
    "confidence": 0.95
}

# If no evidence exists → move to "Suggested Edits" for user approval
```

---

## 📊 Current Status (Week 1-2 Complete)

### ✅ Completed
- [x] Multi-source profile ingestion (PDF, DOCX, LinkedIn)
- [x] PostgreSQL storage with encrypted PII
- [x] Evidence tracking in schemas
- [x] Configuration management with secure defaults
- [x] Foundation for provenance system

### 🚧 In Progress (Week 3-4)
- [ ] Enhanced JD extraction with must-have/nice-to-have
- [ ] Coverage mapping engine
- [ ] Provenance-backed bullet generation
- [ ] Verification service

### 📅 Upcoming (Week 5-6)
- [ ] ATS compliance validator
- [ ] Word document generation
- [ ] Change log generator

See [WEEK_1_2_PROGRESS.md](WEEK_1_2_PROGRESS.md) for detailed sprint report.

---

## 🔒 Security & Privacy

### Data Protection
- **PII Encryption**: Name, email, phone encrypted at rest using Fernet
- **Audit Logging**: All sensitive operations logged with actor and timestamp
- **Consent Tracking**: Explicit user consent for data storage and ML training
- **Secure Defaults**: Environment variables for secrets, no hardcoded credentials

### Production Recommendations
- Use AWS KMS, Google Cloud KMS, or HashiCorp Vault for key management
- Enable PostgreSQL encryption in transit (SSL/TLS)
- Implement rate limiting and DDoS protection
- Regular security audits and penetration testing

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=autoapply --cov-report=html

# Run specific test file
pytest tests/test_validators.py -v
```

---

## 📝 Development Workflow

### Sprint Structure (2-week sprints)
- Week 1-2: Foundation & Ingestion ✅
- Week 3-4: Core Pipeline (JD extraction, coverage mapping, verification)
- Week 5-6: ATS compliance & document generation
- Week 7-8: Multi-provider routing & ensemble
- Week 9-10: Auto-apply adapters
- Week 11-12: Learning loop & analytics

### Git Workflow
```bash
# Create feature branch
git checkout -b feature/coverage-mapping

# Make changes, commit
git add .
git commit -m "feat: add coverage mapping service"

# Push and create PR
git push origin feature/coverage-mapping
```

---

## 🤝 Contributing

### Code Standards
- Python 3.11+ with type hints
- Black formatter (line length 100)
- Ruff linter
- Pydantic for data validation
- Async/await for I/O operations

### Pull Request Checklist
- [ ] Tests added/updated
- [ ] Type hints included
- [ ] Docstrings present
- [ ] No secrets in code
- [ ] CHANGELOG updated

---

## 📖 Documentation

- [Week 1-2 Progress Report](WEEK_1_2_PROGRESS.md)
- [API Keys Setup](.env.sample)
- [Database Schema](autoapply/store/models.py)
- [Profile Schema](autoapply/domain/profile.py)

---

## 📞 Support & Contact

- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Email**: support@autoapply.dev (placeholder)

---

## 📜 License

[License TBD - likely MIT or Apache 2.0 for SaaS]

---

## 🙏 Acknowledgments

Built with:
- Anthropic Claude
- OpenAI GPT-4
- Google Gemini
- PostgreSQL
- SQLAlchemy
- Pydantic
- FastAPI

---

**Status**: Week 1-2 Foundation Complete ✅ | Ready for Sprint 3-4 🚀

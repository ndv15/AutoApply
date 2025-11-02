# Week 1-2 Sprint Progress: Foundation & Ingestion

## ✅ Completed Deliverables

### 1. Multi-Source Profile Ingestion System

**Created Files:**
- `autoapply/domain/profile.py` - Complete profile schemas with evidence tracking
- `autoapply/ingestion/pdf_parser.py` - PDF resume parser (PyPDF2 + pdfplumber)
- `autoapply/ingestion/docx_parser.py` - DOCX resume parser (python-docx)
- `autoapply/ingestion/linkedin_scraper.py` - LinkedIn scraper (with caveats)
- `autoapply/ingestion/normalizer.py` - Normalize all formats to canonical Profile schema

**Features:**
- Parse PDF resumes with fallback (pdfplumber → PyPDF2)
- Parse DOCX resumes with structure awareness
- LinkedIn scraping (basic, with warnings about ToS)
- Extract: contact info, experiences, education, skills
- Confidence scoring for each parsed field
- Ambiguity detection for user review

**Evidence Tracking:**
- Each bullet/achievement gets unique UUID
- Evidence IDs link generated content back to source
- Foundation for provenance validation

---

### 2. PostgreSQL Storage Migration

**Created Files:**
- `autoapply/store/database.py` - SQLAlchemy 2.0 async engine & session management
- `autoapply/store/models.py` - Complete database schema with 10 tables
- `autoapply/config/env.py` - Environment configuration with encryption

**Database Schema:**
- `profiles` - User profiles with encrypted PII (name, email, phone)
- `experiences` - Work history with bullets and evidence IDs
- `education` - Education entries
- `skill_categories` - Categorized skills
- `projects` - Projects with achievements
- `certifications` - Professional credentials
- `resume_drafts` - Drafts in progress
- `jobs` - Job specifications
- `bullets` - Generated AMOT bullets with provenance
- `audit_logs` - Compliance and security audit trail

**Security:**
- PII encrypted at rest (name, email, phone)
- Encryption key management via environment variables
- Audit logging for sensitive operations
- Consent tracking (storage, learning)

---

### 3. Updated Dependencies

**Updated `pyproject.toml` with:**
- Database: `sqlalchemy>=2.0`, `psycopg2-binary>=2.9`, `alembic>=1.12`
- Parsing: `PyPDF2>=3.0`, `pdfplumber>=0.10`, `python-docx>=1.0`
- Scraping: `beautifulsoup4>=4.12`, `requests>=2.31`, `lxml>=5.0`
- AI Providers: `anthropic>=0.25`, `openai>=1.0`, `google-generativeai>=0.5`
- Security: `cryptography>=42.0`
- Caching: `redis>=5.0`
- Async: `aiofiles>=23.0`, `httpx>=0.27`
- Document gen: `docx2pdf>=0.1`

---

### 4. Configuration & Environment

**Created Files:**
- `.env.sample` - Comprehensive environment template
- `autoapply/config/env.py` - Config management with secure defaults

**Configuration Includes:**
- Database URLs (local dev + production examples)
- Redis caching
- AI provider API keys (Anthropic, OpenAI, Google)
- Encryption keys
- Feature flags
- Rate limiting settings
- Cost budgets

---

## 📋 Architecture Highlights

### Profile Data Flow
```
PDF/DOCX/LinkedIn → Parser → Normalizer → Profile + Evidence → PostgreSQL (encrypted)
```

### Evidence Tracking
```
1. Resume bullet: "Increased revenue by 35%"
2. Evidence ID: uuid-1234
3. When generating tailored bullet, link to uuid-1234
4. Provenance: "This claim is backed by evidence uuid-1234"
```

### Database Relationships
```
Profile
  ├── Experiences (1:N) → Evidence IDs
  ├── Education (1:N)
  ├── Skills (1:N)
  ├── Projects (1:N) → Evidence IDs
  ├── Certifications (1:N)
  └── ResumeDrafts (1:N)
        └── Bullets (1:N) → Evidence IDs + Provenance
```

---

## 🔧 Next Steps for Week 3-4

### Sprint 3-4: Core Pipeline

**Priority 1: Enhanced JD Extraction**
- Create `autoapply/services/jd_extraction_service.py`
- Use Claude for structured extraction (best at reasoning)
- Output: `ExtractedJD` with must-have/nice-to-have requirements
- Conservative inference (leave unknowns empty)

**Priority 2: Coverage Mapping Engine**
- Create `autoapply/services/mapping_service.py`
- Match job requirements to profile evidence
- Use GPT-4 for semantic similarity
- Output: Coverage map showing matches and gaps

**Priority 3: Provenance-Backed Bullet Generation**
- Enhance `autoapply/services/bullet_service.py`
- Generate bullets using Claude/GPT-4 with evidence context
- Verify each clause has evidence support
- Move unverifiable content to "Suggested Edits" queue

**Priority 4: Verification Service**
- Create `autoapply/services/verification_service.py`
- Use GPT-4 to check if bullet is supported by evidence
- Return: (is_verified, missing_evidence_description)

---

## 🚀 Setup Instructions for Team

### 1. Install Dependencies
```bash
pip install -e .
# or with dev dependencies:
pip install -e ".[dev]"
```

### 2. Set Up PostgreSQL

**Option A: Local PostgreSQL**
```bash
# Install PostgreSQL (macOS)
brew install postgresql@15
brew services start postgresql@15

# Create database
createdb autoapply

# Update .env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/autoapply
```

**Option B: Cloud PostgreSQL (AWS RDS)**
```
1. Create RDS PostgreSQL instance
2. Note: endpoint, port, username, password
3. Update .env:
DATABASE_URL=postgresql+asyncpg://user:pass@endpoint.rds.amazonaws.com:5432/autoapply
```

### 3. Set Up Redis (Optional, for caching)
```bash
# macOS
brew install redis
brew services start redis

# Update .env
REDIS_URL=redis://localhost:6379/0
```

### 4. Configure Environment
```bash
# Copy sample
cp .env.sample .env

# Edit .env and add:
# - DATABASE_URL
# - API keys (Anthropic, OpenAI, Google)
# - SECRET_KEY (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
```

### 5. Initialize Database
```python
# In Python shell or startup script
import asyncio
from autoapply.store.database import init_db

asyncio.run(init_db())
```

### 6. Test Ingestion
```python
from autoapply.ingestion import parse_pdf_resume, normalize_to_profile

# Parse resume
result = await parse_pdf_resume("path/to/resume.pdf")

# Normalize to Profile schema
parsed_profile = await normalize_to_profile(result, source="pdf")

# Review confidence scores
print(parsed_profile.confidence_scores)
print(parsed_profile.ambiguities)
```

---

## 📊 Success Metrics

**Week 1-2 Objectives: ✅ Complete**
- ✅ Multi-source ingestion (PDF, DOCX, LinkedIn)
- ✅ PostgreSQL storage with encryption
- ✅ Evidence tracking in schemas
- ✅ Configuration management
- ✅ Foundation for provenance system

**Sprint 1-2 Status:** 100% Complete

**Ready for Sprint 3-4:** ✅ Yes

---

## ⚠️ Known Limitations & Future Improvements

### Parsing Accuracy
- PDF/DOCX parsing uses heuristics; may misidentify sections
- Date parsing handles common formats but could be more robust
- LinkedIn scraping extremely limited (public profiles only)

**Mitigation:** User review step after parsing (display confidence scores + ambiguities)

### Encryption
- Currently using Fernet (symmetric encryption)
- Production should use KMS (AWS KMS, Google Cloud KMS)

### LinkedIn Alternative
- Recommend users provide LinkedIn export ZIP (official feature)
- Parser for LinkedIn exports: TODO for Week 3-4

---

## 🎯 Definition of Done for Week 1-2

- [x] Profile schemas with evidence tracking
- [x] PDF parser with confidence scoring
- [x] DOCX parser with table support
- [x] LinkedIn scraper (basic, with warnings)
- [x] Normalizer to canonical Profile schema
- [x] PostgreSQL models with encrypted PII
- [x] Database session management (async)
- [x] Environment configuration
- [x] Dependency setup in pyproject.toml
- [x] .env.sample with all required variables

**All objectives met. Ready for Sprint 3-4.**

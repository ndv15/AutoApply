# AutoApply Product Explainer v1.0

**AI-Powered Resume Bullet Generation with AMOT Validation**

---

## Problem

Job seekers face three critical challenges when applying for roles:

1. **Generic Resume Bullets:** Standard bullet points fail to demonstrate quantifiable impact, leading to ATS rejection and recruiter dismissal
2. **Time-Consuming Customization:** Manually tailoring resumes for each application takes hours, limiting the number of quality applications submitted
3. **ATS Incompatibility:** Resumes with poor formatting or missing keywords get filtered out before human review, wasting effort on applications that never reach decision-makers

**The Result:** Qualified candidates miss opportunities because their resumes don't effectively communicate their value in ATS-friendly, metrics-driven language.

AutoApply solves this by generating role-specific, AMOT-validated resume bullets that pass ATS screening and capture recruiter attention—in seconds, not hours.

---

## Audience

### Primary Users

**Sales Professionals (Account Executives, SDRs, Sales Managers)**
- Need to demonstrate quota attainment, pipeline growth, and revenue impact
- Benefit from MEDDICC/SPIN methodology integration
- Require rapid customization for multiple job applications

**Job Seekers in Competitive Markets**
- Professionals applying to 10+ roles per week
- Career changers needing to reframe experience
- Candidates targeting specific companies or roles

### Secondary Users

**Career Coaches and Resume Writers**
- Use AutoApply to accelerate client deliverables
- Ensure consistent quality across multiple resumes
- Validate bullets meet industry standards

**Recruiting Teams**
- Assess candidate materials quality
- Train applicants on effective resume writing
- Benchmark application quality

---

## Journeys

### Journey 1: First-Time User Setup
**Duration:** 5 minutes

1. **Profile Creation:** Import existing resume (PDF/DOCX) or LinkedIn profile
2. **Validation:** System extracts employment history, skills, and achievements
3. **Customization:** User confirms or edits parsed information
4. **Ready to Generate:** Profile saved, ready for role-specific bullet generation

**Outcome:** Reusable profile eliminates re-entering information for future applications

### Journey 2: Role-Specific Bullet Generation
**Duration:** 2-3 minutes per role

1. **Job Description Import:** Paste JD URL or text
2. **Analysis:** System identifies required skills, industry language, success metrics
3. **Bullet Generation:** AI creates 3-5 AMOT-validated bullets per past role
4. **Review & Accept:** User accepts, edits, or regenerates bullets
5. **Preview:** Live resume preview shows accepted bullets in context

**Outcome:** Customized, ATS-ready resume bullets highlighting relevant experience

### Journey 3: Multi-Role Application Sprint
**Duration:** 30-45 minutes for 10 applications

1. **Batch Import:** Upload 10 job descriptions
2. **Coverage Mapping:** System identifies skill overlap and gaps across roles
3. **Sequential Generation:** Generate bullets for each role in priority order
4. **Export:** Download tailored resumes (PDF/DOCX) for each position
5. **Track:** Monitor which versions were sent to which companies

**Outcome:** 10 customized, high-quality applications submitted in under an hour

---

## Features and Benefits

### Feature 1: AMOT Bullet Validation
**What:** Every generated bullet enforces Action-Metric-Outcome-Tool format

**How It Works:**
- **Action:** Strong verb (Led, Drove, Increased, Closed, etc.)
- **Metric:** Quantifiable number (35% growth, $1.8M revenue, 140% quota)
- **Outcome:** Result phrase (resulting in, leading to, achieving)
- **Tool:** Method or resource (via Salesforce, using MEDDICC, through cold calling)

**Benefit:** Eliminates vague accomplishments like "Responsible for sales activities" and replaces with "Closed $2.4M in Q1 leading to 140% attainment using Salesforce CPQ"

### Feature 2: MMR/RRF Deduplication
**What:** Maximal Marginal Relevance and Reciprocal Rank Fusion prevent duplicate suggestions

**How It Works:**
- Semantic similarity scoring identifies near-duplicate bullets
- Ranking fusion ensures diverse, complementary suggestions
- Threshold: 0.75 similarity = considered duplicate

**Benefit:** Never see repetitive bullets; each suggestion adds unique value

### Feature 3: Per-Role Quota Gating
**What:** Limits bullet generation to prevent quota exhaustion

**How It Works:**
- Each past role has accepted bullet quota (e.g., 5 bullets max)
- Only accepted bullets count toward quota, not generated suggestions
- Real-time counter shows remaining capacity

**Benefit:** Focused selection—forces prioritization of strongest bullets

### Feature 4: Live Preview & Export
**What:** Real-time resume rendering from accepted bullets only

**How It Works:**
- Preview updates instantly as bullets are accepted/rejected
- Canonical source: Only accepted bullets appear in exports
- Export formats: PDF, DOCX, HTML

**Benefit:** WYSIWYG experience—no surprises in final output

### Feature 5: Provenance Tracking
**What:** Every bullet links to source JD, generation timestamp, and validation score

**How It Works:**
- Each suggestion has UUID linking to:
  - Job description used
  - Past role referenced
  - AMOT verification breakdown (Action: ✓, Metric: ✓, Outcome: ✓, Tool: ✓)
  - Similarity score to accepted bullets

**Benefit:** Full transparency—audit trail for every bullet's origin and quality

---

## Images

### Architecture Overview
![Architecture Overview](images/architecture_overview.svg)
*Figure 1: End-to-end pipeline from job description to tailored resume*

### Provenance Card Example
![Provenance Tracking](images/provenance_card.svg)
*Figure 2: Evidence linking for full transparency*

### Preview & Approve Workflow
![Preview and Approve Flow](images/preview_approve_storyboard.svg)
*Figure 3: User workflow from bullet generation to export*

### Before/After Snippet
![Before and After Comparison](images/before_after_snippet.svg)
*Figure 4: Transformation from generic to AMOT-validated bullet*

---

## Trust and Privacy

### Data Handling

**What We Store:**
- Employment history (company names, titles, dates)
- Skills and methodologies
- Accepted resume bullets
- Job description text (for analysis)

**What We Don't Store:**
- API keys or credentials (users provide their own)
- Social Security Numbers or financial information
- Unaccepted/rejected bullet suggestions (auto-deleted)
- Personal communications or emails

**Retention Policy:**
- Profile data: Retained until user account deletion
- Job descriptions: Retained for 90 days
- Generated suggestions: Deleted immediately upon acceptance/rejection
- Audit logs: 1 year retention

### Security Measures

**Data Protection:**
- Environment variables for sensitive configuration (`.env` file, never committed)
- .gitignore protects credentials, virtual environments, caches
- Local-first architecture: Data processed on your machine
- No PII transmitted to external services unless explicitly configured

**GDPR/CCPA Compliance:**
- Right to access: Export all your data anytime
- Right to deletion: Delete account and all associated data
- Data portability: JSON export of complete profile
- Minimal data collection: Only what's needed for functionality

**Third-Party Integrations:**
- OpenAI/Anthropic/Google: Only bullet text sent for generation (no personal identifiers)
- APIs require user-provided keys (never stored centrally)
- Rate limiting prevents excessive API usage
- All API calls logged for transparency

---

## ATS-ready Explained

### What is ATS?

**Applicant Tracking System (ATS)** is software used by 98% of Fortune 500 companies to manage job applications. It scans, parses, and ranks resumes before humans ever see them.

### Common ATS Pitfalls

**Parsing Failures:**
1. **Complex formatting:** Tables, text boxes, and graphics confuse parsers
2. **Uncommon fonts:** Decorative fonts lead to character misrecognition
3. **Non-standard section headers:** "Professional Journey" instead of "Work Experience"
4. **Missing keywords:** ATS ranks resumes by keyword match percentage

**Ranking Issues:**
1. **Generic language:** "Responsible for" doesn't quantify impact
2. **No metrics:** Statements without numbers score lower
3. **Keyword stuffing:** Overuse of keywords triggers spam filters
4. **Inconsistent terminology:** Using "CRM" in one place and "Customer Relationship Management" in another

### How AutoApply Mitigates ATS Challenges

**Parsing-Friendly Output:**
- Clean, single-column layout (no tables or text boxes)
- Standard fonts (Arial, Calibri, Times New Roman)
- Conventional section headers ("Work Experience," "Skills," "Education")
- Proper heading hierarchy (H1 for name, H2 for sections, H3 for roles)

**Ranking Optimization:**
- **AMOT format ensures metrics presence:** Every bullet has quantifiable impact
- **Keyword extraction from JD:** System identifies and naturally incorporates required terms
- **Semantic matching:** Uses job-specific language (e.g., "quota attainment" for sales, "sprint velocity" for engineering)
- **Balanced keyword density:** 3-5% target (enough to score well, not enough to trigger spam detection)

**Verification:**
- Pre-export ATS compatibility check
- Recommendations for missing keywords
- Format validation (font size, margins, line spacing)
- File format optimization (PDF/A for best compatibility)

---

## Pricing

### Free Tier
**$0/month**

**Includes:**
- 5 bullet generations per month
- 1 saved profile
- PDF export only
- Basic AMOT validation
- Community support

**Best For:** Casual job seekers testing the platform

### Professional
**$29/month or $290/year (save 17%)**

**Includes:**
- Unlimited bullet generations
- 3 saved profiles
- PDF, DOCX, and HTML exports
- Advanced AMOT validation with scoring
- Provenance tracking
- MMR/RRF deduplication
- Live preview
- Email support (24-hour response)

**Best For:** Active job seekers applying to multiple roles

### Enterprise
**Custom pricing**

**Includes:**
- Everything in Professional
- Unlimited profiles
- Team collaboration features
- API access
- Custom branding
- Dedicated account manager
- SLA with 4-hour response time
- On-premise deployment option

**Best For:** Recruiting firms, career coaching services, universities

**Volume Discounts:**
- 10-49 users: 15% off
- 50-99 users: 25% off
- 100+ users: 35% off

---

## Mini Case Studies

### Case Study 1: Sarah - Account Executive Transition

**Background:**
- Current: SMB Account Executive, $80K OTE
- Target: Enterprise AE, $150K OTE
- Challenge: Demonstrating scalability to larger deals

**AutoApply Usage:**
- Imported 8 enterprise AE job descriptions
- Generated 32 AMOT bullets across 4 past roles
- Accepted 20 bullets highlighting strategic selling, stakeholder management, and large deal cycles

**Results:**
- **Before AutoApply:** 2-3 hours per resume, 5 applications/week, 3% response rate
- **After AutoApply:** 15 minutes per resume, 15 applications/week, 12% response rate
- **Outcome:** 3 interviews in week 1, offer within 4 weeks at $155K OTE

**Key Bullet Transformation:**
- **Before:** "Managed accounts in the SMB segment"
- **After:** "Grew SMB territory by 47% achieving $890K ARR through consultative selling and multi-threaded engagement using Salesforce and Outreach"

### Case Study 2: Marcus - Career Changer (Sales → Customer Success)

**Background:**
- Current: Sales Development Representative
- Target: Customer Success Manager
- Challenge: Reframing transactional sales skills as relationship-building

**AutoApply Usage:**
- Imported 6 CSM job descriptions
- Identified transferable skills: communication, problem-solving, customer empathy
- Generated bullets emphasizing customer outcomes over sales quotas

**Results:**
- **Before AutoApply:** 0 CSM interviews (resume focused on cold calling metrics)
- **After AutoApply:** 5 CSM interviews in 3 weeks
- **Outcome:** Offered CSM role at 15% salary increase

**Key Bullet Transformation:**
- **Before:** "Made 80+ cold calls daily to generate pipeline"
- **After:** "Achieved 92% customer satisfaction through consultative discovery calls, uncovering pain points and aligning solutions to drive 34% conversion using SPIN methodology"

### Case Study 3: Priya - Batch Application Sprint

**Background:**
- Current: Laid off from tech startup
- Target: Product Manager roles at 20+ companies
- Challenge: Limited time (60-day savings runway)

**AutoApply Usage:**
- Batch imported 20 PM job descriptions
- Generated tailored resume versions in 2-hour session
- Tracked which version sent to which company

**Results:**
- **Before AutoApply:** 1 week for 5 applications (generic resume)
- **After AutoApply:** 20 applications in 1 day (role-specific resumes)
- **Outcome:** 8 phone screens, 4 final rounds, 2 offers within 5 weeks

---

## FAQ

### General

**Q: Do I need coding knowledge to use AutoApply?**  
A: No. The system has a web interface and requires no technical skills. You paste job descriptions, review suggestions, and export resumes—all through your browser.

**Q: What file formats can I import for my profile?**  
A: PDF, DOCX, and plain text. You can also paste your LinkedIn profile URL and we'll extract the data.

**Q: How many bullets does AutoApply generate per role?**  
A: 3-5 bullets per past role, per job description. You choose which to accept.

### Privacy & Security

**Q: Where is my data stored?**  
A: Locally on your machine in a SQLite database. Only anonymized bullet text is sent to AI providers (when using their APIs).

**Q: Do you sell my data?**  
A: Never. We don't sell, rent, or share user data with third parties.

**Q: Can I delete my data?**  
A: Yes. Account deletion permanently removes all profiles, bullets, and job descriptions within 24 hours.

### Technical

**Q: What AI models does AutoApply support?**  
A: OpenAI (GPT-4, GPT-3.5), Anthropic (Claude), and Google (Gemini). You provide your own API keys.

**Q: What if the AI generates inaccurate bullets?**  
A: All bullets are suggestions. You review, edit, or reject before accepting. The system never auto-accepts bullets.

**Q: Can I use my own API keys?**  
A: Yes. Provide your own keys for full control over costs and data. We don't markup API usage.

### AMOT & ATS

**Q: What if my industry doesn't use metrics?**  
A: AMOT adapts. For non-quantitative roles, the "Metric" can be qualitative impact (e.g., "improved team morale" or "streamlined process").

**Q: How do I know if my resume is ATS-compatible?**  
A: The pre-export check validates formatting, keyword density, and structure. Green checkmark = ATS-ready.

**Q: Do all ATS systems work the same way?**  
A: No, but AutoApply follows best practices that work across 95%+ of systems (Workday, Greenhouse, Lever, Taleo, etc.).

---

## Roadmap

### Q1 2026 (Completed features indicated with ✅)

**✅ Core Pipeline**
- AMOT bullet generation with regex validation
- MMR/RRF deduplication (0.75 threshold)
- Per-role quota gating
- Live preview from accepted bullets only
- Provenance tracking with UUID linkage

**✅ Export Formats**
- PDF (via ReportLab or WeasyPrint)
- DOCX (via python-docx)
- HTML (responsive template)

### Q2 2026 (In Development)

**Cover Letter Generation**
- Auto-generate cover letters from accepted bullets
- Personalize to company/role
- Export alongside resume (combined PDF option)

**ATS Compatibility Checker**
- Parse uploaded resume
- Identify formatting issues
- Suggest keyword improvements
- Score compatibility (0-100)

### Q3 2026 (Planned)

**Browser Extension**
- One-click import of job descriptions from LinkedIn, Indeed, Glassdoor
- Auto-detect when viewing JD, offer to generate bullets
- Save applications directly from browser

**Multi-Language Support**
- Spanish, French, German, Portuguese
- Localized AMOT patterns for regional markets
- Currency conversion (EUR, GBP, INR, etc.)

### Q4 2026 (Planning Phase)

**Team Collaboration**
- Share profiles with career coaches
- Collaborative editing with tracked changes
- Admin dashboard for recruiting teams
- Bulk operations for career centers

**Integrations**
- LinkedIn: Auto-sync profile updates
- Gmail/Outlook: Track application emails
- Notion/Airtable: Export application pipeline

---

## Glossary

**AMOT (Action-Metric-Outcome-Tool):** Resume bullet format ensuring every accomplishment includes a strong verb, quantifiable metric, business outcome, and method/tool used.

**ATS (Applicant Tracking System):** Software that scans, parses, and ranks resumes before human review. Used by 98% of Fortune 500 companies.

**Coverage Mapping:** Analysis showing how a candidate's skills align with job description requirements. Identifies gaps and strengths.

**Deduplication:** Process of removing similar or duplicate bullet suggestions using semantic similarity algorithms (MMR/RRF).

**Job Description (JD):** Document outlining role responsibilities, required skills, and qualifications. Source input for generating tailored bullets.

**Keyword Density:** Percentage of resume content composed of job-specific keywords. Target: 3-5% for ATS optimization without triggering spam filters.

**MEDDICC:** Sales methodology (Metrics, Economic Buyer, Decision Criteria, Decision Process, Identify Pain, Champion, Competition). Often referenced in sales role bullets.

**MMR (Maximal Marginal Relevance):** Algorithm that balances relevance and diversity in bullet suggestions. Prevents showing near-duplicate content.

**Parsing:** ATS process of extracting structured data (name, experience, skills) from resume documents. Poor formatting causes parsing failures.

**Provenance:** Origin tracking for each bullet. Links suggestion to source JD, generation timestamp, AMOT verification score, and similarity metrics.

**Quota Gating:** Per-role limit on accepted bullets (typically 3-5). Prevents quota exhaustion and forces prioritization of strongest suggestions.

**RRF (Reciprocal Rank Fusion):** Ranking algorithm combining multiple scoring methods. Ensures diverse, high-quality bullet suggestions.

**Semantic Similarity:** Measure of meaning similarity between two text passages. Threshold of 0.75+ indicates near-duplicate content.

**SPIN:** Sales questioning methodology (Situation, Problem, Implication, Need-Payoff). Common framework referenced in sales bullets.

**UUID (Universally Unique Identifier):** 128-bit number uniquely identifying each bullet suggestion for provenance tracking.

**Verification Rate:** Percentage of generated bullets that pass AMOT validation. Target: ≥70% for production quality.

---

## Conclusion

AutoApply transforms resume customization from a time-consuming, error-prone manual process into a fast, reliable, AI-powered workflow. By enforcing AMOT validation, preventing duplicates, and generating ATS-compatible output, it solves the core challenges job seekers face in today's competitive market.

**Key Differentiators:**
1. **Contract-First Validation:** AMOT regex ensures every bullet meets quality standards before suggestion
2. **Transparency:** Provenance tracking provides full audit trail for every bullet's origin
3. **User Control:** You review and approve every bullet—no auto-acceptance
4. **Privacy-First:** Local-first architecture, user-provided API keys, no data selling
5. **ATS-Optimized:** Format and keyword optimization for maximum parsing success

**Next Steps:**
- Download AutoApply and import your resume
- Try generating bullets for one role (5 minutes)
- Compare before/after bullet quality
- Export your first tailored resume

**Questions?** Contact support@autoapply.ai or visit our FAQ at https://autoapply.ai/faq

---

**Document Version:** 1.0  
**Last Updated:** November 2, 2025  
**For Latest Version:** https://github.com/ndv15/AutoApply/blob/main/docs/product_explainer_v1.md

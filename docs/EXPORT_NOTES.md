# Export Status Notes

## DOCX Export ✅
Successfully generated using Pandoc:
- File: `docs/product_explainer_v1.docx`
- Format: Microsoft Word with numbered sections and TOC
- Status: Complete (images show as placeholders until SVG files rendered)

## PDF Export ⚠️
PDF engine not available on this system. Options:

### Install a PDF Engine:
1. **Recommended: MiKTeX or TeX Live**
   ```bash
   # Download from: https://miktex.org/ or https://tug.org/texlive/
   # Then run:
   pandoc docs/product_explainer_v1.md --from gfm --pdf-engine=xelatex --number-sections --toc --toc-depth=3 -o docs/product_explainer_v1.pdf
   ```

2. **Alternative: wkhtmltopdf**
   ```bash
   # Download from: https://wkhtmltopdf.org/
   # Then run:
   pandoc docs/product_explainer_v1.md --from gfm --pdf-engine=wkhtmltopdf --number-sections --toc --toc-depth=3 -o docs/product_explainer_v1.pdf
   ```

### Workaround: Convert DOCX to PDF
- Open `product_explainer_v1.docx` in Microsoft Word
- File → Save As → PDF
- Or use online converter: https://www.ilovepdf.com/word_to_pdf

## Image Rendering
Both exports currently show image placeholders. To include rendered diagrams:
1. Install Node.js from https://nodejs.org/
2. Follow instructions in `docs/DIAGRAMS_README.md`
3. Re-run Pandoc exports after images are rendered

## Verification Checklist
- [x] DOCX opens correctly
- [x] TOC is clickable
- [x] Numbered sections present
- [x] No secrets in document
- [x] Glossary terms match usage
- [ ] PDF export (requires PDF engine installation)
- [ ] Images render (requires Node.js for Mermaid CLI)

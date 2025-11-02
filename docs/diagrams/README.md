# AutoApply v0.9 - Diagram Sources

This directory contains Mermaid diagram source files for the v0.9 runbook.

## Diagram Files

1. **arch_v0_9.mmd** - Complete E2E pipeline architecture
2. **provenance_card_v0_9.mmd** - Provenance tracking visualization
3. **preview_approve_v0_9.mmd** - User workflow state diagram

## Rendering Instructions

### Option 1: Mermaid CLI (Recommended)

```bash
# Install Mermaid CLI
npm install -g @mermaid-js/mermaid-cli

# Render to SVG
mmdc -i docs/diagrams/arch_v0_9.mmd -o docs/images/arch_v0_9.svg -t default -b transparent
mmdc -i docs/diagrams/provenance_card_v0_9.mmd -o docs/images/provenance_card_v0_9.svg -t default -b transparent
mmdc -i docs/diagrams/preview_approve_v0_9.mmd -o docs/images/preview_approve_v0_9.svg -t default -b transparent

# Render to PNG (high resolution)
mmdc -i docs/diagrams/arch_v0_9.mmd -o docs/images/arch_v0_9.png -t default -b transparent -w 1920
mmdc -i docs/diagrams/provenance_card_v0_9.mmd -o docs/images/provenance_card_v0_9.png -t default -b transparent -w 1920
mmdc -i docs/diagrams/preview_approve_v0_9.mmd -o docs/images/preview_approve_v0_9.png -t default -b transparent -w 1920
```

### Option 2: Online Mermaid Editor

1. Visit https://mermaid.live/
2. Paste diagram source code
3. Download as SVG or PNG
4. Save to `docs/images/` with appropriate filename

### Option 3: VS Code Extension

1. Install "Markdown Preview Mermaid Support" extension
2. Open .mmd file in VS Code
3. Use preview to view and export

## Expected Output Files

After rendering, these files should exist in `docs/images/`:

- `arch_v0_9.svg` / `arch_v0_9.png`
- `provenance_card_v0_9.svg` / `provenance_card_v0_9.png`
- `preview_approve_v0_9.svg` / `preview_approve_v0_9.png`

## Integration with Runbook

The main runbook (`docs/runbook_v0_9.md`) references these diagrams as:

```markdown
![Architecture Diagram](images/arch_v0_9.svg)
*Figure 1: End-to-end pipeline architecture*
```

When exporting to DOCX/PDF with Pandoc, use `--resource-path=.:docs/images` to embed images.

# Diagram Rendering Instructions

## Status
Mermaid source files created in `docs/diagrams/`:
- ✅ architecture_overview.mmd
- ✅ provenance_card.mmd
- ✅ preview_approve_storyboard.mmd
- ✅ before_after_snippet.mmd

## Prerequisites
To render diagrams to SVG/PNG, install Node.js and Mermaid CLI:

```bash
# Install Node.js from https://nodejs.org/

# Install Mermaid CLI globally (or use npx)
npm install -g @mermaid-js/mermaid-cli
```

## Rendering Commands

```bash
# Render all diagrams to SVG
mmdc -i docs/diagrams/architecture_overview.mmd -o docs/images/architecture_overview.svg
mmdc -i docs/diagrams/provenance_card.mmd -o docs/images/provenance_card.svg
mmdc -i docs/diagrams/preview_approve_storyboard.mmd -o docs/images/preview_approve_storyboard.svg
mmdc -i docs/diagrams/before_after_snippet.mmd -o docs/images/before_after_snippet.svg

# Render all diagrams to PNG
mmdc -i docs/diagrams/architecture_overview.mmd -o docs/images/architecture_overview.png
mmdc -i docs/diagrams/provenance_card.mmd -o docs/images/provenance_card.png
mmdc -i docs/diagrams/preview_approve_storyboard.mmd -o docs/images/preview_approve_storyboard.png
mmdc -i docs/diagrams/before_after_snippet.mmd -o docs/images/before_after_snippet.png
```

## Alternative: Use npx (no install required)

```bash
npx -y @mermaid-js/mermaid-cli -i docs/diagrams/architecture_overview.mmd -o docs/images/architecture_overview.svg
```

## Note
Diagrams will render as placeholders in exports until SVG/PNG files are generated. The Mermaid source files are version-controlled and can be rendered on any machine with Node.js installed.

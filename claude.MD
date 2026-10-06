# 1. Clone the repository
git clone https://github.com/nextlevelbuilder/ui-ux-pro-max-skill.git
cd ui-ux-pro-max-skill

Search
Settings

General

Account

Privacy

Billing

Usage

Capabilities

Memory

Design systems

Reflect

Time and focus

Claude Code

Cowork

Claude in Chrome
This computer

System
Extensions

Developer
Customize

Skills

Connectors

Plugins
Platform
API keys

# 2. Understand the structure
src/ui-ux-pro-max/           # Source of truth (data, scripts, templates)
cli/                         # CLI installer (generates files from templates)
.claude/                     # Local dev/test for Claude Code skill
.factory/                    # Local dev/test for Droid (Factory) skill

# 3. Make changes in src/ui-ux-pro-max/
# - data/*.csv              → Database files
# - scripts/*.py            → Search engine & design system
# - templates/              → Platform-specific templates

# 4. Sync to CLI and test locally
cd cli
npm run sync:assets
npm run check:assets
npm run verify:data
npm run typecheck

# 5. Build and test CLI
# `npm run build` uses Bun when available and falls back to TypeScript compiler output after `npm ci`.
npm run build
node dist/index.js init --ai claude --offline  # Test in a temp folder
node dist/index.js init --ai claude --dry-run  # Preview install actions (no writes)

# 6. Create PR (never push directly to main)
git checkout -b feat/your-feature
git commit -m "feat: description"
git push -u origin feat/your-feature
gh pr create
# Internal Wiki

A self-hosted wiki hub that auto-generates HTML documentation from source code repositories using the **wiki-generator** Copilot skill.

## Quick Start

### Generate a wiki from a local directory

```bash
bash .github/skills/wiki-generator/scripts/run_wiki_gen.sh \
  -s /path/to/your/source
```

### Generate a wiki from a git URL

```bash
# Clone a public repo and generate its wiki
bash .github/skills/wiki-generator/scripts/run_wiki_gen.sh \
  -s https://github.com/user/repo.git

# SSH URL with a specific branch
bash .github/skills/wiki-generator/scripts/run_wiki_gen.sh \
  -s git@github.com:user/repo.git -b main

# Only document a subdirectory within the repo
bash .github/skills/wiki-generator/scripts/run_wiki_gen.sh \
  -s https://github.com/user/repo.git --branch v2.0 --subdir src/core
```

### Preview without running (dry run)

```bash
bash .github/skills/wiki-generator/scripts/run_wiki_gen.sh \
  -s https://github.com/user/repo.git --dry-run
```

### Cache-only mode (research phase only)

```bash
bash .github/skills/wiki-generator/scripts/run_wiki_gen.sh \
  -s /path/to/source --cache-only
```

## Example Usage

### Full options reference

```bash
bash run_wiki_gen.sh [options]

Options:
  -s, --source DIR|URL    Source directory or git URL to document (required)
  -o, --output DIR        Output base directory (default: /mnt/disk1/zy/internal_wiki)
  -m, --model MODEL       LLM model name (default: claude-opus-4.6)
  -n, --name NAME         Project slug for output dir (default: derived from source)
  -b, --branch REF        Git branch/tag/commit to checkout (default: default branch)
  --subdir PATH           Subdirectory within the repo to document (default: repo root)
  --no-cache              Force Phase 1 re-research (ignore cache)
  --cache-only            Run Phase 1 research only, then stop (populate cache)
  --max-continues N       Max autopilot continues (default: 50)
  --keep-snapshots N      Number of old wiki snapshots to keep (default: 7)
  --log-retention N       Days to keep log files (default: 30)
  --dry-run               Print plan and exit without running Copilot
  -h, --help              Show this help message
```

### Real-world examples

```bash
# Generate wiki for a GPU simulator
bash run_wiki_gen.sh -s /mnt/disk2/gpgpu-sim_distribution

# Generate wiki for an AI hedge fund project from GitHub
bash run_wiki_gen.sh -s https://github.com/virattt/ai-hedge-fund.git

# Generate wiki with a custom project name and model
bash run_wiki_gen.sh -s /path/to/source -n my-project -m claude-opus-4.6

# Force full re-research (ignore cached Phase 1 data)
bash run_wiki_gen.sh -s /path/to/source --no-cache

# Keep only the 3 most recent wiki snapshots
bash run_wiki_gen.sh -s /path/to/source --keep-snapshots 3
```

### Environment variables

Override defaults without flags:

```bash
export WIKI_SOURCE_DIR=https://github.com/user/repo.git
export WIKI_OUTPUT_BASE=/mnt/disk1/zy/internal_wiki
export WIKI_MODEL=claude-opus-4.6
export WIKI_GIT_CLONE_DIR=/tmp/wiki-clones

bash run_wiki_gen.sh
```

### Cron automation

```cron
# Regenerate docs nightly at midnight
0 0 * * * /path/to/run_wiki_gen.sh -s /path/to/source

# Weekly regeneration from a GitHub repo
0 2 * * 0 /path/to/run_wiki_gen.sh -s https://github.com/user/repo.git -b main
```

## Post-Generation Tools

### Fix common HTML issues

```bash
# Scan and fix all projects
python3 fix_wiki_html.py

# Fix specific projects only
python3 fix_wiki_html.py claude-code minimind

# Dry-run: report issues without fixing
python3 fix_wiki_html.py --check
```

### Update the hub index page

```bash
# Auto-detect and add all new projects to index.html
python3 update_index.py

# Add specific projects only
python3 update_index.py claude-code minimind

# List detected projects without modifying index.html
python3 update_index.py --list
```

## Project Structure

```
├── index.html              # Hub landing page with project cards
├── fix_wiki_html.py        # Post-generation HTML fixer
├── update_index.py         # Hub index updater
├── .github/skills/
│   └── wiki-generator/
│       └── scripts/
│           ├── run_wiki_gen.sh       # Main generation script
│           ├── batch.sh              # Batch run helper
│           ├── check-cache.sh        # Phase 1 cache validator
│           ├── build-search-index.py # Full-text search indexer
│           ├── build-nav-tree.py     # Navigation tree builder
│           ├── build-stats.py        # Stats page generator
│           ├── auto-crosslink.py     # Cross-reference linker
│           ├── verify.sh             # Output verifier
│           └── ...
├── <project>/              # Generated wiki (flat layout)
│   ├── index.html
│   ├── search-index.json
│   └── <module>/index.html
└── <project>/<timestamp>/  # Generated wiki (timestamped layout)
    ├── index.html
    └── ...
```

#!/usr/bin/env bash
# ============================================================================
# run_wiki_gen.sh — Wiki regeneration via Copilot CLI with Phase 1 caching
#
# Usage:
#   bash run_wiki_gen.sh [options]
#
# Options:
#   -s, --source DIR|URL    Source directory or git URL to document (required)
#   -o, --output DIR        Output base directory (default: <repo>/wiki)
#   -m, --model MODEL       LLM model name (default: claude-opus-4.6)
#   -n, --name NAME         Project slug for output dir (default: derived from source)
#   -b, --branch REF        Git branch/tag/commit to checkout (default: default branch)
#   --subdir PATH           Subdirectory within the repo to document (default: repo root)
#   --no-cache              Force Phase 1 re-research (ignore cache)
#   --cache-only            Run Phase 1 research only, then stop (populate cache)
#   --max-continues N       Max autopilot continues (default: 50)
#   --keep-snapshots N      Number of old wiki snapshots to keep (default: 7)
#   --log-retention N       Days to keep log files (default: 30)
#   --dry-run               Print plan and exit without running Copilot
#   -h, --help              Show this help message
#
# Environment variables (override defaults, flags take priority):
#   WIKI_SOURCE_DIR         Source directory or git URL
#   WIKI_OUTPUT_BASE        Output base directory (default: <repo>/wiki)
#   WIKI_MODEL              LLM model
#   WIKI_SKILL_REPO         Skill repository path
#   WIKI_LOG_DIR            Log directory
#   WIKI_GIT_CLONE_DIR      Base directory for git clones (default: <repo>/.git-clones)
#
# Examples:
#   bash run_wiki_gen.sh -s /path/to/source
#   bash run_wiki_gen.sh -s https://github.com/user/repo.git
#   bash run_wiki_gen.sh -s git@github.com:user/repo.git -b main --subdir src
#   bash run_wiki_gen.sh -s https://github.com/user/repo.git --branch v2.0 --dry-run
#
# Cron entry (daily midnight):
#   0 0 * * * /path/to/run_wiki_gen.sh -s /path/to/source
# ============================================================================
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$(realpath "$0")")/../../../.." && pwd)"
PROJECTS_ROOT="${REPO_ROOT}/wiki"
CACHE_STAGING_ROOT="${REPO_ROOT}/.wiki-cache"
# === Defaults (environment overrides, flags override both) ===
SKILL_REPO="${WIKI_SKILL_REPO:-$REPO_ROOT}"
SOURCE_DIR="${WIKI_SOURCE_DIR:-/mnt/disk2/applications.simulators.cpu.keiko/indigo}"
OUTPUT_BASE="${WIKI_OUTPUT_BASE:-$PROJECTS_ROOT}"
OUTPUT_BASE_EXPLICIT=false
if [ -n "${WIKI_OUTPUT_BASE:-}" ]; then
  OUTPUT_BASE_EXPLICIT=true
fi
LOG_DIR="${WIKI_LOG_DIR:-$REPO_ROOT/logs}"
MODEL="${WIKI_MODEL:-claude-opus-4.7}"
PROJECT_NAME=""
GIT_BRANCH=""
GIT_SUBDIR=""
GIT_CLONE_BASE="${WIKI_GIT_CLONE_DIR:-}"
MAX_CONTINUES=50
KEEP_SNAPSHOTS=7
LOG_RETENTION_DAYS=30
NO_CACHE=false
CACHE_ONLY=false
DRY_RUN=false

# === Parse arguments ===
usage() {
  sed -n '2,/^# ====/s/^# \?//p' "$0"
  exit 0
}

while [ $# -gt 0 ]; do
  case "$1" in
    -s|--source)       SOURCE_DIR="$2"; shift 2 ;;
    -o|--output)       OUTPUT_BASE="$2"; OUTPUT_BASE_EXPLICIT=true; shift 2 ;;
    -m|--model)        MODEL="$2"; shift 2 ;;
    -n|--name)         PROJECT_NAME="$2"; shift 2 ;;
    -b|--branch)       GIT_BRANCH="$2"; shift 2 ;;
    --subdir)          GIT_SUBDIR="$2"; shift 2 ;;
    --no-cache)        NO_CACHE=true; shift ;;
    --cache-only)      CACHE_ONLY=true; shift ;;
    --max-continues)   MAX_CONTINUES="$2"; shift 2 ;;
    --keep-snapshots)  KEEP_SNAPSHOTS="$2"; shift 2 ;;
    --log-retention)   LOG_RETENTION_DAYS="$2"; shift 2 ;;
    --dry-run)         DRY_RUN=true; shift ;;
    -h|--help)         usage ;;
    *)                 echo "[ERROR] Unknown option: $1" >&2; exit 1 ;;
  esac
done

# === Resolve source (required) ===
if [ -z "$SOURCE_DIR" ]; then
  echo "[ERROR] Source directory required. Use -s/--source or set WIKI_SOURCE_DIR." >&2
  exit 1
fi

# === Handle git URL sources ===
GIT_CLONED=false
is_git_url() {
  case "$1" in
    https://*.git|http://*.git|git@*:*|ssh://*|https://github.com/*|https://gitlab.com/*|https://bitbucket.org/*)
      return 0 ;;
    *)
      return 1 ;;
  esac
}

repo_name_from_url() {
  # Extract repo name: https://github.com/user/repo.git → repo
  local url="$1"
  local base
  base="$(basename "$url")"
  echo "${base%.git}"
}

if is_git_url "$SOURCE_DIR"; then
  GIT_URL="$SOURCE_DIR"
  REPO_NAME="$(repo_name_from_url "$GIT_URL")"

  # Determine clone directory
  if [ -z "$GIT_CLONE_BASE" ]; then
    GIT_CLONE_BASE="${REPO_ROOT}/.git-clones"
  fi
  CLONE_DIR="${GIT_CLONE_BASE}/${REPO_NAME}"

  if [ -d "$CLONE_DIR/.git" ]; then
    echo "[INFO] Updating existing clone at $CLONE_DIR"
    git -C "$CLONE_DIR" fetch --all --prune --quiet
    if [ -n "$GIT_BRANCH" ]; then
      git -C "$CLONE_DIR" checkout "$GIT_BRANCH" --quiet 2>/dev/null \
        || git -C "$CLONE_DIR" checkout -b "$GIT_BRANCH" "origin/$GIT_BRANCH" --quiet
      git -C "$CLONE_DIR" pull --ff-only --quiet 2>/dev/null || true
    else
      # Update the current branch
      git -C "$CLONE_DIR" pull --ff-only --quiet 2>/dev/null || true
    fi
  else
    echo "[INFO] Cloning $GIT_URL into $CLONE_DIR"
    mkdir -p "$GIT_CLONE_BASE"
    CLONE_ARGS=(git clone --quiet)
    if [ -n "$GIT_BRANCH" ]; then
      CLONE_ARGS+=(--branch "$GIT_BRANCH")
    fi
    CLONE_ARGS+=("$GIT_URL" "$CLONE_DIR")
    "${CLONE_ARGS[@]}"
  fi

  GIT_CLONED=true
  SOURCE_DIR="$CLONE_DIR"

  # Apply --subdir if specified
  if [ -n "$GIT_SUBDIR" ]; then
    SOURCE_DIR="${CLONE_DIR}/${GIT_SUBDIR}"
  fi
fi

if [ ! -d "$SOURCE_DIR" ]; then
  echo "[ERROR] Source directory not found: $SOURCE_DIR" >&2
  exit 1
fi
SOURCE_DIR="$(realpath "$SOURCE_DIR")"

# === Derive project name from source dir if not given ===
if [ -z "$PROJECT_NAME" ]; then
  if [ "$GIT_CLONED" = "true" ] && [ -n "$GIT_SUBDIR" ]; then
    # Use repo-subdir as the project name
    PROJECT_NAME="${REPO_NAME}_$(echo "$GIT_SUBDIR" | tr '/' '_' | tr '[:upper:]' '[:lower:]')"
  else
    PROJECT_NAME="$(basename "$SOURCE_DIR" | tr '[:upper:]' '[:lower:]' | tr ' .' '_')"
  fi
fi

if [ "$CACHE_ONLY" = "true" ] && [ "$OUTPUT_BASE_EXPLICIT" = "false" ]; then
  OUTPUT_BASE="$CACHE_STAGING_ROOT"
fi

OUTPUT_BASE_REAL="$(realpath -m "$OUTPUT_BASE")"
PROJECTS_ROOT_REAL="$(realpath -m "$PROJECTS_ROOT")"
PUBLISH_TO_CANONICAL=false
if [ "$OUTPUT_BASE_REAL" = "$PROJECTS_ROOT_REAL" ] && [ "$CACHE_ONLY" != "true" ]; then
  PUBLISH_TO_CANONICAL=true
fi

LEGACY_PROJECT_DIR="${REPO_ROOT}/${PROJECT_NAME}"
CANONICAL_PROJECT_DIR="${PROJECTS_ROOT}/${PROJECT_NAME}"
if [ "$PUBLISH_TO_CANONICAL" = "true" ] && [ -d "$LEGACY_PROJECT_DIR" ]; then
  echo "[ERROR] Legacy project directory still exists at $LEGACY_PROJECT_DIR" >&2
  echo "[ERROR] Move it under $PROJECTS_ROOT before publishing new snapshots for $PROJECT_NAME." >&2
  exit 1
fi

# === Environment (cron has minimal PATH) ===
export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
if [ -s "$NVM_DIR/nvm.sh" ]; then . "$NVM_DIR/nvm.sh"; fi
export PATH="$HOME/.local/bin:$PATH"

# === Locate copilot binary ===
COPILOT_BIN="$(command -v copilot 2>/dev/null || true)"
if [ -z "$COPILOT_BIN" ]; then
  echo "[ERROR] copilot binary not found in PATH" >&2
  exit 1
fi

# === Pre-flight checks ===
SCRIPTS_DIR="$SKILL_REPO/.github/skills/wiki-generator/scripts"
SKILL_SCRIPTS="$SCRIPTS_DIR"
SKILL_RESOURCES="$SKILL_REPO/.github/skills/wiki-generator/resources"

if [ ! -d "$SKILL_REPO/.github/skills/wiki-generator" ]; then
  echo "[ERROR] wiki-generator skill not found at $SKILL_REPO" >&2
  exit 1
fi

# === Timestamps & paths ===
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUTPUT_DIR="${OUTPUT_BASE}/${PROJECT_NAME}/${TIMESTAMP}"
LOG_FILE="${LOG_DIR}/wiki_gen_${PROJECT_NAME}_${TIMESTAMP}.log"

# === Phase 1 cache check ===
# Look for the most recent output that has a _research/_manifest.json
CACHE_DIR=""
CACHE_STATUS="MISS"

find_latest_cache() {
  local best_dir=""
  local best_ts=""
  local proj_dir=""
  local dir=""
  local ts=""
  for base in "$CACHE_STAGING_ROOT" "$PROJECTS_ROOT"; do
    proj_dir="${base}/${PROJECT_NAME}"
    [ -d "$proj_dir" ] || continue
    for dir in "$proj_dir"/[0-9]*_[0-9]*; do
      [ -d "$dir" ] || continue
      if [ ! -f "$dir/docs/_research/01-survey.md" ] \
         && [ ! -f "$dir/docs/_research/_manifest.json" ] \
         && [ ! -f "$dir/_research/_manifest.json" ] \
         && [ ! -f "$dir/docs/_research/_synthesis.md" ]; then
        continue
      fi
      ts="$(basename "$dir")"
      if [ -z "$best_dir" ] || [[ "$ts" > "$best_ts" ]]; then
        best_dir="$dir"
        best_ts="$ts"
      fi
    done
  done
  [ -n "$best_dir" ] || return 1
  if [ -f "$best_dir/docs/_research/01-survey.md" ] && [ -f "$best_dir/docs/_research/_synthesis.md" ]; then
    echo "$best_dir/docs"
    return 0
  fi
  if [ -f "$best_dir/docs/_research/_manifest.json" ]; then
    echo "$best_dir/docs"
    return 0
  fi
  if [ -f "$best_dir/_research/_manifest.json" ]; then
    echo "$best_dir"
    return 0
  fi
  return 1
}

if [ "$NO_CACHE" = "false" ]; then
  CACHE_DIR="$(find_latest_cache || true)"
  if [ -n "$CACHE_DIR" ]; then
    CACHE_STATUS="$(bash "$SCRIPTS_DIR/check-cache.sh" "$SOURCE_DIR" "$CACHE_DIR" 2>/dev/null | head -1 || echo "MISS")"
  fi
fi

CACHE_HIT=false
case "$CACHE_STATUS" in
  HIT*) CACHE_HIT=true ;;
esac

# === Build the prompt ===
PROMPT="Use the wiki-generator skill to generate a complete HTML wiki for the source code at ${SOURCE_DIR}. Save all generated HTML files to ${OUTPUT_DIR}."

# Add 3-pass research instructions
PROMPT="${PROMPT} Follow the 3-pass research approach: Phase 1A (broad survey), Phase 1B (per-module deep WHY analysis), and Phase 1C (cross-module synthesis). Save all research artifacts to ${OUTPUT_DIR}/docs/_research/ with filenames: 01-survey.md, <module>_deep.md for each module, and _synthesis.md."

if [ "$CACHE_HIT" = "true" ]; then
  PROMPT="${PROMPT} Phase 1 research cache is FRESH at ${CACHE_DIR}/_research/. Copy the _research/ directory to the new output, then skip Phase 1 and start from Phase 1.5."
elif [ "$NO_CACHE" = "true" ]; then
  PROMPT="${PROMPT} Force a full Phase 1 re-research (ignore any cached data)."
fi

if [ "$CACHE_ONLY" = "true" ]; then
  PROMPT="Use the wiki-generator skill Phase 1 ONLY (all 3 passes: 1A broad survey, 1B per-module deep analysis, 1C cross-module synthesis): research the source code at ${SOURCE_DIR}, save research cache to ${OUTPUT_DIR}/docs/_research/, then STOP. Do not generate any HTML pages."
fi

# === Dry-run output ===
if [ "$DRY_RUN" = "true" ]; then
  echo "=== Wiki Generation Plan ==="
  echo "Source:       $SOURCE_DIR"
  echo "Output:       $OUTPUT_DIR"
  echo "Project:      $PROJECT_NAME"
  echo "Model:        $MODEL"
  echo "Max continues:$MAX_CONTINUES"
  echo "Cache status: $CACHE_STATUS"
  echo "Cache dir:    ${CACHE_DIR:-none}"
  echo "Cache hit:    $CACHE_HIT"
  echo "No-cache:     $NO_CACHE"
  echo "Cache-only:   $CACHE_ONLY"
  echo "Publish mode: $PUBLISH_TO_CANONICAL"
  if [ "$GIT_CLONED" = "true" ]; then
  echo "Git URL:      $GIT_URL"
  echo "Git branch:   ${GIT_BRANCH:-<default>}"
  echo "Git subdir:   ${GIT_SUBDIR:-<root>}"
  echo "Clone dir:    $CLONE_DIR"
  fi
  echo "Copilot:      $COPILOT_BIN"
  echo "Skill repo:   $SKILL_REPO"
  echo "Log file:     $LOG_FILE"
  echo ""
  echo "Prompt:"
  echo "  $PROMPT"
  exit 0
fi

# === Setup output and log directories ===
mkdir -p "$OUTPUT_DIR/docs" "$LOG_DIR"

# === Copy cached research if cache hit ===
if [ "$CACHE_HIT" = "true" ] && [ -d "$CACHE_DIR/_research" ]; then
  mkdir -p "$OUTPUT_DIR/docs/_research"
  cp -a "$CACHE_DIR/_research/." "$OUTPUT_DIR/docs/_research/"
  echo "[$(date -Iseconds)] Copied cached research from $CACHE_DIR/_research/" >> "$LOG_FILE"
fi

# === Log header ===
{
  echo "[$(date -Iseconds)] Wiki generation started"
  echo "  Source:      $SOURCE_DIR"
  echo "  Output:      $OUTPUT_DIR"
  echo "  Project:     $PROJECT_NAME"
  echo "  Model:       $MODEL"
  echo "  Cache:       $CACHE_STATUS"
  echo "  Cache dir:   ${CACHE_DIR:-none}"
  echo "  No-cache:    $NO_CACHE"
  echo "  Cache-only:  $CACHE_ONLY"
  echo "  Publish:     $PUBLISH_TO_CANONICAL"
  if [ "$GIT_CLONED" = "true" ]; then
  echo "  Git URL:     $GIT_URL"
  echo "  Git branch:  ${GIT_BRANCH:-<default>}"
  echo "  Git subdir:  ${GIT_SUBDIR:-<root>}"
  echo "  Clone dir:   $CLONE_DIR"
  fi
  echo "  Copilot:     $COPILOT_BIN"
  echo "  Prompt:      $PROMPT"
  echo "---"
} >> "$LOG_FILE"

# === Run Copilot ===
cd "$SKILL_REPO"

set +e
"$COPILOT_BIN" -p \
  "$PROMPT" \
  --allow-all \
  --autopilot \
  --max-autopilot-continues "$MAX_CONTINUES" \
  --model "$MODEL" \
  >> "$LOG_FILE" 2>&1
EXIT_CODE=$?
set -e

{
  echo "---"
  echo "[$(date -Iseconds)] Wiki generation finished (exit code: $EXIT_CODE)"
} >> "$LOG_FILE"

# === Log rotation ===
find "$LOG_DIR" -name "wiki_gen_*.log" -mtime +"$LOG_RETENTION_DAYS" -delete 2>/dev/null || true

# === Prune old wiki snapshots ===
if [ "$PUBLISH_TO_CANONICAL" = "true" ] && [ "$KEEP_SNAPSHOTS" -gt 0 ]; then
  _proj_dir="${OUTPUT_BASE}/${PROJECT_NAME}"
  if [ -d "$_proj_dir" ]; then
    ls -dt "$_proj_dir"/[0-9]*_[0-9]* 2>/dev/null \
      | tail -n +"$((KEEP_SNAPSHOTS + 1))" \
      | xargs rm -rf 2>/dev/null || true
  fi
fi

# === Summary ===
if [ $EXIT_CODE -eq 0 ]; then
  PAGE_COUNT=$(find "$OUTPUT_DIR" -name '*.html' 2>/dev/null | wc -l)
  echo "[OK] Wiki generated: $OUTPUT_DIR ($PAGE_COUNT pages)"

  # --- Overview Pass (Gate D) ---
  if [[ -f "$OUTPUT_DIR/docs/_research/_worklist.yaml" ]]; then
    echo "[overview] Running Overview Pass…"
    python3 "$SKILL_SCRIPTS/yaml_to_worklist_json.py" \
      "$OUTPUT_DIR/docs/_research/_worklist.yaml" > "$OUTPUT_DIR/_worklist.json"
    python3 "$SKILL_SCRIPTS/overview_pass.py" \
      --wiki-root "$OUTPUT_DIR" \
      --worklist-json "$OUTPUT_DIR/_worklist.json" \
      --project-name "$PROJECT_NAME" \
      --project-tagline "${PROJECT_TAGLINE:-}" \
      --prompt-template "$SKILL_RESOURCES/overview_pass.md" \
      --html-template "$SKILL_RESOURCES/overview-template.html"
    rm -f "$OUTPUT_DIR/_worklist.json"
    bash "$SKILL_SCRIPTS/verify.sh" --stage=D --project="$OUTPUT_DIR" \
      || { echo "Gate D failed"; exit 1; }
    python3 "$SKILL_SCRIPTS/inject_overview_link.py" "$OUTPUT_DIR"
  else
    echo "[overview] No _worklist.yaml — skipping Overview Pass (project not eligible)"
  fi
  # --- end Overview Pass ---

  # === Post-generation: update versions, switcher, and hub index ===
  GEN_VERSIONS="${REPO_ROOT}/generate_versions.py"
  INJ_SWITCHER="${REPO_ROOT}/inject_version_switcher.py"
  UPDATE_INDEX="${REPO_ROOT}/update_index.py"
  if [ "$PUBLISH_TO_CANONICAL" != "true" ]; then
    echo "[INFO] Skipping repo-root versions/switcher/index updates for non-canonical output." 
  elif [ -f "$GEN_VERSIONS" ]; then
    echo "[INFO] Regenerating versions.json for $PROJECT_NAME ..."
    python3 "$GEN_VERSIONS" "$PROJECT_NAME" 2>&1 | sed 's/^/  /'
  fi
  if [ "$PUBLISH_TO_CANONICAL" = "true" ] && [ -f "$INJ_SWITCHER" ]; then
    echo "[INFO] Injecting version switcher for $PROJECT_NAME ..."
    python3 "$INJ_SWITCHER" "$PROJECT_NAME" 2>&1 | sed 's/^/  /'
  fi
  if [ "$PUBLISH_TO_CANONICAL" = "true" ] && [ -f "$UPDATE_INDEX" ]; then
    echo "[INFO] Updating hub index.html for $PROJECT_NAME ..."
    python3 "$UPDATE_INDEX" "$PROJECT_NAME" 2>&1 | sed 's/^/  /'
  fi
else
  echo "[FAIL] Wiki generation failed (exit $EXIT_CODE). See $LOG_FILE" >&2
fi

exit $EXIT_CODE

#!/usr/bin/env bash
# fieldlink-sync.sh — Pull atlas mounts from upstream sibling repos.
#
# Reads .fieldlink.json and fetches each declared mount's remote file
# from the corresponding GitHub repo into the local atlas/remote/ tree.
#
# Usage:
#   ./fieldlink-sync.sh          # pull all mounts
#   ./fieldlink-sync.sh --dry    # show what would be fetched
#
# Requires: curl, python3 (for JSON parsing)

set -euo pipefail

DRY_RUN=false
[[ "${1:-}" == "--dry" ]] && DRY_RUN=true

FIELDLINK=".fieldlink.json"

if [[ ! -f "$FIELDLINK" ]]; then
    echo "Error: $FIELDLINK not found. Run from repo root." >&2
    exit 1
fi

# Extract mount entries: (repo_url, ref, remote_path, local_path)
MOUNTS=$(python3 -c "
import json, sys
with open('$FIELDLINK') as f:
    data = json.load(f)
for src in data['fieldlink']['sources']:
    repo = src['repo']
    ref = src.get('ref', 'main')
    for mount in src.get('mounts', []):
        remote = mount['remote']
        local = mount['as']
        print(f'{repo}\t{ref}\t{remote}\t{local}')
")

if [[ -z "$MOUNTS" ]]; then
    echo "No mounts declared in $FIELDLINK."
    exit 0
fi

TOTAL=0
OK=0
FAIL=0

while IFS=$'\t' read -r repo ref remote local; do
    TOTAL=$((TOTAL + 1))

    # Convert GitHub repo URL to raw content URL
    # https://github.com/JinnZ2/Repo -> https://raw.githubusercontent.com/JinnZ2/Repo/main/path
    RAW_URL="${repo/github.com/raw.githubusercontent.com}/${ref}/${remote}"

    if $DRY_RUN; then
        echo "[DRY] $RAW_URL -> $local"
        continue
    fi

    # Ensure target directory exists
    mkdir -p "$(dirname "$local")"

    # Fetch with retry
    FETCHED=false
    for attempt in 1 2 3; do
        if curl -sfL --max-time 10 -o "$local" "$RAW_URL" 2>/dev/null; then
            FETCHED=true
            break
        fi
        sleep $((attempt * 2))
    done

    if $FETCHED; then
        echo "  OK: $local (from ${repo##*/})"
        OK=$((OK + 1))
    else
        echo "  FAIL: $local ($RAW_URL)" >&2
        FAIL=$((FAIL + 1))
    fi
done <<< "$MOUNTS"

if $DRY_RUN; then
    echo "$TOTAL mounts would be fetched."
else
    echo ""
    echo "Sync complete: $OK/$TOTAL succeeded, $FAIL failed."
fi

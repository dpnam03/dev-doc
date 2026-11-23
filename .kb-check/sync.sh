#!/usr/bin/env bash
# Refresh the vendored KB check from a BS-Knowledge-Base checkout.
# Usage: .kb-check/sync.sh [path-to-BS-Knowledge-Base]   (default: ../BS-Knowledge-Base)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KB="${1:-$HERE/../../BS-Knowledge-Base}"
[ -d "$KB/.kb-ci" ] || { echo "not a KB checkout: $KB" >&2; exit 1; }

for f in kb-check.py pr-check.py readable-check.py readable-banned.txt config.json; do
  cp "$KB/.kb-ci/$f" "$HERE/$f"
done

# Foundation 0 is the rule source: keep only the newest version.
rm -f "$HERE"/foundation/Foundation_s0_how-this-kb-works_v*.md
cp "$(ls "$KB/0. Department Foundation"/Foundation_s0_how-this-kb-works_v*.md | sort -V | tail -1)" "$HERE/foundation/"
cp "$KB/2. Reference Library/Shared/Ref_Shared_doc-template_v1.1.md" "$HERE/" 2>/dev/null || true

echo "synced from $KB @ $(git -C "$KB" log -1 --format=%h) · $(ls "$HERE/foundation")"

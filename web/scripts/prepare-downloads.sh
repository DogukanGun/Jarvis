#!/usr/bin/env bash
# Build the Jarvis desktop installer for the target platform and copy the
# output into web/public/downloads/ so Next.js serves them directly.
#
# Usage (run from repo root or web/ directory):
#   ./web/scripts/prepare-downloads.sh           # auto-detect platform
#   ./web/scripts/prepare-downloads.sh --mac
#   ./web/scripts/prepare-downloads.sh --mac-universal
#   ./web/scripts/prepare-downloads.sh --win
#   ./web/scripts/prepare-downloads.sh --linux
#   ./web/scripts/prepare-downloads.sh --all     # CI / all platforms
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DIST="$ROOT/desktop/dist"
OUT="$SCRIPT_DIR/../public/downloads"

mkdir -p "$OUT"

echo "▶ Building desktop app…"
"$ROOT/build-desktop.sh" "${1:-}"

echo ""
echo "▶ Copying artifacts to web/public/downloads/…"
COPIED=0
for f in \
  "$DIST"/*.dmg \
  "$DIST"/*.exe \
  "$DIST"/*.AppImage \
  "$DIST"/*.deb \
  "$DIST"/*.zip \
  "$DIST"/*.tar.gz; do
  if [ -f "$f" ]; then
    cp -f "$f" "$OUT/"
    echo "  ✓ $(basename "$f")"
    COPIED=$((COPIED + 1))
  fi
done

if [ "$COPIED" -eq 0 ]; then
  echo "  ⚠  No installer artifacts found in $DIST"
  exit 1
fi

echo ""
echo "Done. $COPIED file(s) ready in web/public/downloads/:"
ls -lh "$OUT/"

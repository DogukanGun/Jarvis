#!/usr/bin/env bash
# Build Jarvis desktop installer for the target platform.
#
# Usage:
#   ./build-desktop.sh                  # auto-detect current platform
#   ./build-desktop.sh --mac            # macOS arm64 .dmg
#   ./build-desktop.sh --mac-universal  # macOS universal .dmg (arm64 + x64)
#   ./build-desktop.sh --win            # Windows NSIS .exe
#   ./build-desktop.sh --linux          # Linux .AppImage + .deb
#   ./build-desktop.sh --all            # all platforms (CI only)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP="$ROOT/desktop"

ensure_assets() {
  mkdir -p "$DESKTOP/build"
  if [ ! -f "$DESKTOP/build/icon.png" ]; then
    cp "$DESKTOP/resources/icon.png" "$DESKTOP/build/icon.png"
  fi
}

TARGET="${1:-}"
if [ -z "$TARGET" ]; then
  case "$(uname -s)" in
    Darwin)             TARGET="--mac" ;;
    Linux)              TARGET="--linux" ;;
    MINGW*|MSYS*|CYGWIN*) TARGET="--win" ;;
    *) echo "Unknown platform: $(uname -s)"; exit 1 ;;
  esac
fi

ensure_assets

case "$TARGET" in
  --mac)           (cd "$DESKTOP" && npm run build:mac) ;;
  --mac-universal) (cd "$DESKTOP" && npm run build:mac:universal) ;;
  --win)           (cd "$DESKTOP" && npm run build:win) ;;
  --linux)         (cd "$DESKTOP" && npm run build:linux) ;;
  --all)           (cd "$DESKTOP" && npm run build:all) ;;
  -h|--help)
    sed -n '2,8p' "$0"
    exit 0
    ;;
  *)
    echo "Unknown target: $TARGET"
    echo "Run with --help for usage."
    exit 1
    ;;
esac

echo ""
echo "Done. Output in desktop/dist/"
ls "$DESKTOP/dist/" 2>/dev/null || true

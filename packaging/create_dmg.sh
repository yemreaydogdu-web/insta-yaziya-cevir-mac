#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DIST_DIR="$ROOT_DIR/dist"
APP_PATH="$DIST_DIR/InstaYaziyaCevir.app"
DMG_ROOT="$DIST_DIR/dmgroot"
DMG_PATH="$DIST_DIR/InstaYaziyaCevir.dmg"

if [[ ! -d "$APP_PATH" ]]; then
  echo "Hata: $APP_PATH bulunamadı. Önce build_macos.sh çalıştırılmalı."
  exit 1
fi

rm -rf "$DMG_ROOT" "$DMG_PATH"
mkdir -p "$DMG_ROOT"
cp -R "$APP_PATH" "$DMG_ROOT/"
ln -s /Applications "$DMG_ROOT/Applications"

hdiutil create \
  -volname "InstaYaziyaCevir" \
  -srcfolder "$DMG_ROOT" \
  -ov \
  -format UDZO \
  "$DMG_PATH"

rm -rf "$DMG_ROOT"

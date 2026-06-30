#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt

rm -rf build dist
pyinstaller --noconfirm --clean ZelkaScribe.spec

# GitHub/macOS'ta karantina attribute kalırsa temizle.
xattr -cr "dist/Zelka Scribe.app" 2>/dev/null || true

bash packaging/create_dmg.sh

echo ""
echo "Bitti:"
echo "  dist/Zelka Scribe.app"
echo "  dist/ZelkaScribe.dmg"

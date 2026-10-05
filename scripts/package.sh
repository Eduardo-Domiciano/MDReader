#!/usr/bin/env bash
# Empacota um único executável para Ubuntu com PyInstaller.
# Depois: briefcase ou fpm podem gerar um .deb a partir de dist/MDReader.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"

if [[ ! -x .venv/bin/python ]]; then
  "$root/scripts/setup.sh"
fi

# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install "pyinstaller>=6.0"

# --onefile gera dist/MDReader; remove a pasta do empacotamento antigo.
rm -rf "$root/dist/MDReader"

pyinstaller \
  --noconfirm \
  --onefile \
  --windowed \
  --name MDReader \
  --add-data "app/icon.png:app" \
  --collect-all PySide6_Essentials \
  --collect-all mmdc \
  --collect-all termaid \
  --collect-all quickjs \
  --collect-all resvg_py \
  app/__main__.py

rm -f "$root/dist/mdreader.png" "$root/dist/mdreader.desktop"

echo
echo "Binário em dist/MDReader"
echo "Para um .deb no futuro: briefcase ou fpm sobre esse arquivo."

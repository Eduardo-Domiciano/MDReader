#!/usr/bin/env bash
# Empacota um executável para Ubuntu com PyInstaller.
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

pyinstaller \
  --noconfirm \
  --windowed \
  --name MDReader \
  --collect-all PySide6_Essentials \
  app/__main__.py

echo
echo "Binário em dist/MDReader/MDReader"
echo "Para um .deb no futuro: briefcase ou fpm sobre essa pasta."

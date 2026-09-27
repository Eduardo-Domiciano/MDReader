#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"

if ! command -v python3 >/dev/null; then
  echo "Instale o Python 3: sudo apt install python3 python3-venv python3-pip"
  exit 1
fi

python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo
echo "Ambiente pronto. Para abrir o app:"
echo "  source .venv/bin/activate"
echo "  python -m app"

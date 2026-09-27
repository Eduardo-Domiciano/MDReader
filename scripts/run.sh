#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"

if [[ ! -x .venv/bin/python ]]; then
  echo "Ambiente ainda não criado. Rodando scripts/setup.sh…"
  "$root/scripts/setup.sh"
fi

exec .venv/bin/python -m app

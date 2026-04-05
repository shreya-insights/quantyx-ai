#!/usr/bin/env bash
# Run API from the real backend root (avoids ModuleNotFoundError: app when cwd is backend/backend).
# Uses backend/.venv when present so reload workers do not pick up system Python / missing deps.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
PY="${ROOT}/.venv/bin/python"
if [[ -x "$PY" ]]; then
  exec "$PY" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
fi
exec python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

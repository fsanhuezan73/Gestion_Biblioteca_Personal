#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 no está instalado. Instálalo antes de arrancar la demo."
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "Node.js y npm no están instalados. Instálalos antes de arrancar la demo."
  exit 1
fi

cd "$ROOT_DIR/backend"
if [ ! -d venv ]; then
  python3 -m venv venv
fi
source venv/bin/activate
python -m pip install --upgrade pip >/dev/null 2>&1 || true
python -m pip install -r requirements.txt >/dev/null

uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

cd "$ROOT_DIR/frontend"
if [ ! -d node_modules ]; then
  npm install
fi
npm run dev -- --host 0.0.0.0 --port 5173 &
FRONTEND_PID=$!

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true" EXIT

cat <<EOF

Demo lista para usar:
- Backend: http://localhost:8000/docs
- Frontend: http://localhost:5173

Presiona Ctrl+C para detener la demo.
EOF

wait

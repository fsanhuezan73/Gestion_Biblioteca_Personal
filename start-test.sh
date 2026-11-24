#!/usr/bin/env bash
# Prueba local contra BIBLIOTECA_TEST (nunca producción).
# Backend en 8001 y frontend en 5174, para no chocar con `npm run dev` (5173).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8001}"
FRONTEND_PORT="${FRONTEND_PORT:-5174}"

cd "$ROOT_DIR/backend"
source venv/bin/activate
python scripts/run_local_test.py --port "$BACKEND_PORT" &
BACKEND_PID=$!

cd "$ROOT_DIR/frontend"
VITE_API_URL="http://localhost:$BACKEND_PORT/api/v1" npx vite --port "$FRONTEND_PORT" --strictPort &
FRONTEND_PID=$!

trap 'kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true' EXIT

cat <<EOF

Ambiente de PRUEBAS (BIBLIOTECA_TEST):
- Frontend: http://localhost:$FRONTEND_PORT
- Backend:  http://localhost:$BACKEND_PORT/docs

Presiona Ctrl+C para detenerlo.
EOF

wait

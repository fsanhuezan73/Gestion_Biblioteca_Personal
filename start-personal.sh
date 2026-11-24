#!/usr/bin/env bash
# Prueba local contra BIBLIOTECA_PERSONAL (PRODUCCIÓN): tus datos reales.
# Backend en 8002 y frontend en 5175, para no confundirlo con start-test.sh
# (8001/5174) ni con `npm run dev` (5173).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8002}"
FRONTEND_PORT="${FRONTEND_PORT:-5175}"

cat <<EOF
ATENCIÓN: este ambiente local usa la base de PRODUCCIÓN (BIBLIOTECA_PERSONAL).
Todo lo que hagas (agregar libros, valorar, generar recomendaciones) cambia
tus datos reales y cuenta para el límite diario de recomendaciones.
EOF
read -r -p "Escribe PERSONAL para continuar: " answer
if [ "$answer" != "PERSONAL" ]; then
  echo "Cancelado."
  exit 1
fi

cd "$ROOT_DIR/backend"
source venv/bin/activate
python scripts/run_local_test.py --schema personal --confirm-production --port "$BACKEND_PORT" &
BACKEND_PID=$!

cd "$ROOT_DIR/frontend"
VITE_API_URL="http://localhost:$BACKEND_PORT/api/v1" npx vite --port "$FRONTEND_PORT" --strictPort &
FRONTEND_PID=$!

trap 'kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true' EXIT

cat <<EOF

Ambiente local con datos de PRODUCCIÓN (BIBLIOTECA_PERSONAL):
- Frontend: http://localhost:$FRONTEND_PORT
- Backend:  http://localhost:$BACKEND_PORT/docs

Presiona Ctrl+C para detenerlo.
EOF

wait

#!/bin/bash
set -e

echo ""
echo "=========================================="
echo "  Configurando Biblioteca Personal Dev"
echo "=========================================="
echo ""

# ── 1. Backend: entorno virtual e instalación de dependencias ──────────────
echo ">>> [1/4] Instalando dependencias Python (backend)..."
cd /workspaces/Gestion_Biblioteca_Personal/backend
python -m venv venv
source venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo "    ✓ Dependencias Python instaladas"

# ── 2. Frontend: instalación de dependencias npm ───────────────────────────
echo ">>> [2/4] Instalando dependencias Node.js (frontend)..."
cd /workspaces/Gestion_Biblioteca_Personal/frontend
npm install --silent
echo "    ✓ Dependencias Node.js instaladas"

# ── 3. Crear backend/.env desde Codespace Secrets ─────────────────────────
echo ">>> [3/4] Configurando archivo .env del backend..."
ENV_FILE="/workspaces/Gestion_Biblioteca_Personal/backend/.env"

if [ ! -f "$ENV_FILE" ]; then
  cat > "$ENV_FILE" << EOF
# Oracle Autonomous Database
ORACLE_USER=${ORACLE_USER:-}
ORACLE_PASSWORD=${ORACLE_PASSWORD:-}
ORACLE_DSN=${ORACLE_DSN:-}
ORACLE_WALLET_DIR=/workspaces/Gestion_Biblioteca_Personal/wallet
ORACLE_WALLET_PASSWORD=${ORACLE_WALLET_PASSWORD:-}

# JWT
JWT_SECRET_KEY=${JWT_SECRET_KEY:-cambia-esto-por-un-secreto-largo}
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# App
APP_ENV=development
EOF
  echo "    ✓ Archivo .env creado"
else
  echo "    ✓ Archivo .env ya existe, no se sobreescribe"
fi

# ── 4. Descomprimir Oracle Wallet desde Codespace Secret ─────────────────
echo ">>> [4/4] Configurando Oracle Wallet..."
WALLET_DIR="/workspaces/Gestion_Biblioteca_Personal/wallet"

if [ -n "${ORACLE_WALLET_B64:-}" ]; then
  mkdir -p "$WALLET_DIR"
  echo "$ORACLE_WALLET_B64" | base64 -d > /tmp/wallet.zip
  unzip -o -j /tmp/wallet.zip -d "$WALLET_DIR"   # -j: sin subdirectorios
  rm /tmp/wallet.zip
  # Corregir ruta en sqlnet.ora (el wallet trae la ruta de la máquina original)
  cat > "$WALLET_DIR/sqlnet.ora" << 'SQLNET'
WALLET_LOCATION = (SOURCE = (METHOD = file) (METHOD_DATA = (DIRECTORY="/workspaces/Gestion_Biblioteca_Personal/wallet")))
SSL_SERVER_DN_MATCH=yes
SQLNET
  echo "    ✓ Wallet descomprimido y sqlnet.ora corregido en $WALLET_DIR"
else
  echo "    ⚠ Secret ORACLE_WALLET_B64 no encontrado."
  echo "      Sigue los pasos de la guía para agregar el wallet."
  mkdir -p "$WALLET_DIR"
fi

echo ""
echo "=========================================="
echo "  ✅ Entorno configurado exitosamente"
echo ""
echo "  Para iniciar la aplicación:"
echo ""
echo "  1. Backend:"
echo "     cd backend && source venv/bin/activate"
echo "     uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "  2. Frontend (en otra terminal):"
echo "     cd frontend && npm run dev"
echo "=========================================="
echo ""

# Gestión Biblioteca Personal

Sistema web para gestionar la colección personal de libros con autenticación JWT, catálogo, edición y estado de lectura.

**Stack**: Vue 3 + Bootstrap 5 (frontend) · FastAPI + Python (backend) · Oracle Autonomous Database 26ai

---

## Estado de la demo

La aplicación está preparada para demostración local con:

- Frontend en `http://localhost:5173`
- Backend en `http://localhost:8000`
- Swagger/OpenAPI en `http://localhost:8000/docs`

---

## Requisitos previos

- Python 3.10+
- Node.js 18+
- npm
- Oracle Autonomous Database configurado o un servicio Oracle accesible
- Wallet de Oracle si se conecta a Autonomous Database

---

## Arranque rápido para demo

### Opción 1: script de arranque

```bash
cd Gestion_Biblioteca_Personal
chmod +x start-demo.sh
./start-demo.sh
```

Esto levantará automáticamente:

- backend en puerto `8000`
- frontend en puerto `5173`

### Opción 2: arranque manual

#### 1) Preparar variables de entorno

```bash
cd Gestion_Biblioteca_Personal
cp backend/.env.example backend/.env
```

Edita `backend/.env` con tus credenciales reales de Oracle y el secreto JWT.

Ejemplo:

```env
ORACLE_USER=ADMIN
ORACLE_PASSWORD=TuPassword123
ORACLE_DSN=tu_servicio_high
ORACLE_WALLET_DIR=/ruta/al/wallet
ORACLE_WALLET_PASSWORD=tu_wallet_password
JWT_SECRET_KEY=una_clave_larga_y_segura
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
APP_ENV=development
```

#### 2) Crear tablas en Oracle

Ejecuta el SQL de inicialización:

```sql
@backend/sql/001_create_tables.sql
```

#### 3) Backend

```bash
cd Gestion_Biblioteca_Personal/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend disponible en:

- `http://localhost:8000`
- `http://localhost:8000/docs`

#### 4) Frontend

```bash
cd Gestion_Biblioteca_Personal/frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

Frontend disponible en:

- `http://localhost:5173`

---

## Estructura del proyecto

```text
Gestion_Biblioteca_Personal/
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── endpoints/
│   │   │   └── router.py
│   │   ├── core/
│   │   ├── db/
│   │   ├── schemas/
│   │   └── main.py
│   ├── sql/
│   ├── .env.example
│   ├── requirements.txt
│   ├── pytest.ini
│   └── tests/
├── frontend/
│   ├── src/
│   ├── package.json
│   ├── vite.config.js
│   └── index.html
├── README.md
├── start-demo.sh
├── Wallet/
└── Plan de pruebas/
```

---

## Endpoints principales

| Método | Ruta | Descripción | Auth |
| -------- | ------ | ------------- | ------ |
| `POST` | `/api/v1/auth/register` | Registro de usuario | No |
| `POST` | `/api/v1/auth/login` | Login y emisión de JWT | No |
| `GET` | `/api/v1/books/` | Listar libros del usuario | ✅ |
| `POST` | `/api/v1/books/` | Crear libro | ✅ |
| `GET` | `/api/v1/books/{id}` | Detalle de libro | ✅ |
| `PUT` | `/api/v1/books/{id}` | Editar libro | ✅ |
| `DELETE` | `/api/v1/books/{id}` | Eliminar libro | ✅ |
| `GET` | `/health` | Health check del backend | No |

---

## Validación recomendada antes de la demo

```bash
cd backend
source venv/bin/activate
pytest -q
```

O para validación más específica:

```bash
cd backend
source venv/bin/activate
pytest tests/integration -q
```

Frontend:

```bash
cd frontend
npm run build
```

---

## Notas operativas

- La API usa CORS para permitir peticiones desde `http://localhost:5173`.
- El flujo de autenticación usa JWT con token en header `Authorization: Bearer ...`.
- La base de datos Oracle se gestiona a través del pool de conexiones configurado en `backend/app/db/session.py`.
- Si se usa Oracle Autonomous Database, el wallet debe estar disponible y referenciado en `ORACLE_WALLET_DIR`.

---

## Demo checklist

- [x] Backend operativo
- [x] Frontend operativo
- [x] Autenticación funcionando
- [x] CRUD de libros funcionando
- [x] Portadas visibles completas en UX
- [x] Build de frontend validada
- [x] Documentación de arranque actualizada

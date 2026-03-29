# Gestión Biblioteca Personal

Sistema web para gestionar tu colección de libros personal.

**Stack**: Vue 3 + Bootstrap 5 (frontend) · FastAPI + Python (backend) · Oracle Autonomous Database 26ai

---

## Estructura del Proyecto

```
Gestion_Biblioteca_Personal/
├── backend/        ← API REST (FastAPI + Python)
│   ├── app/
│   │   ├── main.py                # Entrada de la app
│   │   ├── api/v1/endpoints/      # auth.py, books.py
│   │   ├── core/                  # config.py, security.py
│   │   ├── db/session.py          # Pool conexiones Oracle
│   │   └── schemas/               # Pydantic models
│   ├── sql/001_create_tables.sql  # Script de BD
│   ├── requirements.txt
│   └── .env.example
└── frontend/       ← SPA (Vue 3 + Vite)
    ├── src/
    │   ├── views/       # Pantallas de la app
    │   ├── components/  # Componentes reutilizables
    │   ├── stores/      # Pinia: auth.js, books.js
    │   ├── router/      # Vue Router + guards
    │   └── utils/api.js # Axios + interceptor JWT
    └── package.json
```

---

## Configuración inicial

### 1. Clonar y configurar variables de entorno

```bash
git clone <url-del-repo>
cd Gestion_Biblioteca_Personal
cp backend/.env.example backend/.env
# Editar backend/.env con tus credenciales de Oracle y un JWT secret
```

### 2. Crear tablas en Oracle

Conectar a Oracle SQL Developer Web (o SQLcl) y ejecutar:
```sql
@backend/sql/001_create_tables.sql
```

### 3. Instalar dependencias del backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate          # macOS/Linux
# venv\Scripts\activate           # Windows
pip install -r requirements.txt
```

### 4. Arrancar el servidor backend

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
# API disponible en http://localhost:8000
# Docs interactivos: http://localhost:8000/docs
```

### 5. Instalar dependencias del frontend

```bash
cd frontend
npm install
```

### 6. Arrancar el servidor frontend

```bash
cd frontend
npm run dev
# App disponible en http://localhost:5173
```

---

## Variables de entorno (backend/.env)

| Variable | Descripción |
|----------|-------------|
| `ORACLE_USER` | Usuario de la BD Oracle |
| `ORACLE_PASSWORD` | Contraseña de la BD |
| `ORACLE_DSN` | Service name (ej: `nombre_high`) |
| `ORACLE_WALLET_DIR` | Ruta al directorio del wallet extraído |
| `ORACLE_WALLET_PASSWORD` | Contraseña del wallet |
| `JWT_SECRET_KEY` | Clave secreta para firmar JWT (larga y aleatoria) |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Duración del token (default: 30) |

---

## Endpoints de la API

| Método | Ruta | Descripción | Auth |
|--------|------|-------------|------|
| `POST` | `/api/v1/auth/register` | Registrar nuevo usuario | No |
| `POST` | `/api/v1/auth/login` | Login → retorna JWT | No |
| `GET` | `/api/v1/books/` | Listar libros del usuario | ✅ JWT |
| `POST` | `/api/v1/books/` | Añadir libro | ✅ JWT |
| `GET` | `/api/v1/books/{id}` | Detalle de un libro | ✅ JWT |
| `PUT` | `/api/v1/books/{id}` | Editar libro | ✅ JWT |
| `DELETE` | `/api/v1/books/{id}` | Eliminar libro (soft delete) | ✅ JWT |
| `GET` | `/health` | Health check | No |

Documentación interactiva completa: `http://localhost:8000/docs`

---

## Backlog / Sprints

| Sprint | Historias de Usuario |
|--------|---------------------|
| **Sprint 1** ✅ | Setup + HU-07 (Sign Up) + HU-08 (Login JWT) |
| **Sprint 2** ✅ | HU-01 (Añadir libro) + HU-02 (Ver lista) + HU-03 (Editar) + HU-04 (Eliminar) |
| **Sprint 3** 🔜 | HU-05 (Búsqueda) + HU-06 (Estado de lectura) |
| **Sprint 4** 🔜 | HU-09 (Autocompletado ISBN vía Google Books API) |

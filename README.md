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
@backend/sql/002_migrate_3nf.sql
@backend/sql/003_add_cover_url.sql
@backend/sql/004_add_reading_status.sql
@backend/sql/005_add_personal_reviews.sql
@backend/sql/006_add_password_recovery.sql
@backend/sql/007_add_reading_stats.sql
```

Para instalaciones existentes con 001–005 aplicadas, ejecutar **solo** la
migración `006_add_password_recovery.sql`, primero en un esquema de pruebas y
después en el esquema real con respaldo y aprobación. No se aplica al iniciar
la aplicación. Oracle confirma DDL implícitamente, por lo que `ROLLBACK` no
deshace la migración. El backend de autenticación nuevo requiere esta migración
antes de desplegarse.

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
| `GET` | `/api/v1/books/check-isbn?isbn=` | ¿Ya tengo este ISBN? (ignora guiones, acepta ISBN-10) | ✅ |
| `GET` | `/api/v1/stats/?year=2026` | Estadísticas del año y de la biblioteca | ✅ |
| `GET/PUT/DELETE` | `/api/v1/goals/{year}` | Meta anual de lectura | ✅ |
| `GET` | `/health` | Health check del backend | No |
| `GET` | `/health/db` | Ejecuta SQL en Oracle (keepalive diario, ver DEPLOY.md) | Header `X-Health-Token` |

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

## Valoraciones y notas personales

Desde la ficha de cada libro puedes guardar una valoración opcional de **1 a 5
estrellas** y notas privadas de hasta **5000 caracteres**, incluyendo reseñas y
citas en texto plano. Selecciona «Sin valorar» o vacía las notas y guarda para
borrarlas. «Descartar cambios» recupera lo guardado. La valoración aparece también
en tarjetas y tabla; las notas se cargan solo con la ficha individual.

La API ofrece `PATCH /api/v1/books/{id}/personal` con `rating` y/o
`personal_notes`. Omitir un campo conserva su valor; enviar `null` lo borra.
Solo el propietario puede leer o modificar estos datos mediante la API.
No hay publicación de reseñas ni edición de HTML.

**Base de datos:** para una instalación existente con 001–004 aplicadas, ejecutar
solo `backend/sql/005_add_personal_reviews.sql`, primero en un esquema Oracle de
pruebas. No repetir las migraciones anteriores. La migración agrega dos columnas
opcionales y una restricción de valores de estrellas, sin cambiar los libros
existentes. No se aplica al iniciar la aplicación. Oracle confirma DDL
implícitamente; un `ROLLBACK` no elimina las columnas creadas.

El worktree aísla el código, no Oracle: usar un esquema de pruebas y puertos
distintos a los del checkout principal. Ver [validación de la funcionalidad](docs/valoraciones-notas.md).

## Correo de recuperación de contraseña (preparación)

El backend permite configurar un servidor SMTP con STARTTLS o SSL implícito.
Completar en `backend/.env` los valores `SMTP_HOST`, `SMTP_PORT`,
`SMTP_SECURITY`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL` y
`FRONTEND_BASE_URL` (ver `backend/.env.example`). Usar una cuenta de envío
dedicada y guardar las credenciales solo como secretos del entorno; no
versionarlas. La URL se construye desde `FRONTEND_BASE_URL`, nunca desde el
encabezado `Host` de la petición. En producción se exige HTTPS; HTTP solo se
acepta para `localhost` o `127.0.0.1` en desarrollo.

Ver [validación y pasos pendientes de activación](docs/password-recovery-validation.md).

Mantener `PASSWORD_RESET_ENABLED=false` hasta que la migración 006 esté aplicada,
la vista frontend `/reset-password` exista y se haya probado el envío con el
proveedor elegido. La configuración y las pruebas actuales no envían correos
reales. Cuando se habilite, el endpoint de solicitud siempre responderá con un
mensaje genérico; los errores SMTP se registran sin dirección ni token.

## Estadísticas y metas de lectura

La página **📊 Estadísticas** (`/stats`) muestra la meta anual con su ritmo,
libros y páginas leídos por año, libros por mes, géneros, valoraciones, autores
más leídos y libros en curso. Cada libro guarda fecha de inicio, fecha de
término y número de páginas (autocompletado por ISBN desde Open Library).

Fechas automáticas al cambiar el estado (siempre editables): «Leyendo» fija el
inicio en hoy si falta y borra el término; «Leído» fija el término en hoy si
falta, sin inventar el inicio; «Quiero leer» borra ambas. Los libros leídos sin
fecha de término cuentan en los totales, pero no en el año ni en la meta.

**Base de datos:** para una instalación con 001–006 aplicadas, ejecutar solo
`backend/sql/007_add_reading_stats.sql`, primero en un esquema de pruebas. La
migración es aditiva (columnas opcionales y tabla nueva): el backend anterior
sigue funcionando, por lo que debe aplicarse **antes** de desplegar este código.
Ver [validación de la funcionalidad](docs/estadisticas-metas.md).

## Escanear el código de barras

En **Añadir libro** (o con **📷 Escanear** en la barra de la biblioteca) se abre
la cámara trasera; al leer el EAN-13 del libro (978/979) se completa el ISBN,
se buscan los datos en Open Library y se avisa si el libro ya está en tu
biblioteca. Incluye cambio de cámara, linterna (si el equipo la soporta) y
lectura desde una foto. Las imágenes se procesan solo en el navegador.

- Lector: `BarcodeDetector` nativo si soporta EAN-13; si no (Safari/iPhone,
  Firefox), ZXing en WebAssembly (`barcode-detector` + `zxing-wasm`), servido
  desde la propia app y cargado solo al abrir el escáner.
- La cámara exige HTTPS (o `localhost`). Para probar desde un celular en la
  misma red: `npm run dev:mobile` (certificado local; aceptar la advertencia
  del navegador) y abrir la dirección «Network» que muestra Vite. La API se
  consulta por el proxy `/api` (`VITE_PROXY_TARGET`, por defecto el backend en
  `127.0.0.1:8000`).
- Pruebas E2E: `tests/e2e/barcode-scanner.spec.js` usa una cámara falsa de
  Chrome que muestra un código EAN-13 generado en la prueba (modo nativo y
  WebAssembly).

# Resumen para continuar el desarrollo (sesión Claude Code, 22-nov-2026)

## 1. Proyecto

- **App:** sistema web de gestión de biblioteca personal.
- **Producción:** https://biblioteca-personal.site (frontend, Vercel) · API https://biblioteca-personal-api.onrender.com (Render, plan free, despliegue automático desde `main`).
- **Repo:** https://github.com/fsanhuezan73/Gestion_Biblioteca_Personal (público). Ramas: `main` (producción) y `development` (integración).
- **Stack:** Vue 3 + Pinia + Bootstrap 5 + Vite (frontend) · FastAPI + Python 3 + `oracledb` (backend) · Oracle Autonomous Database Always Free 26ai · correo SMTP con Brevo · Chart.js · `barcode-detector`/`zxing-wasm`.
- **Desarrollo:** antes en VS Code + Copilot; ahora con Claude Code (app de escritorio).

## 2. Flujo de trabajo acordado (respetar)

1. Explicar la propuesta y un plan de trabajo **antes de escribir código** y esperar la aprobación del usuario.
2. Rama `feature/<nombre>` desde `development` → PR a `development` → PR `development` → `main`.
3. **Mergear a `main` solo con instrucción explícita** del usuario («mergea el PR #N»). Un merge a producción no pedido fue bloqueado por el sistema de permisos.
4. Commits con `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; descripciones de PR con `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
5. Validar antes de entregar: `pytest -q` y `ruff check` (backend), `npm run lint`, `npm run test:run` y `npm run build` (frontend), y Playwright E2E.
6. **Secretos:** el asistente nunca debe ver ni escribir claves o tokens. El usuario los copia con `pbcopy`/`pbpaste` y los pega él mismo en Render o GitHub.

## 3. Bases de datos Oracle

| Esquema | Uso | Credenciales locales |
|---|---|---|
| `BIBLIOTECA_PERSONAL` | **Producción** (Render y también el `backend/.env` local) | `backend/.env` |
| `BIBLIOTECA_TEST` | Pruebas de migraciones y validaciones | `backend/.env.test` |

- Ambos archivos están ignorados por Git (`backend/.gitignore`: `.env` y `.env.*`, excepto `.env.example`).
- **Migraciones** en `backend/sql/001…007`, todas aplicadas en ambos esquemas. Proceso: confirmar el esquema → respaldar → aplicar en TEST → validar → respaldar → aplicar en PERSONAL → comparar estructura y datos. Los DDL de Oracle no se deshacen con `ROLLBACK`.
- **Respaldos lógicos** (JSON + DDL + SHA256) en `~/Backups/BibliotecaPersonal/`; el último de producción es `20261122T185804Z-before-007`.
- Al aplicar SQL con scripts, separar las sentencias respetando las comillas: los comentarios de la 007 contienen `;`.
- **Cuidado:** `npm run dev` + backend local trabajan sobre los datos REALES de producción.

## 4. Funcionalidades en producción

**Previas a esta sesión:** registro/login JWT con bcrypt · recuperación de contraseña por correo (Brevo, puerto 2525) · cambio de contraseña con invalidación de JWT · CRUD de libros con borrado lógico · varios autores, géneros y editoriales (3FN) · autocompletado por ISBN · portadas · estado de lectura · búsqueda y filtros · vista cuadrícula/tabla · valoración de 1 a 5 y notas privadas.

**Agregadas en esta sesión (PRs #16–#23, todos mergeados a `main`):**

1. **Keepalive diario de Oracle** (PRs #16 y #17). Oracle detiene la base Always Free tras 7 días sin SQL.
   - `GET /health/db` ejecuta `SELECT 1 FROM DUAL` y exige el header `X-Health-Token`.
   - El workflow `.github/workflows/oracle-keepalive.yml` corre todos los días a las 09:17 UTC; si falla, GitHub avisa por correo.
   - Configuración: secret `HEALTHCHECK_TOKEN` (Render y GitHub) y variable `HEALTHCHECK_URL` (GitHub).
2. **Estadísticas y metas de lectura** (PRs #18 y #19, migración 007).
   - `books.started_at`, `finished_at` y `page_count`, y tabla `reading_goals`.
   - Fechas automáticas al cambiar el estado (Leyendo → inicio hoy; Leído → término hoy; Quiero leer → borra ambas).
   - `GET /stats/?year=`, `GET/PUT/DELETE /goals/{year}` y página `/stats`: meta con ritmo, indicadores, gráficos y lista de libros leídos del año.
   - La biblioteca muestra fechas y días de lectura en cuadrícula y tabla, el chip de meta y un filtro de libros leídos sin fecha.
3. **Escáner de código de barras** (PRs #20 y #21).
   - `BarcodeScanner.vue` lee EAN-13 978/979 con la cámara; incluye linterna, cambio de cámara y subir foto.
   - Usa el lector nativo del navegador o ZXing WebAssembly, cargado solo al abrir el escáner.
   - `GET /books/check-isbn` avisa si el libro ya está en la biblioteca.
   - `npm run dev:mobile` levanta un servidor HTTPS para probar desde el celular.
   - Probado en el celular del usuario: lee bien los códigos.
4. **Búsqueda combinada por ISBN** (PRs #22 y #23).
   - `GET /books/lookup`: Open Library como base, Google Books completa los datos que falten, en paralelo y con caché de 6 h.
   - Secret `GOOGLE_BOOKS_API_KEY`, ya configurado en Render. La copia local está en `backend/.env.googlebooks` (ignorado por Git).
   - Limitación conocida: algunos ISBN chilenos de editoriales pequeñas (`978-956-6196…`) no están en ninguna base pública. No existe una API pública de la agencia ISBN chilena; ISBNdb (pago) es la única alternativa más completa.

## 5. Pendientes y próximos pasos sugeridos

- **Verificación pendiente del usuario:** buscar 978-956-239-958-6 en producción y confirmar el mensaje «Datos de Google Books».
- **Funcionalidad pendiente del top 3:** recomendaciones y resúmenes con IA (Claude API), usando las valoraciones y notas.
- **Deuda técnica:**
  - CI con GitHub Actions: hoy no corren tests en los PRs; solo existe el workflow de keepalive.
  - Consultas libro por libro (N+1) para obtener autores en `GET /books/`.
  - Paginación de la biblioteca.
  - Exportar e importar en CSV (por ejemplo desde Goodreads).
- **Ideas mencionadas:** modo ráfaga del escáner para cargar una estantería completa; relecturas; metas por páginas.
- **Datos:** los libros reales marcados «Leído» antes de la migración 007 no tienen fecha de término; el usuario puede completarlas desde el aviso «Completar fechas».
- **Limpieza opcional:**
  - Ramas remotas ya mergeadas: `feature/valoraciones-notas`, `feature/oracle-keepalive` y otras que siguen listadas localmente por falta de `git fetch --prune`.
  - Cuentas y libros «VALIDACIÓN 007» en `BIBLIOTECA_TEST`.

## 6. Notas técnicas útiles

- **Playwright:** los navegadores propios no están instalados. Usar el Chrome del sistema con una configuración temporal (`use: { channel: 'chrome' }`) y otro puerto si 5173 está ocupado por el `npm run dev` del usuario. La prueba E2E del escáner usa una cámara falsa de Chrome (`tests/e2e/support/fake-barcode-video.js`).
- **ESLint** no tiene globals de navegador ni de Node: usar `globalThis.navigator`, `import process from 'node:process'`, etc.
- **Render free** se suspende tras 15 minutos sin uso; el primer request tarda unos 50 segundos.
- **Documentación por funcionalidad** en `docs/`: `valoraciones-notas.md`, `password-recovery-validation.md`, `estadisticas-metas.md`. Despliegue en `DEPLOY.md`.

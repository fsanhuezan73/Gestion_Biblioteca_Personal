# CLAUDE.md

Guía para Claude Code en este repositorio. Responder al usuario en **español**.

## Proyecto

Sistema web de gestión de una biblioteca personal de libros.

- **Producción:**
  - Frontend: https://biblioteca-personal.site (Vercel).
  - API: https://biblioteca-personal-api.onrender.com (Render, plan free: tras 15 minutos sin uso, el primer request tarda unos 50 s).
  - Ambos se despliegan automáticamente desde `main`.
- **Ramas:** `main` (producción) y `development` (integración).
- **Stack:**
  - `frontend/`: Vue 3, Pinia, Vue Router, Bootstrap 5, Vite, Chart.js (solo en `/stats`) y `barcode-detector` + `zxing-wasm` (escáner, carga diferida).
  - `backend/`: FastAPI, `oracledb`, JWT y bcrypt, `httpx`.
  - Base de datos: Oracle Autonomous Database Always Free.
  - Correo: SMTP de Brevo.
- **Documentación:**
  - Arranque y endpoints: `README.md`.
  - Despliegue y keepalive: `DEPLOY.md`.
  - Validaciones por funcionalidad: `docs/`.
  - Historial de la sesión de nov-2026: `docs/resumen-sesion-claude.md`.

## Flujo de trabajo (obligatorio)

1. Para una funcionalidad nueva o un cambio relevante: **explicar la propuesta y un plan de trabajo, y esperar la aprobación** antes de escribir código. Preguntar las decisiones de diseño con una recomendación.
2. Rama `feature/<nombre>` (o `fix/`, `docs/`) desde `development` → PR a `development` → PR `development` → `main`.
3. **No mergear a `main` (producción) sin una instrucción explícita** del usuario para ese PR, por ejemplo «mergea el PR #N». Mergear a `development` solo cuando lo pida.
4. Antes de abrir un PR, todo en verde:
   - Backend (`cd backend && source venv/bin/activate`): `pytest -q` y `ruff check app tests`.
   - Frontend (`cd frontend`): `npm run lint`, `npm run test:run` y `npm run build`.
   - E2E: `npx playwright test` (ver la nota sobre Playwright más abajo).
5. Después de un merge a `main`: comprobar el despliegue en Render (que el endpoint nuevo aparezca en `/openapi.json`) y en Vercel, y revisar los logs.

## Revisiones de IA de pago (Copilot, Codex)

- El 22 de noviembre de 2026, los PR #16 a #25 dispararon revisiones automáticas de Copilot que agotaron los créditos y parte del presupuesto adicional.
- **Nunca** pedir revisiones a Copilot, Codex u otros bots de IA (revisores, `requested_reviewers`, comentarios `@copilot`/`@codex`) sin aprobación explícita del usuario en el chat para ese PR.
- Estado acordado: revisión automática de Copilot **desactivada** en la cuenta; revisión **automática** de Codex al abrir un PR **autorizada**. Pedir revisiones extra a Codex (`@codex review`) requiere aprobación.
- Abrir un PR puede disparar revisiones automáticas. Después de cada `gh pr create`, comprobar si Copilot u otro bot no autorizado recibió una solicitud; si ocurrió, detenerse y avisar al usuario.
- La regla y los hooks globales están en `~/.claude/CLAUDE.md` y `~/.claude/settings.json`.

## Secretos (nunca verlos ni escribirlos)

- No leer, imprimir ni pegar en comandos o herramientas los valores de claves y tokens.
- El usuario los copia con `pbcopy`/`pbpaste` y los pega él mismo en Render o GitHub. Para guardar un secreto local, usar archivos `backend/.env.*`.
- Secretos actuales:
  - `HEALTHCHECK_TOKEN`: Render y GitHub.
  - `GOOGLE_BOOKS_API_KEY`: Render; copia local en `backend/.env.googlebooks`.
  - `GEMINI_API_KEY` y `GROQ_API_KEY`: Render; copia local en `backend/.env.ai` (lo carga `config.py`).
  - Credenciales de Oracle, JWT y SMTP: Render.
- `backend/.gitignore` ignora `.env` y `.env.*` (excepto `.env.example`). Confirmar con `git check-ignore` antes de crear un archivo de secretos.

## Oracle

| Esquema | Uso | Archivo local |
|---|---|---|
| `BIBLIOTECA_PERSONAL` | **Producción** (Render) | `backend/.env` |
| `BIBLIOTECA_TEST` | Pruebas de migraciones y validaciones | `backend/.env.test` |

- **Ojo:** `backend/.env` apunta a producción. Un backend local con `.env` usa datos reales. Para pruebas, cargar `.env.test`; las variables de entorno tienen prioridad sobre el archivo `.env`.
- **Migraciones:** `backend/sql/NNN_*.sql`; las 001–009 están aplicadas en ambos esquemas. Nunca aplicarlas automáticamente al iniciar la app. Para una nueva:
  1. Crear el archivo siguiente (`010_…`). No modificar una migración ya aplicada.
  2. Confirmar `SESSION_USER` y `CURRENT_SCHEMA` → respaldar → aplicar en TEST → validar.
  3. **Con aprobación del usuario**, respaldar y aplicar en PERSONAL. Comparar la estructura con TEST y los datos con el respaldo.
  4. Aplicar la migración **antes** de desplegar el código que la necesita.
- Oracle confirma los DDL implícitamente: `ROLLBACK` no los deshace.
- **Respaldos lógicos** (JSON + DDL + SHA256) en `~/Backups/BibliotecaPersonal/`, fuera del repo.
- Al separar SQL en sentencias, respetar las comillas: los comentarios pueden contener `;`.
- Evitar `MERGE` y los `DELETE+INSERT` de la misma fila: provocan ORA-12860 en Autonomous Database. Usar SELECT y luego UPDATE o INSERT; ver `_get_or_create_id` en `books.py`.

## Convenciones de código

- **Backend:**
  - Endpoints en `app/api/v1/endpoints/`, esquemas en `app/schemas/` y lógica pura en `app/core/`, testeable sin base de datos.
  - Todas las consultas filtran por `user_id` y `deleted_at IS NULL`, con parámetros enlazados.
  - Las rutas fijas de `/books` (`/genres`, `/lookup`, `/check-isbn`) van **antes** de `/{book_id}`.
  - Tests: `tests/unit` y `tests/integration`, con cursores simulados (`MagicMock`) y `httpx.MockTransport`.
- **Frontend:**
  - Vistas en `src/views/`, componentes en `src/components/`, stores Pinia en `src/stores/` y utilidades en `src/utils/` (`dates.js`, `isbn.js`).
  - La API se consume con `src/utils/api.js` (axios + JWT).
  - ESLint **no** define globals de navegador ni de Node: usar `globalThis.navigator`, `globalThis.fetch`, `import process from 'node:process'` e `import { Buffer } from 'node:buffer'`.
  - Los specs de componentes que usan stores necesitan `setActivePinia(createPinia())`.
- **Textos:** la interfaz va en español. Los commits van en inglés, en formato convencional (`feat:`, `fix:`, `docs:`).
- **Atribución:**
  - Commits: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
  - PRs: `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- **Dependencias nuevas:** fijar la versión exacta (`--save-exact`) y preferir versiones con más de dos semanas de publicación.

## Notas de entorno

- **Playwright:** los navegadores propios no están instalados. Usar el Chrome del sistema con una configuración temporal que extienda `playwright.config.js` con `use: { channel: 'chrome' }` y un `webServer` de Vite, y borrarla al terminar.
  - El usuario suele tener `npm run dev` corriendo en el puerto 5173: usar otro puerto, no detener su servidor.
  - Con la caché de Vite en frío, la primera ejecución E2E puede fallar por una recarga de página; repetir antes de investigar.
- **Cámara en el celular:** `npm run dev:mobile` levanta Vite con HTTPS en la red local y la API por el proxy `/api` (`VITE_PROXY_TARGET`).
- **Keepalive de Oracle:** el workflow `.github/workflows/oracle-keepalive.yml` llama todos los días a `GET /health/db`; se puede ejecutar a mano con `gh workflow run oracle-keepalive.yml --ref main`.
- **Funcionalidad pendiente del top 3:** resúmenes con IA (Fase 2). Las recomendaciones (Fase 1) están en `docs/recomendaciones-ia.md`. **Deuda técnica:** CI de tests en PRs, consultas N+1 de autores en `GET /books/`, paginación y exportar/importar CSV.

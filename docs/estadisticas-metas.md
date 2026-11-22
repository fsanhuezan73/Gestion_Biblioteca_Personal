# Estadísticas y metas de lectura — validación

## Alcance

- Migración `backend/sql/007_add_reading_stats.sql`: `books.started_at`,
  `books.finished_at`, `books.page_count`, índice `(user_id, finished_at)` y
  tabla `reading_goals` (una meta por usuario y año, 1–365 libros).
- API: `GET /api/v1/stats/?year=`, `GET/PUT/DELETE /api/v1/goals/{year}`,
  fechas y páginas en `POST/PUT /books`, fechas automáticas en
  `PATCH /books/{id}/status`, filtro `without_finish_date` en `GET /books/`.
- Frontend: vista `/stats`, indicador de meta en la biblioteca, campos de fechas
  y páginas en el formulario y la ficha.
- «Hoy» se calcula en `APP_TIMEZONE` (por defecto `America/Santiago`).

## Pruebas automatizadas

- Backend: `pytest -q` (reglas de fechas, metas, estadísticas y aislamiento por usuario).
- Frontend: `npm run test:run`, `npm run lint`, `npm run build`.
- E2E: `npx playwright test` con el servidor de desarrollo en el puerto 5173
  (`tests/e2e/stats-goals.spec.js`, API simulada).

## Orden de despliegue

1. Respaldar y aplicar 007 en el esquema de pruebas; validar.
2. Respaldar y aplicar 007 en el esquema real (`BIBLIOTECA_PERSONAL`).
   Es compatible con el backend actual, que ignora las columnas nuevas.
3. Mergear a `main`: Render y Vercel despliegan el código nuevo.

Oracle confirma DDL implícitamente: un `ROLLBACK` no deshace la migración.
No volver a ejecutarla en un esquema donde ya esté aplicada.

## Validación en BIBLIOTECA_TEST (22 de noviembre de 2026)

- `SESSION_USER` y `CURRENT_SCHEMA` confirmados como `BIBLIOTECA_TEST`, con
  001–006 aplicadas y 007 ausente.
- Respaldo lógico privado (JSON de todas las tablas y recuentos) fuera de Git en
  `~/Backups/BibliotecaPersonal/20261122T185014Z-test-before-007/`.
- Migración 007 aplicada completa (9 sentencias). Recuentos de las tablas
  existentes sin cambios.
- Backend local contra el esquema de pruebas: 24/24 comprobaciones de API
  (fechas automáticas y explícitas, validaciones, filtro sin fecha, metas,
  estadísticas, aislamiento entre usuarios, año sin datos).
- Navegador: biblioteca con indicador de meta, panel de estadísticas en
  escritorio y móvil, ficha con fechas y días de lectura, formulario de edición.
  Sin errores en consola.
- Se crearon dos cuentas de validación (`validacion-007-*@validacion-biblioteca.com`)
  y tres libros «VALIDACIÓN 007 — …» en `BIBLIOTECA_TEST`.

Pendiente: respaldar y aplicar 007 en `BIBLIOTECA_PERSONAL` antes de mergear a `main`.

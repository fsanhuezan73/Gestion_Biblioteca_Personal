# Recomendaciones con IA (Fase 1)

Botón «Recomiéndame qué leer» en la página **Para ti** (`/for-you`, desde el menú). Devuelve
hasta 5 libros reales, cada uno con título, autor, motivo y sinopsis, a costo $0.
La Fase 2 (resúmenes) queda fuera de alcance.

## Flujo

1. `POST /api/v1/ai/recommendations` lee la biblioteca en una sola consulta
   (sin `personal_notes`).
2. Exige al menos `AI_MIN_RATED_BOOKS` (3) libros «Leído» con valoración (422) y
   cupo diario (429, antes de llamar a la IA).
3. Arma el perfil: hasta 40 libros leídos y valorados, primero los de más
   estrellas y, entre iguales, los terminados más recientemente. Solo envía título,
   autor, género y estrellas.
4. Pide 8 candidatos en JSON con esquema (`title`, `author`, `reason`) al primer
   proveedor de `AI_PROVIDER_ORDER`:
   - Un error HTTP (incluido el 429 o 503 por cuota o saturación), un timeout o
     una respuesta vacía pasa al siguiente proveedor.
   - Un JSON inválido se reintenta una vez con el mismo proveedor.
   - Presupuesto total de 45 s para la IA. Cada intento deja 15 s reservados
     para cada proveedor de respaldo pendiente.
   - Si todos fallan, responde 503 y no cuenta para el límite.
5. Descarta los candidatos que ya están en la biblioteca (título y apellido del
   autor normalizados, contra **todos** los libros activos) y verifica el resto en
   paralelo, con 12 s como máximo por candidato (`app/core/book_search.py`).
   Así el POST responde en menos de ~60 s, bajo el timeout de 90 s del frontend:
   - Google Books: `intitle:"…" inauthor:"…"`, con descripción e ISBN.
   - Open Library: `search.json?title=&author=`, si Google no encuentra el
     libro, falla o no hay clave.
   - Un resultado vale solo si coinciden el título (sin subtítulo ni
     paréntesis) y el apellido del autor.
6. Se quedan los primeros 5 verificados, sin repetidos. La sinopsis sale solo de
   Google Books; si falta, la tarjeta muestra solo el motivo. Si no queda
   ninguno, responde 502 y no cuenta para el límite.
7. Guarda el resultado en `ai_recommendations` (SELECT … FOR UPDATE y luego
   UPDATE o INSERT, sin MERGE) y vuelve a revisar el límite bajo bloqueo.

`GET /api/v1/ai/recommendations` devuelve el último resultado y recalcula
`in_library` para mostrar «✓ En tu biblioteca» en los libros agregados después.

## Proveedores (confirmados el 23-11-2026 en la documentación oficial)

| Proveedor | Modelo | Notas |
|---|---|---|
| Gemini | `gemini-3.5-flash-lite` (estable, GA en julio de 2026) | `generateContent` con `responseMimeType` y `responseJsonSchema`. Clave en el header `x-goog-api-key`. En el plan gratuito, Google usa el contenido para mejorar sus productos: por eso solo se envían metadatos. |
| Groq | `openai/gpt-oss-120b` (modelo de producción) | `response_format` con `json_schema` y `strict: true`, `reasoning_effort: low`. Plan gratuito: 30 solicitudes/min, 1.000/día, 8.000 tokens/min y 200.000/día (según la tabla de límites). |

Los modelos se cambian con `AI_GEMINI_MODEL` y `AI_GROQ_MODEL` sin tocar el código.

## Límite diario

- 5 generaciones **exitosas** por usuario y día (`AI_DAILY_LIMIT`). El día se
  calcula en `APP_TIMEZONE` (America/Santiago).
- Las fallas (503, 502) no descuentan cupo.
- Al agotar el cupo, el botón se deshabilita y se sigue mostrando el último
  resultado.

## Privacidad

- La consulta de la biblioteca no selecciona `personal_notes`, y un test lo
  verifica.
- La interfaz avisa: «Generado por IA. Solo se envían título, autor, género y
  estrellas; nunca tus notas».
- Los logs registran solo el proveedor y el tipo de falla, nunca las claves.

## Migración 009 — validación en BIBLIOTECA_TEST (23-11-2026)

- `SESSION_USER` y `CURRENT_SCHEMA` confirmados como `BIBLIOTECA_TEST`.
- Respaldo lógico con SHA256 verificado en
  `~/Backups/BibliotecaPersonal/20261123T234323Z-test-before-009/`.
- Migración aplicada (8 sentencias): columnas, restricciones (PK, FK con
  `ON DELETE CASCADE`, `IS JSON`, proveedor, conteo ≥ 0) y comentarios
  verificados.
- Instantánea posterior (`20261123T234404Z-test-after-009`): las 10 tablas
  existentes quedaron byte a byte iguales al respaldo. `AI_RECOMMENDATIONS` está
  vacía.

- Consultas reales del endpoint validadas contra TEST (23-11-2026):
  - Guardado (INSERT y luego UPDATE) y lectura del CLOB con tildes.
  - Contador diario y límite revisado bajo bloqueo.
  - Reinicio del contador al cambiar de día.
  - La fila de prueba se borró al terminar.
- Esta validación encontró que python-oracledb entrega el CLOB con `IS JSON` ya
  decodificado como lista. Está corregido y cubierto por un test.

## Prueba local contra BIBLIOTECA_TEST

`./start-test.sh` levanta el backend en el puerto 8001 contra `BIBLIOTECA_TEST`
y el frontend en el 5174. No interfiere con `npm run dev` (5173) ni con
producción.

- El script carga `backend/.env.test`, `backend/.env.googlebooks` y
  `backend/.env.ai` como variables de entorno, que tienen prioridad sobre
  `backend/.env` (producción).
- Se cancela si `ORACLE_USER` no es `BIBLIOTECA_TEST`.
- Al arrancar indica qué claves están presentes, sin mostrar sus valores.

### Pasos

1. Guardar las claves de IA en `backend/.env.ai`, ignorado por Git y sin
   mostrarlas en pantalla. Copia la clave de Gemini (Google AI Studio) y ejecuta:

   ```bash
   cd backend && touch .env.ai && chmod 600 .env.ai
   printf 'GEMINI_API_KEY=%s\n' "$(pbpaste)" >> .env.ai
   ```

   Copia la clave de Groq y ejecuta:

   ```bash
   printf 'GROQ_API_KEY=%s\n' "$(pbpaste)" >> .env.ai
   ```

   Opcional: para probar solo el respaldo, agrega `AI_PROVIDER_ORDER=groq`. Para
   tener más intentos en las pruebas, agrega `AI_DAILY_LIMIT=20`.
2. Desde la raíz del repo, ejecutar `./start-test.sh`.
3. Abrir http://localhost:5174 y crear una cuenta de prueba en «Registrarse». La
   cuenta queda en `BIBLIOTECA_TEST`.
4. Agregar al menos 3 libros con estado «Leído» y asignarles estrellas.
5. Pulsar «Recomiéndame qué leer». Lo normal es que tarde entre 3 y 10 s. En la
   terminal, el log
   `Recomendaciones: <proveedor> propuso N, M verificadas (IA x s, total y s)`
   indica qué proveedor respondió y cuánto tardó. Una línea
   `Proveedor de IA falló: gemini: HTTP 503` indica que Gemini estaba saturado y
   respondió Groq.
6. Si el navegador corta la espera, la sección vuelve a consultar el último
   resultado: si el servidor alcanzó a terminar, las recomendaciones aparecen
   igual.

## Prueba local contra BIBLIOTECA_PERSONAL (producción)

`./start-personal.sh` levanta el backend en el puerto 8002 contra
`BIBLIOTECA_PERSONAL` (`backend/.env`) y el frontend en el 5175. Sirve para
probar el código nuevo con tus datos reales antes de mergear a `main`.

- Antes de arrancar pide escribir `PERSONAL`. El script de Python, además, se
  niega a usar producción sin `--confirm-production` y comprueba que
  `ORACLE_USER` sea `BIBLIOTECA_PERSONAL`.
- **Todo cambio es real:** agregar o valorar libros, «Agregar a Quiero leer» y
  cada generación, que cuenta para el límite diario de tu cuenta, el mismo que
  usará el sitio en producción.
- Inicia sesión con tu cuenta real. Las claves de IA y de Google Books se leen
  de `backend/.env.ai` y `backend/.env.googlebooks`, igual que en la prueba con
  TEST.
- La migración 009 ya está aplicada en `BIBLIOTECA_PERSONAL`. El backend de
  Render (código anterior) ignora la tabla nueva, así que ambos conviven sin
  problemas.

### Diagnóstico del 23-11-2026

Una primera prueba local mostró «La solicitud tardó demasiado», aunque el
servidor terminó y guardó el resultado después de los 90 s del navegador. Cada
etapa medida por separado fue rápida (IA 2–5 s, verificación ~1,5 s), pero el
diseño original permitía, en el peor caso, más de 90 s (30 s por intento de IA,
con reintento y respaldo). Por eso se agregó el presupuesto total de tiempo, los
logs con tiempos y la recarga del resultado tras un error.

## Migración 009 — BIBLIOTECA_PERSONAL (23-11-2026)

- Aplicada con aprobación explícita del usuario. `SESSION_USER` y
  `CURRENT_SCHEMA` confirmados como `BIBLIOTECA_PERSONAL`, sin
  `AI_RECOMMENDATIONS` previa.
- Respaldo lógico previo con SHA256 verificado en
  `~/Backups/BibliotecaPersonal/20261124T012425Z-before-009/`.
- Migración aplicada (8 sentencias). La estructura de `AI_RECOMMENDATIONS`
  (columnas, restricciones, índices y comentarios) es idéntica a
  `BIBLIOTECA_TEST`.
- Instantánea posterior (`20261124T012500Z-after-009`): las 10 tablas existentes
  quedaron byte a byte iguales al respaldo. `AI_RECOMMENDATIONS` está vacía.

### Pendiente para producción

1. Pegar `GEMINI_API_KEY` y `GROQ_API_KEY` en Render (lo hace el usuario).
2. Mergear a `main` y comprobar que `/api/v1/ai/recommendations` aparece en
   `/openapi.json`.

## Pruebas

- Backend, sin llamadas reales (`httpx.MockTransport`):
  - `tests/unit/test_recommendations.py`
  - `tests/unit/test_ai_providers.py`
  - `tests/unit/test_book_search.py`
  - `tests/integration/test_ai_recommendations_api.py`
- Casos cubiertos:
  - JSON inválido y reintento; respaldo ante 429, 5xx, timeout o respuesta vacía.
  - Sin proveedores configurados.
  - Descarte de libros inexistentes y de libros ya en la biblioteca.
  - Mínimo de libros valorados, límite diario y su reinicio, carrera bajo
    bloqueo y en el INSERT.
  - Solo metadatos en el prompt y claves fuera de URL y logs.
- Frontend:
  - `src/stores/recommendations.spec.js`
  - `src/components/RecommendationsSection.spec.js`
  - E2E `tests/e2e/recommendations.spec.js`, con la API simulada.

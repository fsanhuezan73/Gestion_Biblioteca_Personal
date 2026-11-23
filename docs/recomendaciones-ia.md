# Recomendaciones con IA (Fase 1)

Botón «Recomiéndame qué leer» en la sección **Para ti** de la biblioteca. Devuelve
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
   - Un error HTTP (incluido el 429 por cuota), un timeout de 30 s o una
     respuesta vacía pasa al siguiente proveedor.
   - Un JSON inválido se reintenta una vez con el mismo proveedor.
   - Si todos fallan, responde 503 y no cuenta para el límite.
5. Descarta los candidatos que ya están en la biblioteca (título y apellido del
   autor normalizados, contra **todos** los libros activos) y verifica el resto en
   paralelo (`app/core/book_search.py`):
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

### Pendiente para producción

1. Con aprobación del usuario: respaldar y aplicar 009 en `BIBLIOTECA_PERSONAL`,
   y comparar la estructura con TEST y los datos con el respaldo.
2. Pegar `GEMINI_API_KEY` y `GROQ_API_KEY` en Render (lo hace el usuario).
3. Mergear a `main` y comprobar que `/api/v1/ai/recommendations` aparece en
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

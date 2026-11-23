# Portadas subidas por el usuario — validación

## Alcance

- Migración `backend/sql/008_add_book_covers.sql`: tabla `book_covers`
  (id UUID hex, `user_id`, tipo, tamaño, `BLOB`, fecha). No modifica `books`.
- API:
  - `POST /api/v1/covers` (JWT): cuerpo binario, tipo detectado por la firma del
    archivo (JPEG, PNG o WebP), máximo 2 MB. Devuelve `{id, content_type, byte_size}`.
  - `GET /api/v1/covers/{id}` (público): imagen con `Cache-Control: immutable`
    y `X-Content-Type-Options: nosniff`.
  - `PUT /books/{id}`: al cambiar `cover_url`, borra la portada subida anterior
    si ningún libro activo del usuario la usa.
  - `cover_url` en `POST/PUT /books`: vacía = `null`; solo `http(s)://` o rutas
    `/…`; máximo 500 caracteres.
- Frontend: sección «Portada» en `BookForm` (añadir y editar) con vista previa,
  subir/reemplazar, quitar y URL. `src/utils/images.js` reduce a 800 px y
  convierte a JPEG (calidad 0,85) en el navegador. La subida ocurre al guardar.

## Pruebas automatizadas

- Backend: `tests/unit/test_covers.py` y `tests/integration/test_covers_api.py`.
- Frontend: `src/utils/images.spec.js`, specs de portada en
  `BookForm.spec.js` y `stores/books.spec.js`.
- E2E: `tests/e2e/book-cover.spec.js` (subir con compresión real del navegador,
  reemplazar por URL, quitar y rechazar archivos que no son imágenes).

## Orden de despliegue

1. Respaldar y aplicar 008 en `BIBLIOTECA_TEST`; validar.
2. Respaldar y aplicar 008 en `BIBLIOTECA_PERSONAL` (con aprobación). Es
   aditiva: el backend actual la ignora.
3. Mergear a `main`: Render y Vercel despliegan el código nuevo. Comprobar que
   `/api/v1/covers` aparece en `/openapi.json`.

## Validación en BIBLIOTECA_TEST (22 de noviembre de 2026)

- `SESSION_USER` y `CURRENT_SCHEMA` confirmados como `BIBLIOTECA_TEST`.
- Respaldo lógico en `~/Backups/BibliotecaPersonal/20261122T225856Z-test-before-008/`.
- Migración aplicada (6 sentencias); estructura, restricciones e índice verificados.
- Backend local contra TEST, 17/17 comprobaciones: subida de 150 KB (bind BLOB
  mayor a 32 KB), lectura pública con bytes idénticos y cabeceras de caché,
  edición sin `cover_url` que conserva la imagen, reemplazo y eliminación que
  borran la imagen anterior, rechazo de más de 2 MB (413), SVG (415) y subida
  sin JWT (401), sin imágenes huérfanas al terminar.

## Validación en BIBLIOTECA_PERSONAL (22 de noviembre de 2026)

- Aplicada con aprobación explícita del usuario. `SESSION_USER` y `CURRENT_SCHEMA`
  confirmados como `BIBLIOTECA_PERSONAL`, sin `BOOK_COVERS` previa.
- Respaldo lógico previo con SHA256 verificado en
  `~/Backups/BibliotecaPersonal/20261123T000904Z-before-008/`.
- Migración aplicada (6 sentencias). Estructura de `BOOK_COVERS` (columnas,
  restricciones e índices) idéntica a `BIBLIOTECA_TEST`.
- Instantánea posterior (`20261123T000952Z-after-008`): las 9 tablas existentes
  quedaron byte a byte iguales al respaldo; `BOOK_COVERS` está vacía.

# Valoraciones y notas personales

## Alcance

- Valoración opcional entera de 1 a 5 y una nota privada por libro (máximo 5000 caracteres Unicode).
- Texto plano para reseñas, citas y anotaciones; no admite HTML ejecutable.
- Edición desde la ficha, guardado explícito, descarte y aviso al navegar con cambios pendientes.
- Notas vacías se guardan como NULL. Campos omitidos en PATCH conservan su valor.
- Estrellas en cuadrícula y tabla. El listado no consulta ni devuelve las notas.
- Solo el propietario del libro activo puede consultar/modificar; libros ajenos, eliminados
  e inexistentes responden 404. Se utiliza la autenticación JWT existente.

## Contrato

`PATCH /api/v1/books/{id}/personal`, requiere Bearer JWT:

```json
{"rating": 5, "personal_notes": "Mi reseña y una cita para recordar."}
```

Responde 200 con la ficha completa; 422 para campos desconocidos, cuerpo vacío,
estrellas no enteras/fuera de rango o notas demasiado largas; 401 sin autenticación.
`null` borra el campo. Crear/editar datos bibliográficos conserva el flujo anterior;
las valoraciones se gestionan después de guardar el libro, desde su ficha.

## Preparación de Oracle

El worktree NO aísla la base de datos. Usar un esquema de pruebas independiente y
credenciales propias en `backend/.env` del worktree. No copiar automáticamente el
`.env` del checkout principal ni ejecutar la migración contra la base compartida.

- Esquema vacío: aplicar 001, 002, 003, 004 y 005 en ese orden.
- Esquema existente con 001–004: aplicar únicamente `005_add_personal_reviews.sql`.
- La restricción `chk_books_rating` acepta NULL o exactamente 1, 2, 3, 4, 5.
- `personal_notes` usa CLOB; el límite de 5000 se valida en la API.
- Oracle confirma DDL implícitamente. No usar ROLLBACK como reversión de la migración.
- Volver al código anterior permite conservar las columnas adicionales; eliminarlas
  requiere una operación explícita que destruiría las valoraciones/notas guardadas.

## Pruebas automáticas

Backend (con dependencias instaladas y variables de prueba, sin conexión Oracle):

```bash
cd backend
ORACLE_USER=test ORACLE_PASSWORD=test ORACLE_DSN=test JWT_SECRET_KEY=testing-only-secret-not-for-production python -m pytest -q
```

Frontend:

```bash
cd frontend
npm run test:run
npm run build
```

Navegador (desde `frontend`, inicia Vite automáticamente en el puerto 5175):

```bash
npx playwright test --config playwright.worktree.config.js
```

Los tests de navegador interceptan
HTTP; no prueban persistencia real en Oracle. Los tests de API simulan las conexiones
y comprueban validación, parámetros SQL, condición de propietario y exclusión de borrados.

## Validación inicial con servicios simulados (17 de septiembre de 2026)

- Backend: 41 pruebas aprobadas (incluyen API simulada, sin Oracle real).
- Frontend: 14 pruebas aprobadas; ESLint y build aprobados.
- Chromium: 2 flujos aprobados (login y valoración/notas con API simulada).
- Capturas de escritorio y móvil revisadas en `frontend/test-results/` (ignoradas por Git).
- Ruff y revisión de espacios del diff aprobados.
- En esta primera fase la migración estaba preparada pero no aplicada. La posterior
  validación real se detalla a continuación.

## Validación con Oracle real (17 de septiembre de 2026, America/Santiago)

- Conexión comprobada: SESSION_USER y CURRENT_SCHEMA = `BIBLIOTECA_TEST`.
- Esquema inicialmente vacío; migraciones 001 a 005 ejecutadas en orden y sin errores.
- Tablas verificadas: USERS, BOOKS, AUTHORS, BOOK_AUTHORS, GENRES, PUBLISHERS.
- BOOKS contiene RATING y PERSONAL_NOTES (CLOB); CHK_BOOKS_RATING está activa.
- Backend del worktree: `http://127.0.0.1:8001`; frontend: `http://127.0.0.1:5174`.
- `.env` y `.env.local` configurados localmente e ignorados por Git. JWT distinto
  del checkout principal. No se modificó el esquema BIBLIOTECA_PERSONAL.
- Dos cuentas ficticias registradas por la API. Se conserva un libro de demostración
  y otro eliminado lógicamente para la prueba de acceso a libros borrados.
- Once grupos de comprobaciones reales aprobados: registro/login, creación de libro,
  guardado y lectura, CLOB de 5000 caracteres Unicode, rechazo de entradas inválidas,
  conservación tras editar título/estado, aislamiento entre usuarios, listado sin
  notas, borrado/restauración de datos personales, bloqueo de libros eliminados y
  verificación directa en Oracle de persistencia y restricción de estrellas.
- Chromium contra los servicios reales (sin interceptar HTTP): login, apertura de
  ficha, guardar 4 estrellas y notas, recargar, comprobar persistencia, cuadrícula
  y tabla. Sin errores JavaScript; capturas de escritorio y móvil revisadas.
- El checkout principal sigue limpio. No se realizó commit ni merge a development.

Las contraseñas de las cuentas ficticias se entregan en un archivo local temporal
con permisos restringidos, fuera del repositorio. No son credenciales de Oracle.
Puedes registrar otra cuenta desde el frontend para realizar tu revisión personal.

## Lista de comprobación para repetir la validación antes de integrar en development

1. Verificar las migraciones aplicadas (001–005 ya están instaladas en BIBLIOTECA_TEST;
   no volver a ejecutarlas) y arrancar el backend del worktree en 8001.
2. Arrancar el frontend con `VITE_API_URL=http://localhost:8001/api/v1 npm run dev -- --port 5174`.
3. Crear dos usuarios de prueba y un libro para cada uno.
4. Con el propietario, guardar 1 y 5 estrellas; probar notas con tildes, saltos de línea,
   comillas, emojis y 5000 caracteres. Recargar y comprobar persistencia.
5. Verificar valoración en tarjetas/tabla, quitarla y borrar las notas.
6. Cambiar título/estado de lectura y comprobar que las notas se conservan.
7. Con el segundo usuario, solicitar GET de la ficha y PATCH personal del libro ajeno:
   ambos deben devolver 404 y no alterar ningún dato.
8. Borrar lógicamente el libro y confirmar que PATCH devuelve 404.
9. Simular pérdida de red: debe mostrarse error conservando el borrador.
10. Confirmar que el checkout principal permanece limpio y revisar el diff de la rama
    `feature/valoraciones-notas` antes de decidir su integración.

No se incluye sincronización entre pestañas ni historial de notas; dos guardados
simultáneos del mismo campo conservan el último valor confirmado.

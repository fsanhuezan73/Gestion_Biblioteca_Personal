# Recuperación de contraseña: validación y activación

Estado al 19-09-2026: código integrado mediante PR #9, desplegado en Render
y Vercel, con `main` y `development` sincronizadas. La migración 006 está
aplicada y verificada tanto en `BIBLIOTECA_TEST` como en
`BIBLIOTECA_PERSONAL`. La recuperación está activada en Render; queda una
prueba manual del flujo publicado con una cuenta propia existente.

## Verificación local realizada

- Backend: 78 pruebas aprobadas; Ruff y compilación Python correctos.
- Frontend: 22 pruebas Vitest, ESLint y build correctos.
- Chromium con API simulada: 4 recorridos aprobados, incluidos solicitud,
  eliminación del token de la URL, restablecimiento y cambio desde Mi cuenta.
- Flujo HTTP backend con Oracle y correo simulados: se comprobó enlace de un solo
  uso, límite de tres solicitudes por correo/hora, respuesta indistinguible
  para correo inexistente, cambio de clave, revocación de JWT y rechazo del
  token reutilizado.
- SMTP: STARTTLS y SSL probados con objetos simulados; **no hubo envío real**.

Las pruebas locales con objetos simulados se complementaron posteriormente
con envíos reales a Mailtrap Sandbox y a Zoho mediante Brevo.

## Migración 006 en Oracle de pruebas (19-09-2026)

- `SESSION_USER` y `CURRENT_SCHEMA` confirmados como `BIBLIOTECA_TEST` antes
  de ejecutar DDL. Se verificaron 001–005 y la ausencia de 006.
- Respaldo lógico privado, con datos tipados, DDL y SHA-256 verificados:
  `/Users/fsanhuezan/private/BibliotecaTest-20260919T033408Z-before-006/`.
  El directorio tiene permisos `700` y el archivo de datos `600`.
- Archivo SQL aplicado: `006_add_password_recovery.sql`, SHA-256
  `10e207d0cc2b81b324d78182796a87c5808675114290c68dd1561bc8067d9bda`.
  Las 13 sentencias finalizaron correctamente.
- Se comprobaron `USERS.AUTH_VERSION` no nulo, las dos tablas nuevas, cinco
  restricciones activas y cinco índices. Todos los usuarios existentes tienen
  `AUTH_VERSION=0`; las tablas nuevas están vacías.
- Las filas previas de las seis tablas originales coinciden exactamente con
  el respaldo: 3 usuarios, 2 libros, 1 autor, 2 relaciones y 1 género.
- Prueba funcional HTTP contra Oracle real: se creó una cuenta ficticia única,
  se validaron solicitud, límite por correo, respuesta genérica para cuenta
  inexistente, expiración, uso único, cambio y reutilización de contraseña,
  así como revocación de JWT. El emisor SMTP fue interceptado: **no se enviaron
  correos reales**. Se eliminaron la cuenta y sus registros de prueba; la
  comprobación posterior confirmó tablas nuevas vacías y filas originales
  idénticas al respaldo.
- La prueba detectó y permitió corregir un interbloqueo por DML paralelo en
  Oracle al consumir tokens y un desfase entre el reloj de la aplicación y
  `SYSTIMESTAMP`. Ambas operaciones de consumo ahora se ejecutan en modo
  serial y registran una fecha no anterior a `created_at`.

## Pasos obligatorios antes de activar

1. ~~Confirmar el esquema de pruebas, 001–005 y crear respaldo.~~ Completado.
2. ~~Aplicar `backend/sql/006_add_password_recovery.sql` solo al esquema de
   pruebas y verificar estructura/datos.~~ Completado. Oracle confirma DDL
   implícitamente; un `ROLLBACK` no deshace esta migración.
3. Prueba controlada en `BIBLIOTECA_TEST` completada para solicitud
   existente/inexistente, límite por correo, vencimiento, doble uso, cambio de
   contraseña y JWT revocados. El límite por origen conserva cobertura de
   pruebas automatizadas, pero no se ejercitó en esta prueba Oracle real.
4. ~~Configurar Mailtrap Email Sandbox y comprobar la recepción del mensaje
   en su bandeja aislada.~~ Completado con credenciales renovadas y flujo real
   en `BIBLIOTECA_TEST`. Falta revisión visual del contenido y URL del segundo
   mensaje. Esta prueba **no demuestra entrega a un buzón personal real**.
5. ~~Respaldar y aplicar la migración 006 al esquema real tras aprobación.~~
   Completado y verificado. Desplegar el backend que usa `AUTH_VERSION`
   **después** de la migración. Los JWT anteriores, que no incluyen este
   claim, exigirán nuevo login.
6. ~~Desplegar frontend y backend, verificar la ruta `/reset-password`, TLS,
   política `no-referrer`, configurar SMTP en Render y activar
   `PASSWORD_RESET_ENABLED=true`.~~ Completado. Falta la prueba controlada
   de entrega y consumo desde el sitio público con una cuenta registrada.

No habilitar la recuperación si falla la verificación de esquema, entrega de
correo o URL del enlace. La tarea de correo en segundo plano es local al
proceso: si este termina antes de enviarla, no hay reintento persistente.

## Próxima prueba SMTP: Mailtrap Email Sandbox

Mailtrap Sandbox captura el correo de la aplicación sin entregarlo al
destinatario indicado. Se eligió para verificar autenticación SMTP, STARTTLS,
composición del mensaje y enlace de recuperación sin usar una cuenta real.

El 19-09-2026 se realizó un envío aislado usando las credenciales privadas
provistas para Sandbox: Mailtrap aceptó el mensaje por SMTP con STARTTLS en
el puerto 2525. El destinatario fue ficticio, no se consultó Oracle y el
token del enlace no existe en la base de datos. El propietario confirmó
después la recepción de ese primer mensaje en Sandbox.

El propietario renovó las credenciales. Con las credenciales nuevas se ejecutó
la solicitud HTTP real contra `BIBLIOTECA_TEST`: Mailtrap aceptó el segundo
correo, el token
persistido coincidió con el hash del enviado, el restablecimiento se completó,
un segundo uso falló y el JWT previo quedó revocado. Se eliminó la cuenta
ficticia y sus solicitudes; la comparación con el respaldo confirmó tablas
nuevas vacías y filas originales idénticas. El propietario confirmó la
recepción visual del segundo correo en Mailtrap. Queda revisar su contenido
y que el enlace apunte a `http://localhost:5173/reset-password`, sin copiar
ni compartir el token. Como el token ya fue consumido y la cuenta eliminada,
su enlace no debe volver a funcionar.

1. Crear una cuenta y una bandeja en **Email Sandbox** de Mailtrap. En la
   pestaña **Integration → SMTP**, obtener las credenciales de esa bandeja
   (no las de **Email API/SMTP** para envío real).
2. Guardarlas en un archivo privado fuera del repositorio, con permisos `600`:
   `SMTP_HOST=sandbox.smtp.mailtrap.io`, `SMTP_PORT=2525`,
   `SMTP_SECURITY=starttls`, `SMTP_USERNAME`, `SMTP_PASSWORD` y
   `SMTP_FROM_EMAIL`. Usar un remitente de prueba válido y configurar
   `FRONTEND_BASE_URL` con la URL local donde se abrirá el enlace.
3. Conectar la aplicación **solo a `BIBLIOTECA_TEST`**, crear una cuenta
   ficticia con correo de prueba y habilitar la recuperación únicamente en
   ese proceso de validación. Solicitar un enlace y comprobar en Mailtrap
   destinatario, asunto, cuerpo y URL, sin registrar ni compartir el token.
   Consumirlo una vez y verificar que el segundo uso y el JWT anterior fallan.
4. Eliminar la cuenta y solicitudes ficticias; comparar de nuevo las filas
   previas con el respaldo. Mantener `PASSWORD_RESET_ENABLED=false` en la
   configuración normal y no modificar `BIBLIOTECA_PERSONAL`.

La dirección personal del propietario no es necesaria para esta prueba:
Sandbox acepta un destinatario ficticio. Se necesitará una dirección real
recién al verificar la entrega **fuera del Sandbox** con el proveedor de
correo que vaya a usarse en el despliegue, después de acordar remitente,
dominio y ambiente de prueba. Ese envío requerirá autorización específica.

## Preflight y respaldo del esquema real (19-09-2026)

- Consulta **solo de lectura**: `SESSION_USER` y `CURRENT_SCHEMA` fueron
  `BIBLIOTECA_PERSONAL`. Hay seis tablas base y la migración 005 está
  completa. No existen `USERS.AUTH_VERSION`, las dos tablas de 006 ni sus
  índices/restricciones. No hay otros tipos de objeto fuera de tablas,
  índices, secuencias y LOB.
- Conteos antes de 006: 8 usuarios, 18 libros, 17 autores, 21 relaciones
  libro-autor, 9 géneros y 16 editoriales. `BIBLIOTECA_TEST` conserva la 006
  completa; sus datos originales siguen intactos.
- Respaldo lógico privado previo a 006:
  `/Users/fsanhuezan/private/BibliotecaPersonal-20260919T042301Z-before-006/`.
  Incluye datos tipados, DDL, metadatos y SHA-256. Se verificó lectura,
  conteos, estructura y permisos `700`/`600`. Su SHA-256 es
  `4b06f4fd2bf2d426f7a42e9cb0e84dd081d6b9d5c6d57af4713ca5387fac1106`.
  **No se ha probado una restauración**; el directorio contiene datos y hashes
  de contraseñas, y nunca debe subirse a Git.
- El manifiesto `render.yaml` ahora declara
  `PASSWORD_RESET_ENABLED`, `FRONTEND_BASE_URL` y las variables `SMTP_*` sin
  incluir secretos. `FRONTEND_BASE_URL` apunta a
  `https://gestion-biblioteca-personal.vercel.app`. Render ignora `sync: false`
  al actualizar un Blueprint existente, por lo que las claves y el interruptor
  se configuraron individualmente por la API de Render, preservando las
  variables previas. La API pública es
  `https://biblioteca-personal-api.onrender.com`.

### Secuencia de despliegue y activación

1. Acordar una ventana de cambio y la URL pública del frontend; confirmar
   acceso a Render y al proveedor SMTP real. Dejar la recuperación desactivada.
2. Inmediatamente antes de aplicar 006, repetir la comprobación de identidad,
   estructura y conteos del esquema real. Si hay cambios respecto del respaldo,
   crear un respaldo nuevo y detenerse hasta revisarlos.
3. ~~Con autorización expresa, aplicar solo las 13 sentencias de
   `backend/sql/006_add_password_recovery.sql` como `BIBLIOTECA_PERSONAL`,
   comprobando cada resultado.~~ Completado. Oracle confirma DDL implícitamente: ante un
   error parcial, **detenerse y auditar**, no repetir el archivo completo ni
   confiar en `ROLLBACK`.
4. ~~Comparar columnas, dos tablas, restricciones e índices con `BIBLIOTECA_TEST`;
   verificar `AUTH_VERSION=0` para los usuarios previos y que las seis tablas
   originales conserven sus filas del respaldo.~~ Completado.
5. ~~Solo tras esa verificación, desplegar el backend nuevo y después el
   frontend, y configurar URL pública, SMTP real y remitente verificado en
   Render.~~ Completado. Los JWT emitidos por el backend anterior requieren
   nuevo inicio de sesión porque no contienen `auth_version`.
6. ~~Activar `PASSWORD_RESET_ENABLED=true`.~~ Completado. Resta una prueba
   manual controlada con una cuenta existente desde el sitio público:
   confirmar recepción, uso único y revocación de sesión; revisar estado y
   límites del proveedor. No compartir ni registrar el enlace/token.

## Migración real y prueba Brevo (19-09-2026)

- Tras autorización expresa, se compararon de nuevo todas las filas de las
  seis tablas originales de `BIBLIOTECA_PERSONAL` con el respaldo anterior.
  No había divergencias y 006 seguía pendiente.
- Se aplicaron las 13 sentencias del archivo SQL con SHA-256
  `10e207d0cc2b81b324d78182796a87c5808675114290c68dd1561bc8067d9bda`.
  Una segunda conexión verificó las dos tablas nuevas, `AUTH_VERSION=0` para
  los ocho usuarios existentes, cinco restricciones, cinco índices y todas
  las filas originales idénticas al respaldo. Las tablas nuevas quedaron vacías.
- Los registros públicos del dominio muestran MX de Zoho, código Brevo, dos
  CNAME DKIM de Brevo y DMARC. Un correo de prueba sin token enviado por
  Brevo a `soporte@biblioteca-personal.site` fue recibido en Zoho; el
  propietario confirmó `DKIM=PASS` y `DMARC=PASS`.
- La aplicación local, conectada **solo a `BIBLIOTECA_TEST`**, emitió un enlace
  real mediante Brevo a ese buzón. El enlace se consumió una vez; un segundo
  uso y el JWT anterior fueron rechazados. Se borró la cuenta temporal y la
  comprobación contra el respaldo confirmó que las filas previas del esquema
  de pruebas siguen intactas. El propietario confirmó la recepción del correo
  concreto de este flujo en Zoho.
- Backend: 78 pruebas aprobadas. Frontend: 22 pruebas, lint y build aprobados.

## Despliegue y activación publicados (19-09-2026)

- PR #9 fusionado en `main`; `main` y `development` quedaron en
  `f24c65858db0bf0a937aa5bd25ad762f5db6f680`. Vercel confirmó el
  despliegue de producción y el bundle de la URL estable contiene las rutas
  `/forgot-password` y `/reset-password`. La API pública expone solicitud,
  confirmación y cambio autenticado de contraseña.
- El servicio Render `srv-daiaa5jm8hqs73bijn7g` despliega la rama `main`.
  Sus ocho variables nuevas se configuraron individualmente, preservando las
  existentes; ningún secreto se versionó ni se imprimió. El primer despliegue
  quedó `live` con `PASSWORD_RESET_ENABLED=false` y la API respondió `503`.
  El segundo quedó `live` con el interruptor en `true` y la API respondió
  `200` con el mensaje genérico para una dirección inexistente.
- Se confirmó que esa dirección no pertenecía a ninguna cuenta y se eliminó
  exclusivamente su solicitud sintética. La verificación Oracle posterior
  confirmó la migración completa, tablas nuevas vacías y todas las filas
  originales idénticas al respaldo.
- La aceptación HTTP no demuestra todavía que el proceso publicado entregue
  el enlace a una cuenta real: esa comprobación requiere la prueba manual
  pendiente con una cuenta registrada y correo accesible.

# Menú de navegación

Barra común para todas las páginas con sesión iniciada: botón **☰** en la
esquina superior izquierda y **Cerrar sesión** a la derecha, fuera del menú.
Es un cambio solo de frontend: sin endpoints ni migraciones nuevos.

## Comportamiento

- Opciones del menú, en orden: 📚 Mi colección, ✨ Para ti, 📊 Estadísticas,
  📷 Escanear libro, ➕ Añadir libro y 👤 Mi cuenta. La página actual queda
  marcada (`aria-current="page"`).
- El menú se cierra al elegir una opción, al navegar (incluido atrás/adelante),
  con Esc o al hacer clic fuera. Se implementa solo con Vue, sin el JS de
  Bootstrap.
- «Escanear libro» abre `/books/add?scan=1`. Al abrirse el escáner, la vista
  quita `?scan=1` con `router.replace` (sin entrada en el historial), así que
  cada nueva selección vuelve a abrirlo, aunque ya estés en «Añadir libro» y sin
  perder lo escrito. Desde ese momento el menú marca «Añadir libro».
- `/library` muestra solo la colección. Las recomendaciones pasaron a la página
  **Para ti** (`/for-you`), que avisa si el servicio no está disponible.
- «Estadísticas» y «Mi cuenta» ya no tienen el enlace «← Volver»; detalle,
  edición y «Añadir libro» lo conservan.
- En pantallas angostas (< 420 px) la barra muestra «Biblioteca» en lugar de
  «Biblioteca Personal» para que todo quepa en una línea.

## Tabla con encabezado fijo

En la vista **Tabla**, la tabla tiene scroll propio (alto máximo: la pantalla
menos 6rem) y el `<thead>` usa `position: sticky`. Así la fila de encabezados
queda visible al bajar, también en el celular con scroll horizontal.

## Archivos

- `frontend/src/components/AppNavbar.vue`: barra y menú.
- `frontend/src/App.vue`: muestra la barra en las rutas con `requiresAuth`.
- `frontend/src/views/ForYouView.vue` y la ruta `ForYou` en el router.
- `frontend/src/components/BookTable.vue`: encabezado fijo.

## Validación

- Unitarias: `AppNavbar.spec.js` (opciones, página activa, cierre y logout) y
  `ForYouView.spec.js` (carga y servicio no disponible).
- E2E: `tests/e2e/app-menu.spec.js` (menú, navegación, reabrir el escáner
  dos veces seguidas, logout y encabezado fijo con 40 libros). Se actualizaron los E2E de estadísticas, escáner,
  formatos y recomendaciones para navegar por el menú.
- Revisión visual con Chrome a 1280, 430, 375 y 320 px de ancho. A 320 px el
  nombre se corta con «…», pero la barra queda en una línea.

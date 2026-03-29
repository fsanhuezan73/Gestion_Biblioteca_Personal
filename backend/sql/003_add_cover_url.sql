-- Migración 003: Agregar columna cover_url a BOOKS
-- Almacena la URL de la portada obtenida por autocompletado ISBN (Google Books API)
ALTER TABLE books ADD cover_url VARCHAR2(500);

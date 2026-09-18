-- Valoraciones y notas personales. Ejecutar después de 001–004.
-- Aplicar primero en un esquema Oracle de pruebas, nunca automáticamente.
-- Oracle confirma DDL implícitamente: un ROLLBACK no deshace esta migración.
ALTER TABLE books ADD (
    rating NUMBER,
    personal_notes CLOB,
    CONSTRAINT chk_books_rating CHECK (rating IN (1, 2, 3, 4, 5))
);

COMMENT ON COLUMN books.rating IS 'Valoración privada de 1 a 5; NULL indica sin valorar';
COMMENT ON COLUMN books.personal_notes IS 'Notas privadas en texto plano; API limitada a 5000 caracteres';

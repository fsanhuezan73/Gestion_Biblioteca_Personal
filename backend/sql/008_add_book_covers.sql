-- Portadas subidas por el usuario. Ejecutar después de 001–007.
-- Aplicar primero en un esquema Oracle de pruebas, nunca automáticamente.
-- Oracle confirma DDL implícitamente: un ROLLBACK no deshace esta migración.
-- No modifica datos existentes: books.cover_url sigue siendo la fuente de la portada
-- y apunta a GET /api/v1/covers/{id} cuando la imagen se subió a la app.

CREATE TABLE book_covers (
    id            VARCHAR2(32)  NOT NULL,
    user_id       NUMBER        NOT NULL,
    content_type  VARCHAR2(20)  NOT NULL,
    byte_size     NUMBER(8)     NOT NULL,
    data          BLOB          NOT NULL,
    created_at    TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT pk_book_covers PRIMARY KEY (id),
    CONSTRAINT fk_book_covers_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_book_covers_id CHECK (REGEXP_LIKE(id, '^[0-9a-f]{32}$')),
    CONSTRAINT chk_book_covers_type CHECK (content_type IN ('image/jpeg', 'image/png', 'image/webp')),
    CONSTRAINT chk_book_covers_size CHECK (byte_size BETWEEN 1 AND 2097152)
);

CREATE INDEX idx_book_covers_user ON book_covers(user_id);

COMMENT ON TABLE  book_covers              IS 'Imágenes de portada subidas por los usuarios';
COMMENT ON COLUMN book_covers.id           IS 'UUID v4 en hexadecimal (32 caracteres), no adivinable';
COMMENT ON COLUMN book_covers.content_type IS 'Tipo MIME detectado por el backend (JPEG, PNG o WebP)';
COMMENT ON COLUMN book_covers.byte_size    IS 'Tamaño de la imagen en bytes (máximo 2 MB)';

-- Registrar los formatos que el usuario posee, sin clasificar libros existentes.
CREATE TABLE book_formats (
    book_id     NUMBER NOT NULL,
    format_code VARCHAR2(11) NOT NULL,
    CONSTRAINT pk_book_formats PRIMARY KEY (book_id, format_code),
    CONSTRAINT fk_book_formats_book FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
    CONSTRAINT chk_book_formats_code CHECK (format_code IN ('physical', 'kindle', 'apple_books'))
);

-- ============================================================
-- Script: 004_add_reading_status.sql
-- Descripción: Agrega columna reading_status a la tabla BOOKS
--              Valores posibles: 'Quiero leer', 'Leyendo', 'Leído'
-- HU-06: Gestionar el estado de lectura
-- Base de datos: Oracle Autonomous Database 26ai
-- IMPORTANTE: Ejecutar como BIBLIOTECA_PERSONAL
-- ============================================================

ALTER TABLE books ADD reading_status VARCHAR2(20) DEFAULT 'Quiero leer' NOT NULL;

-- Constraint CHECK para validar valores permitidos
ALTER TABLE books ADD CONSTRAINT chk_reading_status
    CHECK (reading_status IN ('Quiero leer', 'Leyendo', 'Leído'));

COMMENT ON COLUMN books.reading_status IS 'Estado de lectura: Quiero leer, Leyendo, Leído';

COMMIT;

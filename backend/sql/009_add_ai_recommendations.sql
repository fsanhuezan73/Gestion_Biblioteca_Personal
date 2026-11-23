-- Recomendaciones con IA (Fase 1). Ejecutar después de 001–008.
-- Aplicar primero en un esquema Oracle de pruebas, nunca automáticamente.
-- Oracle confirma DDL implícitamente: un ROLLBACK no deshace esta migración.
-- Aditiva: no modifica tablas ni datos existentes.
-- Una fila por usuario con el último resultado y el conteo diario. El backend la
-- escribe con SELECT y luego UPDATE o INSERT (sin MERGE, por ORA-12860).

CREATE TABLE ai_recommendations (
    user_id       NUMBER        NOT NULL,
    result        CLOB,
    provider      VARCHAR2(20),
    model         VARCHAR2(80),
    generated_at  TIMESTAMP,
    daily_count   NUMBER(3)     DEFAULT 0 NOT NULL,
    count_date    DATE,
    CONSTRAINT pk_ai_recommendations PRIMARY KEY (user_id),
    CONSTRAINT fk_ai_recommendations_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_ai_rec_result_json CHECK (result IS JSON),
    CONSTRAINT chk_ai_rec_provider CHECK (provider IN ('gemini', 'groq')),
    CONSTRAINT chk_ai_rec_daily_count CHECK (daily_count >= 0)
);

COMMENT ON TABLE  ai_recommendations              IS 'Último resultado de recomendaciones con IA por usuario y su conteo diario';
COMMENT ON COLUMN ai_recommendations.result       IS 'JSON con los libros recomendados ya verificados (sin notas privadas)';
COMMENT ON COLUMN ai_recommendations.provider     IS 'Proveedor que generó el resultado: gemini o groq';
COMMENT ON COLUMN ai_recommendations.model        IS 'ID exacto del modelo usado';
COMMENT ON COLUMN ai_recommendations.generated_at IS 'Fecha y hora de la última generación exitosa';
COMMENT ON COLUMN ai_recommendations.daily_count  IS 'Generaciones exitosas en count_date';
COMMENT ON COLUMN ai_recommendations.count_date   IS 'Día (zona APP_TIMEZONE) al que corresponde daily_count';

CREATE EXTENSION vector;
SELECT * FROM pg_extension;

-- 1. Borrar tabla si existe (para empezar limpio)
DROP TABLE IF EXISTS canciones_texto;

-- 2. Crear la tabla
CREATE TABLE canciones_texto (
    id SERIAL PRIMARY KEY,
    track_name TEXT,
    artist_name TEXT,
    lyrics TEXT
);

-- 3. Crear el índice de búsqueda rápida
--    El índice se hace sobre la columna 'lyrics'
CREATE INDEX idx_lyrics ON canciones_texto USING GIN (to_tsvector('spanish', lyrics));
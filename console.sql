CREATE EXTENSION vector;
SELECT * FROM pg_extension;

-- Borrar tabla si existe (para empezar limpio)
DROP TABLE IF EXISTS canciones_texto;

CREATE TABLE canciones_texto (
    id SERIAL PRIMARY KEY,
    track_name TEXT,
    artist_name TEXT,
    lyrics TEXT
);

-- Creo el índice sobre la columna 'lyrics'
CREATE INDEX idx_lyrics ON canciones_texto USING GIN (to_tsvector('spanish', lyrics));
"""
build_metadata_sqlite_optimized.py
----------------------------------

Construye directamente metadata.db desde los CSV originales de FMA,
sin generar el JSON intermedio gigante.

Características:
- Usa tracks.csv con MultiIndex y track_id real.
- Normaliza track_id a 6 dígitos (000002, 034996, 122911, etc.).
- Limpia headers "unnamed" y niveles vacíos.
- Reconstruye las secciones track/artist/album de forma anidada
  SOLO en memoria por fila (no arma un dict gigante).
- Extrae: title, artist_name, genre_top, year.
- Inserta en SQLite en batches para mejor performance.
"""

import os
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

from audio.config_metadata import METADATA_DIR, METADATA_STORE

DB_PATH = METADATA_STORE / "metadata.db"

# ============================================================
# NORMALIZACIÓN GLOBAL DEL TRACK ID (siempre 6 dígitos)
# ============================================================

def normalize_tid(tid):
    tid = str(tid).strip()
    try:
        return f"{int(tid):06d}"
    except Exception:
        return tid.zfill(6)


# ============================================================
# HELPERS PARA MULTIINDEX Y NESTING
# ============================================================

def load_multilevel_csv(path: Path) -> pd.DataFrame:
    """
    Carga CSV con MultiIndex (tracks.csv) usando dtype=str
    y reemplaza NaN por None.
    """
    df = pd.read_csv(path, header=[0, 1, 2], dtype=str, low_memory=False)
    df = df.replace({np.nan: None})
    return df


def clean_header(col_tuple):
    """
    Limpia un header de MultiIndex:
    - Quita 'Unnamed'
    - Quita strings vacíos
    - Devuelve un tuple reducido (p.ej. ('track', 'title'))
    """
    cleaned = []
    for c in col_tuple:
        if c is None:
            continue
        s = str(c)
        if s.lower().startswith("unnamed"):
            continue
        if s.strip() == "":
            continue
        cleaned.append(s)
    return tuple(cleaned)


def recursive_insert(target: dict, key_tuple, value):
    """
    Inserta recursivamente en un dict anidado usando un tuple como ruta.
    Ejemplo:
        key_tuple = ('track', 'title')
        → target['track']['title'] = value
    """
    if len(key_tuple) == 1:
        target[key_tuple[0]] = value
        return

    head, tail = key_tuple[0], key_tuple[1:]
    if head not in target:
        target[head] = {}

    recursive_insert(target[head], tail, value)


def row_to_nested(row: pd.Series) -> dict:
    """
    Convierte una fila de tracks.csv (MultiIndex) en un dict anidado:
    {
      "track": {...},
      "artist": {...},
      "album": {...},
      ...
    }
    """
    nested = {}
    for raw_col, value in row.items():
        header = clean_header(raw_col)
        if not header:
            continue
        recursive_insert(nested, header, value)
    return nested


# ============================================================
# SQLITE: CREACIÓN DE TABLA E ÍNDICES
# ============================================================

def create_table(conn: sqlite3.Connection) -> None:
    c = conn.cursor()

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS metadata (
            track_id TEXT PRIMARY KEY,
            title    TEXT,
            artist   TEXT,
            genre    TEXT,
            year     TEXT
        );
        """
    )

    # Índices útiles para búsquedas
    c.execute("CREATE INDEX IF NOT EXISTS idx_metadata_artist ON metadata(artist);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_metadata_genre  ON metadata(genre);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_metadata_year   ON metadata(year);")

    conn.commit()


# ============================================================
# INSERCIÓN DIRECTA DESDE tracks.csv
# ============================================================

def insert_from_tracks_csv(conn: sqlite3.Connection, tracks_path: Path) -> None:
    if not tracks_path.exists():
        raise FileNotFoundError(f"tracks.csv no existe en: {tracks_path}")

    print(f"\n[INFO] Cargando tracks.csv desde: {tracks_path}")
    tracks_df = load_multilevel_csv(tracks_path)

    # Columna real del track_id en el MultiIndex
    tid_col = ('Unnamed: 0_level_0', 'Unnamed: 0_level_1', 'track_id')
    if tid_col not in tracks_df.columns:
        raise RuntimeError("No se encuentra la columna real del track_id en tracks.csv")

    cursor = conn.cursor()

    total_rows = len(tracks_df)
    batch = []
    BATCH_SIZE = 1000

    print(f"[INFO] Procesando {total_rows} filas de tracks.csv…")

    for i, row in tracks_df.iterrows():
        raw_tid = row[tid_col]
        tid = normalize_tid(raw_tid)

        nested = row_to_nested(row)
        track = nested.get("track", {}) or {}
        artist = nested.get("artist", {}) or {}
        album = nested.get("album", {}) or {}

        # Campos planos
        title = (track.get("title") or "").strip()

        artist_name = (
            (artist.get("name") or "").strip()
            or (track.get("artist_name") or "").strip()
        )

        genre_top = (track.get("genre_top") or "").strip()

        # Año robusto
        year_raw = (
            album.get("date_released")
            or track.get("date_created")
            or track.get("date_recorded")
            or ""
        )
        year_str = ""
        if isinstance(year_raw, str) and len(year_raw) >= 4:
            year_str = year_raw[:4]

        batch.append((tid, title, artist_name, genre_top, year_str))

        # Inserción por lotes
        if len(batch) >= BATCH_SIZE:
            cursor.executemany(
                """
                INSERT OR REPLACE INTO metadata (track_id, title, artist, genre, year)
                VALUES (?, ?, ?, ?, ?)
                """,
                batch,
            )
            conn.commit()
            print(f"[SQLITE] Insertadas {i + 1}/{total_rows} filas…")
            batch.clear()

    # Insertar lo que quede pendiente
    if batch:
        cursor.executemany(
            """
            INSERT OR REPLACE INTO metadata (track_id, title, artist, genre, year)
            VALUES (?, ?, ?, ?, ?)
            """,
            batch,
        )
        conn.commit()
        print(f"[SQLITE] Insertadas {total_rows}/{total_rows} filas (lote final).")


# ============================================================
# ENTRYPOINT PRINCIPAL
# ============================================================

def build_sqlite_direct_from_csv() -> None:
    print("\n=== GENERANDO metadata.db (SIN JSON INTERMEDIO) ===")

    os.makedirs(METADATA_STORE, exist_ok=True)

    if DB_PATH.exists():
        print(f"[INFO] Eliminando BD anterior: {DB_PATH}")
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    print(f"[INFO] Conectado a SQLite: {DB_PATH}")

    create_table(conn)

    tracks_path = Path(METADATA_DIR) / "tracks.csv"
    insert_from_tracks_csv(conn, tracks_path)

    conn.close()
    print(f"[OK] Base SQLite generada en: {DB_PATH}")


if __name__ == "__main__":
    build_sqlite_direct_from_csv()

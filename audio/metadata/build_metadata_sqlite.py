import os
import json
import sqlite3
from pathlib import Path

from audio.config_metadata import PARSED_METADATA_PATH, METADATA_STORE

DB_PATH = METADATA_STORE / "metadata.db"


# ============================================================
# CREAR TABLA PLANA DE METADATA
# ============================================================

def create_table(conn: sqlite3.Connection) -> None:
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS metadata (
            track_id TEXT PRIMARY KEY,
            title    TEXT,
            artist   TEXT,
            genre    TEXT,
            year     TEXT
        );
    """)

    c.execute("CREATE INDEX IF NOT EXISTS idx_metadata_artist ON metadata(artist);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_metadata_genre  ON metadata(genre);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_metadata_year   ON metadata(year);")

    conn.commit()


# ============================================================
# CARGAR JSON ANIDADO
# ============================================================

def load_json() -> dict:
    if not PARSED_METADATA_PATH.exists():
        raise FileNotFoundError(f"No existe {PARSED_METADATA_PATH}")

    with open(PARSED_METADATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# INSERTAR DATOS (FLATTEN)
# ============================================================

def insert_data(conn: sqlite3.Connection, data: dict) -> None:
    c = conn.cursor()
    rows = []

    for track_id, rec in data.items():
        track = rec.get("track", {}) or {}
        artist = rec.get("artist", {}) or {}
        album = rec.get("album", {}) or {}

        # Campos planos
        title = track.get("title") or ""

        artist_name = (
            artist.get("name")
            or track.get("artist_name")
            or ""
        )

        genre_top = track.get("genre_top") or ""

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

        rows.append((
            str(track_id),
            str(title),
            str(artist_name),
            str(genre_top),
            str(year_str),
        ))

    print(f"[SQLITE] Insertando {len(rows)} tracks…")

    c.executemany(
        """
        INSERT INTO metadata (track_id, title, artist, genre, year)
        VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )

    conn.commit()
    print("[OK] Inserción completa.")


# ============================================================
# ENTRYPOINT
# ============================================================

def build_sqlite() -> None:
    print("\n=== GENERANDO metadata.db ===")

    os.makedirs(METADATA_STORE, exist_ok=True)

    if DB_PATH.exists():
        print(f"[INFO] Eliminando BD anterior: {DB_PATH}")
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)

    create_table(conn)

    data = load_json()

    insert_data(conn, data)

    conn.close()
    print(f"[OK] Base SQLite generada en: {DB_PATH}")


if __name__ == "__main__":
    build_sqlite()

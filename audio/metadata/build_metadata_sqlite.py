<<<<<<< HEAD
# audio/metadata/build_metadata_sqlite.py

=======
>>>>>>> f84e43eb0e438e1855f7aa7d373bd1f07924ecec
import os
import json
import sqlite3
from pathlib import Path

<<<<<<< HEAD
from audio.config_metadata import PARSED_METADATA_PATH, METADATA_OUT_DIR

DB_PATH = Path(METADATA_OUT_DIR) / "metadata.db"


def create_tables(conn: sqlite3.Connection) -> None:
    c = conn.cursor()

    # 🔥 IMPORTANTE: tirar la tabla vieja si existe, para evitar esquemas antiguos
    c.execute("DROP TABLE IF EXISTS metadata;")

    c.execute(
        """
        CREATE TABLE metadata (
            track_id TEXT PRIMARY KEY,
            track    TEXT,
            artist   TEXT,
            album    TEXT,
            genre    TEXT,
            features TEXT
        );
        """
    )

    # índice por track_id (extra, la PK ya indexa, pero no molesta)
    c.execute(
        "CREATE INDEX IF NOT EXISTS idx_metadata_track_id ON metadata(track_id);"
    )
=======
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
>>>>>>> f84e43eb0e438e1855f7aa7d373bd1f07924ecec

    conn.commit()


<<<<<<< HEAD
=======
# ============================================================
# CARGAR JSON ANIDADO
# ============================================================

>>>>>>> f84e43eb0e438e1855f7aa7d373bd1f07924ecec
def load_json() -> dict:
    if not PARSED_METADATA_PATH.exists():
        raise FileNotFoundError(f"No existe {PARSED_METADATA_PATH}")

    with open(PARSED_METADATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


<<<<<<< HEAD
def insert_data(conn: sqlite3.Connection, data: dict) -> None:
    c = conn.cursor()

    print(f"[SQLITE] Insertando {len(data)} tracks…")

    rows = []
    for raw_tid, record in data.items():
        # normalizamos el track_id: "034996" -> "34996"
        try:
            norm_tid = str(int(raw_tid))
        except ValueError:
            norm_tid = raw_tid

        track = json.dumps(record.get("track", {}), ensure_ascii=False)
        artist = json.dumps(record.get("artist", {}), ensure_ascii=False)
        album = json.dumps(record.get("album", {}), ensure_ascii=False)
        genre = json.dumps(record.get("genre", {}), ensure_ascii=False)
        features = json.dumps(record.get("features", {}), ensure_ascii=False)

        rows.append((norm_tid, track, artist, album, genre, features))

    c.executemany(
        """
        INSERT INTO metadata (
            track_id, track, artist, album, genre, features
        ) VALUES (?, ?, ?, ?, ?, ?)
=======
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
>>>>>>> f84e43eb0e438e1855f7aa7d373bd1f07924ecec
        """,
        rows,
    )

    conn.commit()
    print("[OK] Inserción completa.")


<<<<<<< HEAD
def build_sqlite() -> None:
    print("\n=== GENERANDO metadata.db ===")

    os.makedirs(METADATA_OUT_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    create_tables(conn)

    data = load_json()
=======
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

>>>>>>> f84e43eb0e438e1855f7aa7d373bd1f07924ecec
    insert_data(conn, data)

    conn.close()
    print(f"[OK] Base SQLite generada en: {DB_PATH}")


if __name__ == "__main__":
    build_sqlite()

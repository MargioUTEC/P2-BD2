import os
import json
import sqlite3
from pathlib import Path

from audio.config_metadata import PARSED_METADATA_PATH, METADATA_OUT_DIR

DB_PATH = Path(METADATA_OUT_DIR) / "metadata.db"


def create_tables(conn):
    c = conn.cursor()

    # Tabla principal donde guardaremos TODO como JSON
    c.execute("""
        CREATE TABLE IF NOT EXISTS metadata (
            track_id TEXT PRIMARY KEY,
            track_json TEXT,
            artist_json TEXT,
            album_json TEXT,
            genre_json TEXT,
            features_json TEXT
        );
    """)

    # Índices útiles
    c.execute("CREATE INDEX IF NOT EXISTS idx_metadata_trackid ON metadata(track_id);")

    conn.commit()


def load_json():
    if not PARSED_METADATA_PATH.exists():
        raise FileNotFoundError(f"No existe {PARSED_METADATA_PATH}")

    with open(PARSED_METADATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def insert_data(conn, data):
    c = conn.cursor()

    total = len(data)
    print(f"[SQLITE] Insertando {total} tracks…")

    count = 0

    for track_id, record in data.items():

        c.execute("""
            INSERT OR REPLACE INTO metadata (
                track_id, track_json, artist_json, album_json, genre_json, features_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            track_id,
            json.dumps(record.get("track", {})),
            json.dumps(record.get("artist", {})),
            json.dumps(record.get("album", {})),
            json.dumps(record.get("genre", {})),
            json.dumps(record.get("features", {})),
        ))

        count += 1
        if count % 5000 == 0:
            print(f"  → {count}/{total} insertados…")
            conn.commit()

    conn.commit()
    print("[OK] Inserción completa.")


def build_sqlite():
    print("\n=== GENERANDO metadata.db ===")

    # Crear carpeta si no existe
    os.makedirs(METADATA_OUT_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)

    create_tables(conn)

    data = load_json()

    insert_data(conn, data)

    conn.close()

    print(f"[OK] Base SQLite generada en: {DB_PATH}")


if __name__ == "__main__":
    build_sqlite()

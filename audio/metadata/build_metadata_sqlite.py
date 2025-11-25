# audio/metadata/build_metadata_sqlite.py

import os
import json
import sqlite3
from pathlib import Path

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

    conn.commit()


def load_json() -> dict:
    if not PARSED_METADATA_PATH.exists():
        raise FileNotFoundError(f"No existe {PARSED_METADATA_PATH}")

    with open(PARSED_METADATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


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
        """,
        rows,
    )

    conn.commit()
    print("[OK] Inserción completa.")


def build_sqlite() -> None:
    print("\n=== GENERANDO metadata.db ===")

    os.makedirs(METADATA_OUT_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    create_tables(conn)

    data = load_json()
    insert_data(conn, data)

    conn.close()
    print(f"[OK] Base SQLite generada en: {DB_PATH}")


if __name__ == "__main__":
    build_sqlite()

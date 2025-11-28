import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional

from audio.config_metadata import METADATA_STORE

DB_PATH = METADATA_STORE / "metadata.db"


class MetadataSQLite:
    """
    Acceso sencillo a metadata.db.

    Tabla:
        metadata(track_id TEXT PRIMARY KEY,
                 title TEXT,
                 artist TEXT,
                 genre TEXT,
                 year TEXT)
    """

    def __init__(self) -> None:
        # check_same_thread=False para poder usar la conexión desde FastAPI
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        print(f"[SQLITE] Conectado a {DB_PATH}")

    # ==========================
    # CONSULTA BÁSICA
    # ==========================

    def get_by_track_id(self, track_id: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.execute(
            """
            SELECT track_id, title, artist, genre, year
            FROM metadata
            WHERE track_id = ?
            """,
            (track_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    # Alias para compatibilidad
    def get_metadata(self, track_id: str) -> Optional[Dict[str, Any]]:
        return self.get_by_track_id(track_id)

    # ==========================
    # BÚSQUEDA POR FILTROS
    # ==========================

    def search(
        self,
        *,
        artist: Optional[str] = None,
        genre: Optional[str] = None,
        year: Optional[str | int] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        query = """
            SELECT track_id, title, artist, genre, year
            FROM metadata
            WHERE 1=1
        """
        params: list[Any] = []

        if artist:
            query += " AND artist = ?"
            params.append(artist)

        if genre:
            query += " AND genre = ?"
            params.append(genre)

        if year:
            query += " AND year = ?"
            params.append(str(year))

        query += " LIMIT ?"
        params.append(limit)

        cur = self.conn.execute(query, params)
        return [dict(r) for r in cur.fetchall()]

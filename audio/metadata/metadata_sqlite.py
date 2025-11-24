import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional
from audio.config_metadata import METADATA_OUT_DIR

DB_PATH = Path(METADATA_OUT_DIR) / "metadata.db"


class MetadataSQLite:
    def __init__(self):
        # Permite uso desde workers de FastAPI
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        print(f"[SQLITE] Conectado a {DB_PATH}")

    # ============================================================
    # FORMATEADOR → Compatible con AudioMetadataFusion
    # ============================================================
    def _normalize_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        """
        Convierte la fila plana del JOIN en:
        {
           "track": {...},
           "artist": {...},
           "album": {...}
        }
        """
        row = dict(row)

        normalized = {
            "track": {
                "track_id": row.get("track_id"),
                "title": row.get("title"),
                "genre_top": row.get("genre_top"),
                "date_released": row.get("date_released"),
            },
            "artist": {
                "id": row.get("artist_id"),
                "name": row.get("artist_name"),
                "location": row.get("artist_location"),
            },
            "album": {
                "id": row.get("album_id"),
                "title": row.get("album_title"),
                "type": row.get("album_type"),
            }
        }

        return normalized

    # ============================================================
    # CONSULTAS
    # ============================================================

    def get_track(self, track_id: str) -> Optional[Dict[str, Any]]:
        """Devuelve la fila cruda."""
        cur = self.conn.execute("""
            SELECT * FROM tracks WHERE track_id = ?
        """, (track_id,))
        r = cur.fetchone()
        return dict(r) if r else None

    def get_by_track_id(self, track_id: str) -> Optional[Dict[str, Any]]:
        """JOIN completo normalizado."""
        cur = self.conn.execute("""
            SELECT 
                t.track_id, t.title, t.genre_top, t.date_released,
                a.id AS artist_id, a.name AS artist_name, a.location AS artist_location,
                al.id AS album_id, al.title AS album_title, al.type AS album_type
            FROM tracks t
            LEFT JOIN artists a ON t.artist_id = a.id
            LEFT JOIN albums al ON t.album_id = al.id
            WHERE t.track_id = ?
        """, (track_id,))

        row = cur.fetchone()
        if not row:
            return None
        return self._normalize_row(row)

    def get_by_artist(self, artist_id: str) -> List[Dict[str, Any]]:
        cur = self.conn.execute("""
            SELECT * FROM tracks WHERE artist_id = ?
        """, (artist_id,))
        return [dict(r) for r in cur.fetchall()]

    def get_by_genre(self, genre: str) -> List[Dict[str, Any]]:
        cur = self.conn.execute("""
            SELECT * FROM tracks WHERE genre_top = ?
        """, (genre,))
        return [dict(r) for r in cur.fetchall()]

    def get_by_year(self, year: int) -> List[Dict[str, Any]]:
        year = str(year)
        cur = self.conn.execute("""
            SELECT * FROM tracks 
            WHERE substr(date_released, 1, 4) = ?
        """, (year,))
        return [dict(r) for r in cur.fetchall()]

    # ============================================================
    # INTERFAZ LEGACY → /metadata/track/{id}
    # ============================================================
    def get_metadata(self, track_id: str) -> Optional[Dict[str, Any]]:
        """
        Compatible con la API antigua.
        """
        return self.get_by_track_id(track_id)

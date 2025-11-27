<<<<<<< HEAD
# audio/metadata/metadata_sqlite.py

import sqlite3
import json
from pathlib import Path
from typing import Dict, Any, Optional

from audio.config_metadata import METADATA_OUT_DIR

DB_PATH = Path(METADATA_OUT_DIR) / "metadata.db"
=======
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional

from audio.config_metadata import METADATA_STORE

DB_PATH = METADATA_STORE / "metadata.db"
>>>>>>> f84e43eb0e438e1855f7aa7d373bd1f07924ecec


class MetadataSQLite:
    """
<<<<<<< HEAD
    Acceso a metadata usando SQLite.

    La tabla 'metadata' tiene columnas:
      - track_id (TEXT, PK, sin ceros a la izquierda, ej. "34996")
      - track, artist, album, genre, features (JSON en texto)

    Todos los métodos devuelven dicts con la misma estructura
    que tenías en parsed_metadata.json:
        {
          "track": {...},
          "artist": {...},
          "album": {...},
          "genre": {...},
          "features": {...}
        }
    """

    def __init__(self) -> None:
        self._db_path = DB_PATH
        print(f"[SQLITE] Usando base de metadata en: {self._db_path}")

    # ------------------------------
    # utilidades internas
    # ------------------------------
    def _get_conn(self) -> sqlite3.Connection:
        """
        Creamos una conexión nueva por llamada.
        check_same_thread=False permite usarla desde hilos distintos.
        """
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _normalize_tid(track_id: str) -> str:
        """
        Normaliza el track_id:
          "034996" -> "34996"
          "34996"  -> "34996"
        Si no se puede convertir a int, se deja igual.
        """
        try:
            return str(int(track_id))
        except ValueError:
            return track_id

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> Dict[str, Any]:
        """
        Convierte una fila de la tabla metadata a un dict anidado.
        """
        def decode(col: str) -> Dict[str, Any]:
            txt = row[col]
            if txt is None or txt == "":
                return {}
            try:
                return json.loads(txt)
            except json.JSONDecodeError:
                return {}

        return {
            "track": decode("track"),
            "artist": decode("artist"),
            "album": decode("album"),
            "genre": decode("genre"),
            "features": decode("features"),
        }

    # ------------------------------
    # API pública
    # ------------------------------
    def get_metadata(self, track_id: str) -> Optional[Dict[str, Any]]:
        """
        Devuelve la metadata COMPLETA para un track_id dado,
        o None si no existe.
        """
        norm_tid = self._normalize_tid(track_id)

        with self._get_conn() as conn:
            cur = conn.execute(
                """
                SELECT track, artist, album, genre, features
                FROM metadata
                WHERE track_id = ?
                """,
                (norm_tid,),
            )
            row = cur.fetchone()

        if row is None:
            return None

        return self._row_to_record(row)

    def get_by_track_id(self, track_id: str) -> Optional[Dict[str, Any]]:
        """
        Alias más semántico para usar desde el fusionador.
        """
        return self.get_metadata(track_id)
=======
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
>>>>>>> f84e43eb0e438e1855f7aa7d373bd1f07924ecec

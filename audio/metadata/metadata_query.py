"""
metadata_query.py
-----------------
Consultas de alto nivel sobre el metadata utilizando:

- B+Tree para búsqueda por track_id
- Índices invertidos para consultas por genre_id, album_id, artist_id, año
- Tabla completa en memoria para filtros adicionales

Estructura del JSON (parsed_metadata.json), opción C:

{
  "68580": {
    "track":   { ... },
    "artist":  { ... },
    "album":   { ... },
    "genre":   { ... },
    "features": { ... },
    "echonest": { ... }
  },
  ...
}
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any, Optional

from config_metadata import (
    PARSED_METADATA_PATH,
    METADATA_DIR,
    BPLUS_ORDER,
)

# Import interno del B+Tree
from .metadata_index_bptree import (
    MetadataBPlusTree,
    build_metadata_bptree,
)


# ============================================================
# CARGA DE DATOS PARSEADOS
# ============================================================

def _load_parsed_metadata() -> Dict[str, Dict[str, Any]]:
    """
    Carga el gran diccionario de metadata preprocesada.

    Retorna:
        dict: { track_id(str): { "track": {...}, "artist": {...}, ... }, ... }
    """
    import json

    path = Path(PARSED_METADATA_PATH)
    if not path.exists():
        raise FileNotFoundError(
            f"No se encuentra {path}. Ejecuta parser_metadata.py primero."
        )

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# CARGA DE ÍNDICES INVERTIDOS EN MEMORIA
# ============================================================

def _load_inverted_index(name: str) -> Dict[str, List[str]]:
    """
    Carga índices invertidos simples (genre_id → lista de track_ids, etc.)

    name debe ser uno de:
      - "genre_index.json"
      - "artist_index.json"
      - "album_index.json"
      - "year_index.json"
    """
    import json

    path = Path(METADATA_DIR) / name

    if not path.exists():
        raise FileNotFoundError(
            f"Índice invertido faltante: {path}. "
            f"Ejecuta metadata.build_inverted_indexes primero."
        )

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# OBJETO PRINCIPAL DE CONSULTA
# ============================================================

class MetadataQuery:
    """
    Encapsula:
      - B+Tree para consultas directas por track_id
      - Índices invertidos (genre, artist, album, year)
      - Tabla completa de metadata (dict en memoria)

    Uso típico:

        mq = MetadataQuery()
        track = mq.get_by_track_id("68580")
        rock_tracks = mq.get_by_genre(30)
        tracks_2012 = mq.get_by_year(2012)
        combo = mq.filter(genre=30, year=2012)
    """

    def __init__(self, build_bptree: bool = True):
        # 1. Metadata completa en memoria
        self.table: Dict[str, Dict[str, Any]] = _load_parsed_metadata()

        # 2. B+Tree para búsquedas rápidas por track_id
        self.bptree: Optional[MetadataBPlusTree] = None
        if build_bptree:
            # Construimos el B+Tree una sola vez
            self.bptree = build_metadata_bptree(
                metadata_dict=self.table,
                order=BPLUS_ORDER,
            )

        # 3. Índices invertidos
        self.genre_index: Dict[str, List[str]] = _load_inverted_index("genre_index.json")
        self.artist_index: Dict[str, List[str]] = _load_inverted_index("artist_index.json")
        self.album_index: Dict[str, List[str]] = _load_inverted_index("album_index.json")
        self.year_index: Dict[str, List[str]] = _load_inverted_index("year_index.json")

    # ========================================================
    # CONSULTAS POR track_id
    # ========================================================
    def get_by_track_id(self, tid: str) -> Optional[Dict[str, Any]]:
        """
        Recupera un registro completo por track_id.

        - Si hay B+Tree, usa bptree.search(int(tid))
        - Si no, cae a self.table[tid] directamente
        """
        # 1) Intentar vía B+Tree
        if self.bptree is not None:
            try:
                key = int(tid)
            except ValueError:
                # si viene como '001234' igual será convertible
                key = int(tid.strip())

            record = self.bptree.search(key)
            if record is not None:
                return record

        # 2) Fallback: acceso directo al dict
        return self.table.get(str(tid))

    # ========================================================
    # CONSULTAS POR GENRE
    # ========================================================
    def get_by_genre(self, genre_id: str | int) -> List[Dict[str, Any]]:
        """
        Retorna una lista de metadata filtrada por genre_id (id numérico de FMA).
        """
        track_ids = self.genre_index.get(str(genre_id), [])
        return [self.table[tid] for tid in track_ids if tid in self.table]

    # ========================================================
    # CONSULTAS POR ARTISTA
    # ========================================================
    def get_by_artist(self, artist_id: str | int) -> List[Dict[str, Any]]:
        """
        Retorna todas las canciones de un artista (según artist_id).
        """
        track_ids = self.artist_index.get(str(artist_id), [])
        return [self.table[tid] for tid in track_ids if tid in self.table]

    # ========================================================
    # CONSULTAS POR ÁLBUM
    # ========================================================
    def get_by_album(self, album_id: str | int) -> List[Dict[str, Any]]:
        """
        Retorna todas las canciones de un álbum (según album_id).
        """
        track_ids = self.album_index.get(str(album_id), [])
        return [self.table[tid] for tid in track_ids if tid in self.table]

    # ========================================================
    # CONSULTAS POR AÑO
    # ========================================================
    def get_by_year(self, year: int | str) -> List[Dict[str, Any]]:
        """
        Retorna todos los tracks para un año dado (YYYY).
        """
        return [
            self.table[tid]
            for tid in self.year_index.get(str(year), [])
            if tid in self.table
        ]

    # ========================================================
    # CONSULTAS COMBINADAS (genre + año, artista + álbum, etc.)
    # ========================================================
    def filter(
        self,
        genre: str | int | None = None,
        year: int | str | None = None,
        artist: str | int | None = None,
        album: str | int | None = None,
    ) -> List[Dict[str, Any]]:
        """
        Consulta combinada con AND lógico entre filtros.

        Ejemplo:
            filter(genre=30, year=2010)

        Retorna:
            Lista de tracks que cumplen todos los filtros.
        """
        # Iniciar candidatos con todos los track_ids
        candidates = set(self.table.keys())

        if genre is not None:
            candidates &= set(self.genre_index.get(str(genre), []))

        if year is not None:
            candidates &= set(self.year_index.get(str(year), []))

        if artist is not None:
            candidates &= set(self.artist_index.get(str(artist), []))

        if album is not None:
            candidates &= set(self.album_index.get(str(album), []))

        return [self.table[tid] for tid in candidates]

    # ========================================================
    # UTILIDAD: Obtener recomendaciones híbridas
    # ========================================================
    def enrich_audio_results(
        self,
        audio_results: List[tuple[str, float]],
    ) -> List[Dict[str, Any]]:
        """
        Dado un ranking de resultados de audio (track_id, score),
        añade metadata relevante (título, artista, género, año).

        audio_results = [
            ("001234", 0.91),
            ("009991", 0.87),
            ...
        ]

        Retorna:
            [
                {
                   "track_id": "001234",
                   "score": 0.91,
                   "title": "...",
                   "artist": "...",
                   "genre": "...",
                   "year": 2011
                },
                ...
            ]
        """
        enriched: List[Dict[str, Any]] = []

        for tid, score in audio_results:
            md = self.table.get(str(tid), {})

            track = md.get("track", {}) or {}
            artist = md.get("artist", {}) or {}
            genre = md.get("genre", {}) or {}

            # Título del track (si existe)
            title = track.get("title")

            # Nombre del artista (si existe)
            artist_name = (
                artist.get("name")
                or artist.get("artist_name")
                or artist.get("id")  # fallback: id si no hay nombre
            )

            # Representación de género: título si lo tenemos, si no, genre_top
            genre_display = (
                genre.get("title")
                or track.get("genre_top")
            )

            # Año: podemos inferirlo a partir de date_released/date_created
            year = None
            date_val = track.get("date_released") or track.get("date_created")
            if isinstance(date_val, str) and len(date_val) >= 4 and date_val[:4].isdigit():
                year = int(date_val[:4])

            enriched.append({
                "track_id": str(tid),
                "score": float(score),
                "title": title,
                "artist": artist_name,
                "genre": genre_display,
                "year": year,
            })

        return enriched

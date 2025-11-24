"""
metadata_query.py
-----------------
Consultas de alto nivel sobre el metadata utilizando:

- B+Tree para búsqueda por track_id (por ahora no lo usamos)
- Índices invertidos para consultas por genre_id, album_id, artist_id
- Tabla completa en memoria para filtros adicionales como año, split, etc.
"""

from typing import List, Dict, Any
import json

from audio.config_metadata import (
    PARSED_METADATA_PATH,
    METADATA_DIR,
)

from audio.metadata.metadata_index_bptree import MetadataBPlusTree


# ============================================================
# CARGA DE DATOS PARSEADOS
# ============================================================

def _load_parsed_metadata() -> Dict[str, Dict[str, Any]]:
    """
    Carga el gran diccionario JSON donde está toda la metadata preprocesada.

    Retorna:
        dict: { track_id(str): {metadata...}, ... }
    """
    path = PARSED_METADATA_PATH  # ya es un Path completo al JSON

    if not path.exists():
        raise FileNotFoundError(
            f"No se encuentra {path}. Ejecuta parser_metadata.py primero."
        )

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Debug opcional
    print(f"[METADATA] JSON cargado desde: {path}")
    print(f"[METADATA] Total tracks: {len(data)}")

    return data


# ============================================================
# CARGA DE ÍNDICES INVERTIDOS EN MEMORIA
# ============================================================

def _load_inverted_index(name: str) -> Dict[str, List[str]]:
    """
    Carga índices invertidos simples (genre_id → lista de track_ids, etc.)

    name debe ser uno de:
      - genre_index.json
      - artist_index.json
      - album_index.json
      - year_index.json
    """
    path = METADATA_DIR / name

    if not path.exists():
        raise FileNotFoundError(
            f"Índice invertido faltante: {path}. Ejecuta build_inverted_indexes.py"
        )

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# OBJETO PRINCIPAL DE CONSULTA
# ============================================================

class MetadataQuery:
    """
    Encapsula:
      - Tabla completa de metadata (dict en memoria)
      - Índices invertidos (genre, artist, album, year)
    """

    def __init__(self):
        # 1. Metadata completa
        self.table: Dict[str, Dict[str, Any]] = _load_parsed_metadata()

        # 2. (Opcional) B+Tree, ahora no lo usamos directamente
        self.bptree = MetadataBPlusTree()

        # 3. Índices invertidos
        self.genre_index = _load_inverted_index("genre_index.json")
        self.artist_index = _load_inverted_index("artist_index.json")
        self.album_index = _load_inverted_index("album_index.json")
        self.year_index = _load_inverted_index("year_index.json")

    # --------------------------------------------------------
    # Normalización de track_id
    # --------------------------------------------------------
    def _normalize_tid(self, tid: str) -> str:
        """
        Intenta mapear el track_id a una clave existente en self.table,
        manejando ceros a la izquierda o diferencias de formato.
        """
        tid_str = str(tid)

        # 1) Si existe tal cual
        if tid_str in self.table:
            return tid_str

        # 2) Quitar ceros a la izquierda
        tid_no_zeros = tid_str.lstrip("0")
        if tid_no_zeros in self.table:
            return tid_no_zeros

        # 3) Volver a formatear con 6 dígitos (ej. 34996 -> "034996")
        if tid_no_zeros.isdigit():
            padded = f"{int(tid_no_zeros):06d}"
            if padded in self.table:
                return padded

        # Si nada coincide, devolvemos el original (fallará luego el get)
        return tid_str

    # ========================================================
    # CONSULTAS POR track_id
    # ========================================================
    def get_by_track_id(self, tid: str) -> Dict[str, Any] | None:
        """
        Recupera un registro completo por track_id desde la tabla en memoria,
        normalizando el ID si es necesario.
        """
        norm_tid = self._normalize_tid(tid)
        return self.table.get(norm_tid)

    # ========================================================
    # CONSULTAS POR GENRE
    # ========================================================
    def get_by_genre(self, genre_id: str) -> List[Dict[str, Any]]:
        track_ids = self.genre_index.get(str(genre_id), [])
        return [self.table[tid] for tid in track_ids if tid in self.table]

    # ========================================================
    # CONSULTAS POR ARTISTA
    # ========================================================
    def get_by_artist(self, artist_id: str) -> List[Dict[str, Any]]:
        track_ids = self.artist_index.get(str(artist_id), [])
        return [self.table[tid] for tid in track_ids if tid in self.table]

    # ========================================================
    # CONSULTAS POR ÁLBUM
    # ========================================================
    def get_by_album(self, album_id: str) -> List[Dict[str, Any]]:
        track_ids = self.album_index.get(str(album_id), [])
        return [self.table[tid] for tid in track_ids if tid in self.table]

    # ========================================================
    # CONSULTAS POR AÑO
    # ========================================================
    def get_by_year(self, year: int) -> List[Dict[str, Any]]:
        track_ids = self.year_index.get(str(year), [])
        return [self.table[tid] for tid in track_ids if tid in self.table]

    # ========================================================
    # CONSULTAS COMBINADAS
    # ========================================================
    def filter(
        self,
        genre: str | None = None,
        year: int | None = None,
        artist: str | None = None,
        album: str | None = None,
    ) -> List[Dict[str, Any]]:
        """
        Consulta combinada con AND lógico entre filtros.
        """
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
    # UTILIDAD: enriquecer resultados de audio
    # ========================================================
    def enrich_audio_results(self, audio_results: List[tuple[str, float]]):
        enriched = []
        for tid, score in audio_results:
            norm_tid = self._normalize_tid(tid)
            md = self.table.get(norm_tid, {})
            enriched.append(
                {
                    "track_id": norm_tid,
                    "score": score,
                    "title": md.get("track", {}).get("title"),
                    "artist": md.get("artist", {}).get("name"),
                    "genre": md.get("track", {}).get("genre_top"),
                    "year": md.get("track", {}).get("date_released"),
                }
            )
        return enriched

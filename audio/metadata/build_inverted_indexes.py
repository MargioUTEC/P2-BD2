"""
build_inverted_indexes.py
----------------------------------

Genera los índices invertidos del dataset FMA a partir del
archivo parseado: parsed_metadata.json (versión C, JSON anidado)

Índices generados:
    - genre_index.json    : genre_id → [track_id]
    - artist_index.json   : artist_id → [track_id]
    - album_index.json    : album_id → [track_id]
    - year_index.json     : year → [track_id]
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any

from config_metadata import (
    METADATA_DIR,
    PARSED_METADATA_PATH,
)

# -------------------------------------------------------------
# LOGGING
# -------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("build_indexes")


# =============================================================
# FUNCIONES AUXILIARES
# =============================================================

def _safe_add(index_dict: Dict[str, List[str]], key: str, track_id: str):
    """Añade track_id a la lista del índice para 'key'."""
    if key not in index_dict:
        index_dict[key] = []
    index_dict[key].append(track_id)


def _extract_year(date_val) -> str | None:
    """
    Extrae el año desde un valor tipo fecha:
    - "2012-08-03"
    - "2012"
    - None
    """
    if date_val is None:
        return None
    if isinstance(date_val, int):
        return str(date_val)
    if isinstance(date_val, str) and len(date_val) >= 4 and date_val[:4].isdigit():
        return date_val[:4]
    return None


# =============================================================
# PROCESAMIENTO PRINCIPAL
# =============================================================

def build_inverted_indexes():
    log.info("=== Construyendo índices invertidos FMA (versión C) ===")

    parsed_path = Path(PARSED_METADATA_PATH)

    if not parsed_path.exists():
        raise FileNotFoundError(
            f"No se encuentra {parsed_path}. "
            f"Debes ejecutar parser_metadata.py primero."
        )

    log.info(f"Cargando metadata desde: {parsed_path}")

    with open(parsed_path, "r", encoding="utf-8") as f:
        metadata: Dict[str, Dict[str, Any]] = json.load(f)

    total_tracks = len(metadata)
    log.info(f"Total tracks cargados: {total_tracks:,}")

    # Índices invertidos
    genre_index: Dict[str, List[str]] = {}
    artist_index: Dict[str, List[str]] = {}
    album_index: Dict[str, List[str]] = {}
    year_index: Dict[str, List[str]] = {}

    # =============================================================
    # RECORRER TODOS LOS TRACKS
    # =============================================================
    for tid, md in metadata.items():
        track = md.get("track", {}) or {}
        artist = md.get("artist", {}) or {}
        album = md.get("album", {}) or {}

        # ----------------- GENRE INDEX (por genre_id) -----------------
        # Usamos 'genres' o 'genres_all' (listas de ids)
        g_list = track.get("genres") or track.get("genres_all")

        if isinstance(g_list, list):
            for g in g_list:
                _safe_add(genre_index, str(g), tid)
        elif isinstance(g_list, dict):
            # Por si viene como dict {id: algo}
            for g in g_list.keys():
                _safe_add(genre_index, str(g), tid)

        # ----------------- ARTIST INDEX -----------------
        artist_id = artist.get("id") or artist.get("artist_id")
        if artist_id is not None:
            _safe_add(artist_index, str(artist_id), tid)

        # ----------------- ALBUM INDEX ------------------
        album_id = album.get("id") or album.get("album_id")
        if album_id is not None:
            _safe_add(album_index, str(album_id), tid)

        # ----------------- YEAR INDEX -------------------
        date_val = track.get("date_released") or track.get("date_created")
        year = _extract_year(date_val)
        if year is not None:
            _safe_add(year_index, year, tid)

    log.info("Índices construidos correctamente.")

    # =============================================================
    # GUARDAR TODOS LOS ÍNDICES
    # =============================================================
    def save_index(data: Dict, name: str):
        out_path = Path(METADATA_DIR) / name
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        log.info(f"Guardado: {out_path} ({len(data)} claves)")

    save_index(genre_index, "genre_index.json")
    save_index(artist_index, "artist_index.json")
    save_index(album_index, "album_index.json")
    save_index(year_index, "year_index.json")

    log.info("\n🎉 Índices invertidos generados con éxito.\n")


# =============================================================
# MAIN
# =============================================================
if __name__ == "__main__":
    build_inverted_indexes()

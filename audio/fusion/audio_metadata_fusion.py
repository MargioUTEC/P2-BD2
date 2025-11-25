# audio/fusion/audio_metadata_fusion.py

"""
audio_metadata_fusion.py
------------------------
Fusión de resultados de audio (índice invertido) con metadata
guardada en SQLite.

score_final = alpha * score_audio + (1 - alpha) * score_metadata
"""

from typing import List, Dict, Any, Optional

from audio.fusion.audio_backends import InvertedIndexAudioBackend
from audio.metadata.metadata_sqlite import MetadataSQLite


class AudioMetadataFusion:
    """
    Encapsula la lógica de fusión entre:
      - backend acústico (InvertedIndexAudioBackend)
      - metadata (MetadataSQLite)
    """

    def __init__(
        self,
        audio_backend: InvertedIndexAudioBackend,
        metadata_db: MetadataSQLite,
        alpha: float = 0.7,
    ) -> None:
        self.audio_backend = audio_backend
        self.metadata_db = metadata_db
        self.alpha = alpha

    # ============================
    # MÉTRICA PARA METADATA
    # ============================
    @staticmethod
    def _metadata_score(
        candidate_md: Dict[str, Any],
        reference_md: Dict[str, Any],
    ) -> float:
        """
        Versión simple:
          +1 si coincide genre_top
          +1 si coincide año de release (4 dígitos)
        """

        score = 0.0

        # Género
        genre_q = reference_md.get("track", {}).get("genre_top")
        genre_r = candidate_md.get("track", {}).get("genre_top")
        if genre_q and genre_r and genre_q == genre_r:
            score += 1.0

        # Año (priorizamos album.date_released; si no, track.date_released)
        def _year(md: Dict[str, Any]) -> Optional[str]:
            album_date = md.get("album", {}).get("date_released")
            track_date = md.get("track", {}).get("date_released")
            val = album_date or track_date
            if isinstance(val, str) and len(val) >= 4:
                return val[:4]
            return None

        year_q = _year(reference_md)
        year_r = _year(candidate_md)

        if year_q and year_r and year_q == year_r:
            score += 1.0

        return score

    # ============================
    # FUSIÓN
    # ============================
    def search_by_track(
        self,
        query_track_id: str,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Devuelve una lista de dicts con:
          - track_id
          - score (final)
          - score_audio
          - score_metadata
          - title, artist, genre, year
        """

        # 1) búsqueda acústica
        audio_results = self.audio_backend.search_similar(
            query_track_id, top_k=top_k
        )

        if not audio_results:
            return []

        # 2) metadata de referencia (el track de la query)
        reference_md = self.metadata_db.get_by_track_id(query_track_id)

        if reference_md is None:
            # No hay metadata para la query -> usamos solo audio
            print(
                f"[WARN] Metadata para query_track_id={query_track_id} no encontrada. "
                f"Se usará solo score de audio."
            )

        enriched: List[Dict[str, Any]] = []

        # 3) enriquecemos cada vecino
        for tid, audio_score in audio_results:
            tid_str = str(tid)

            candidate_md = self.metadata_db.get_by_track_id(tid_str)

            if candidate_md is not None and reference_md is not None:
                md_score = self._metadata_score(candidate_md, reference_md)
                title = candidate_md.get("track", {}).get("title")
                artist = candidate_md.get("artist", {}).get("name")
                genre = candidate_md.get("track", {}).get("genre_top")
                year = (
                    candidate_md.get("album", {}).get("date_released")
                    or candidate_md.get("track", {}).get("date_released")
                )
            else:
                md_score = 0.0
                title = None
                artist = None
                genre = None
                year = None

            final_score = (
                self.alpha * float(audio_score)
                + (1.0 - self.alpha) * float(md_score)
            )

            enriched.append(
                {
                    "track_id": tid_str,
                    "score": float(final_score),
                    "score_audio": float(audio_score),
                    "score_metadata": float(md_score),
                    "title": title,
                    "artist": artist,
                    "genre": genre,
                    "year": year,
                }
            )

        enriched.sort(key=lambda x: x["score"], reverse=True)
        return enriched[:top_k]

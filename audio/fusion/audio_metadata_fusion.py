"""
audio_metadata_fusion.py
------------------------
Módulo que combina resultados de audio (índice invertido o KNN)
con metadata tabular para generar recomendaciones enriquecidas.

El parámetro alpha controla la mezcla:
    score_final = alpha * score_audio + (1 - alpha) * score_metadata
"""

from typing import List, Dict, Any

from audio.fusion.audio_backends import InvertedIndexAudioBackend
from audio.metadata.metadata_query import MetadataQuery


class AudioMetadataFusion:
    """
    Encapsula la lógica de fusión entre:
        - Búsqueda acústica (InvertedIndexAudioBackend)
        - Metadata tabular estructurada (MetadataQuery)
    """

    def __init__(
        self,
        audio_backend: InvertedIndexAudioBackend,
        metadata_query: MetadataQuery,
        alpha: float = 0.7,  # peso del score de audio
    ):
        self.audio_backend = audio_backend
        self.metadata_query = metadata_query
        self.alpha = alpha  # mezcla entre audio y metadata

    # ============================================================
    # MÉTRICA SIMPLE PARA METADATA (puedes mejorarla después)
    # ============================================================
    def _metadata_score(
        self,
        candidate_md: Dict[str, Any] | None,
        reference_md: Dict[str, Any] | None,
    ) -> float:
        """
        Calcula similitud de metadata entre un resultado y la metadata del query.
        Versión mínima:
            +1 si coinciden el género principal
            +1 si coincide el año (por fecha de release)
        """
        if not candidate_md or not reference_md:
            return 0.0

        score = 0.0

        # --- Género principal ---
        genre_q = reference_md.get("track", {}).get("genre_top")
        genre_r = candidate_md.get("track", {}).get("genre_top")

        if genre_q is not None and genre_r is not None and genre_q == genre_r:
            score += 1.0

        # --- Año (comparando las 4 primeras cifras de date_released) ---
        year_q = reference_md.get("track", {}).get("date_released")
        year_r = candidate_md.get("track", {}).get("date_released")

        if isinstance(year_q, str) and isinstance(year_r, str):
            if year_q[:4] == year_r[:4]:
                score += 1.0

        return score

    # ============================================================
    # FUSIÓN AUDIO + METADATA PARA UN QUERY EXISTENTE
    # ============================================================
    def search_by_track(
        self,
        query_track_id: str,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Dado un track_id de consulta:
          1. Busca vecinos por audio (índice invertido).
          2. Recupera metadata del query usando normalización de IDs.
          3. Para cada vecino:
             - Recupera metadata normalizada
             - Calcula score de metadata simple
             - Fusiona: score_final = alpha*audio + (1-alpha)*metadata
        """

        # 1. Buscar en audio
        audio_results = self.audio_backend.search_similar(
            query_track_id, top_k=top_k
        )

        if not audio_results:
            return []

        # 2. Metadata del query (usa normalización interna)
        reference_md = self.metadata_query.get_by_track_id(query_track_id)

        # Si NO hay metadata, seguimos solo con audio (score_metadata = 0)
        if reference_md is None:
            print(
                f"[WARN] Metadata para query_track_id={query_track_id} "
                f"no encontrada. Se usará solo score de audio."
            )

        enriched: List[Dict[str, Any]] = []

        # 3. Integrar metadata en resultados
        for tid, audio_score in audio_results:
            tid_str = str(tid)

            # Metadata del vecino, usando normalización
            candidate_md = self.metadata_query.get_by_track_id(tid_str)

            # score basado en metadata
            md_score = self._metadata_score(candidate_md, reference_md)

            # fusión ponderada
            final_score = self.alpha * float(audio_score) + (1.0 - self.alpha) * md_score

            enriched.append(
                {
                    "track_id": tid_str,
                    "score": float(final_score),
                    "score_audio": float(audio_score),
                    "score_metadata": float(md_score),
                    "title": (
                        candidate_md or {}
                    ).get("track", {}).get("title"),
                    "artist": (
                        candidate_md or {}
                    ).get("artist", {}).get("name"),
                    "genre": (
                        candidate_md or {}
                    ).get("track", {}).get("genre_top"),
                    "year": (
                        candidate_md or {}
                    ).get("track", {}).get("date_released"),
                }
            )

        # 4. Ordenar por score final
        enriched.sort(key=lambda x: x["score"], reverse=True)

        return enriched[:top_k]

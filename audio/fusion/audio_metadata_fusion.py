"""
audio_metadata_fusion.py
------------------------
Módulo que combina resultados de audio (índice invertido o KNN)
con metadata tabular para generar recomendaciones enriquecidas.

score_final = alpha * score_audio + (1 - alpha) * score_metadata
"""

from typing import List, Dict, Any

from fusion.audio_backends import InvertedIndexAudioBackend, normalize_tid
from metadata.metadata_query import MetadataQuery


class AudioMetadataFusion:
    """
    Fusión entre:
        - Búsqueda acústica (audio_backend)
        - Metadata tabular (metadata_query)

    alpha controla el peso del audio.
    """

    def __init__(
        self,
        audio_backend: InvertedIndexAudioBackend,
        metadata_query: MetadataQuery,
        alpha: float = 0.7
    ):
        self.audio_backend = audio_backend
        self.metadata_query = metadata_query
        self.alpha = alpha

    # ============================================================
    # SIMILITUD BASADA EN METADATA (versión simple)
    # ============================================================
    def _metadata_score(self, tid: str, reference_md: Dict[str, Any]) -> float:
        """
        Calcula similitud básica de metadata entre un resultado y la metadata del query.

        Para tu metadata (VERSIÓN C, JSON anidado):
        md["track"]["genre_top"]
        md["track"]["date_released"]
        """
        md = self.metadata_query.table.get(tid)
        if md is None:
            return 0.0

        score = 0.0

        # === Género principal ===
        genre_q = reference_md["track"].get("genre_top")
        genre_r = md["track"].get("genre_top")

        if genre_q is not None and genre_r is not None:
            if genre_q == genre_r:
                score += 1.0

        # === Año (comparamos primeros 4 dígitos) ===
        year_q = reference_md["track"].get("date_released")
        year_r = md["track"].get("date_released")

        if isinstance(year_q, str) and isinstance(year_r, str):
            if year_q[:4] == year_r[:4]:
                score += 1.0

        return score

    # ============================================================
    # BÚSQUEDA FUSIONADA
    # ============================================================
    def search_by_track(
        self, query_track_id: str, top_k: int = 10
    ) -> List[Dict[str, Any]]:

        # ------------------------------------------------------------
        # 1. Normalizamos track_id de consulta
        # ------------------------------------------------------------
        qid_norm = normalize_tid(query_track_id)

        # ------------------------------------------------------------
        # 2. Buscar en audio
        # ------------------------------------------------------------
        audio_results = self.audio_backend.search_similar(qid_norm, top_k=top_k)
        if not audio_results:
            return []

        # ------------------------------------------------------------
        # 3. Obtener metadata del track consulta
        # ------------------------------------------------------------
        reference_md = self.metadata_query.table.get(qid_norm)
        if reference_md is None:
            raise ValueError(
                f"La metadata del track {query_track_id} (normalizado: {qid_norm}) "
                "no está en PARSED_METADATA."
            )

        enriched = []

        # ------------------------------------------------------------
        # 4. Enriquecer resultados con metadata
        # ------------------------------------------------------------
        for tid_raw, audio_score in audio_results:

            tid = normalize_tid(tid_raw)
            md = self.metadata_query.table.get(tid, {})

            # Score de metadata
            md_score = self._metadata_score(tid, reference_md)

            # Fusión ponderada
            final_score = self.alpha * audio_score + (1 - self.alpha) * md_score

            enriched.append({
                "track_id": tid,
                "score": float(final_score),
                "score_audio": float(audio_score),
                "score_metadata": float(md_score),
                "title": md.get("track", {}).get("title"),
                "artist": md.get("artist", {}).get("name"),
                "genre": md.get("track", {}).get("genre_top"),
                "year": md.get("track", {}).get("date_released"),
            })

        # ------------------------------------------------------------
        # 5. Ordenar por score final
        # ------------------------------------------------------------
        enriched.sort(key=lambda x: x["score"], reverse=True)

        return enriched[:top_k]

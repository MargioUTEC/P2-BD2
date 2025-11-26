"""
audio_metadata_fusion.py
------------------------
Fusión entre:
 - backend de audio (InvertedIndexAudioBackend o similar)
 - metadata en SQLite (MetadataSQLite)

score_final = alpha * score_audio + (1 - alpha) * score_metadata
"""

from typing import List, Dict, Any, Optional

from audio.fusion.audio_backends import InvertedIndexAudioBackend
from audio.metadata.metadata_sqlite import MetadataSQLite


class AudioMetadataFusion:
    def __init__(
        self,
        audio_backend: InvertedIndexAudioBackend,
        metadata_db: MetadataSQLite,
        alpha: float = 0.7,
    ) -> None:
        self.audio_backend = audio_backend
        self.metadata_db = metadata_db
        self.alpha = alpha  # peso del score de audio vs metadata

    # ==========================
    # MÉTRICA SIMPLE DE METADATA
    # ==========================

    def _metadata_score(
        self,
        cand_md: Optional[Dict[str, Any]],
        ref_md: Optional[Dict[str, Any]],
    ) -> float:
        """
        Similitud muy simple entre dos registros de metadata planos:
          +1 si coincide el género
          +1 si coincide el año
        """
        if not cand_md or not ref_md:
            return 0.0

        score = 0.0

        # Género
        g_c = cand_md.get("genre")
        g_r = ref_md.get("genre")
        if g_c and g_r and g_c == g_r:
            score += 1.0

        # Año
        y_c = cand_md.get("year")
        y_r = ref_md.get("year")
        if y_c and y_r and y_c == y_r:
            score += 1.0

        return score

    # ==========================
    # FUSIÓN
    # ==========================

    def search_by_track(
        self,
        query_track_id: str,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:

        # 1) Resultados de audio
        audio_results = self.audio_backend.search_similar(
            query_track_id, top_k=top_k
        )

        if not audio_results:
            return []

        # 2) Metadata del track de consulta
        ref_md = self.metadata_db.get_by_track_id(query_track_id)
        if ref_md is None:
            # No hay metadata del query → solo audio, pero igual intentamos
            # agregar metadata para los vecinos si existe.
            print(
                f"[WARN] Metadata para query_track_id={query_track_id} no encontrada. "
                f"Se usará solo score de audio."
            )

        enriched: List[Dict[str, Any]] = []

        for tid, audio_score in audio_results:
            tid_str = str(tid)

            cand_md = self.metadata_db.get_by_track_id(tid_str)

            md_score = self._metadata_score(cand_md, ref_md)

            final_score = self.alpha * float(audio_score) + (1.0 - self.alpha) * md_score

            enriched.append(
                {
                    "track_id": tid_str,
                    "score": float(final_score),
                    "score_audio": float(audio_score),
                    "score_metadata": float(md_score),
                    "title": cand_md.get("title") if cand_md else None,
                    "artist": cand_md.get("artist") if cand_md else None,
                    "genre": cand_md.get("genre") if cand_md else None,
                    "year": cand_md.get("year") if cand_md else None,
                }
            )

        enriched.sort(key=lambda x: x["score"], reverse=True)
        return enriched[:top_k]

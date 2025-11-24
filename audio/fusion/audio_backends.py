from __future__ import annotations

"""
audio_backends.py
-----------------

Adaptadores para usar tu infraestructura de búsqueda por audio
como "backends" genéricos que luego se combinan con metadata.

Corrección clave:
- Normalización consistente de track_id → str(int(track_id))
  para eliminar padding como '034996'.
"""

import os
from typing import List, Tuple
import numpy as np

from config import HIST_DIR
from index.inverted.search_inverted import InvertedIndexSearch
from index.sequential.knn_sequential import KNNSequential


# ============================================================
# UTILIDAD: Normalizar track_id
# ============================================================

def normalize_tid(tid: str | int) -> str:
    """
    Forzamos a que todos los track_id usen el formato sin padding:
        '034996'  -> '34996'
        '000012'  -> '12'
    """
    try:
        return str(int(tid))
    except:
        return str(tid)


# ============================================================
# UTILIDAD: cargar histograma de un track (robusto)
# ============================================================

def load_histogram(track_id: str, hist_dir: str = HIST_DIR) -> np.ndarray:
    """
    Carga el histograma .npy correspondiente a un track_id desde HIST_DIR.

    Corrección: intenta cargar tanto '<tid>.npy' como '<tid padded>.npy'
    si existe divergencia entre audio y metadata.
    """
    tid_norm = normalize_tid(track_id)
    direct_path = os.path.join(hist_dir, f"{tid_norm}.npy")
    padded_path = os.path.join(hist_dir, f"{track_id}.npy")

    # 1. Intentar con el normalizado
    if os.path.exists(direct_path):
        return np.load(direct_path)

    # 2. Intentar con el padding original (034996.npy)
    if os.path.exists(padded_path):
        return np.load(padded_path)

    # Falló → error claro
    raise FileNotFoundError(
        f"No se encontró histograma para track_id={track_id}.\n"
        f"Buscado en:\n"
        f" - {direct_path}\n"
        f" - {padded_path}\n"
        f"Asegúrate de haber generado los histogramas."
    )


# ============================================================
# BACKEND: ÍNDICE INVERTIDO ACÚSTICO
# ============================================================

class InvertedIndexAudioBackend:
    """
    Backend de búsqueda de audio basado en índice invertido acústico.
    """

    def __init__(self, hist_dir: str = HIST_DIR):
        self.hist_dir = hist_dir
        self.search_engine = InvertedIndexSearch()

    def search_similar(self, query_track_id: str, top_k: int = 50) -> List[Tuple[str, float]]:
        """
        Búsqueda usando índice invertido.
        """
        tid_norm = normalize_tid(query_track_id)
        query_hist = load_histogram(query_track_id, self.hist_dir)

        raw_results = self.search_engine.search(query_hist, k=top_k + 1)

        out: List[Tuple[str, float]] = []
        for audio_id, sim in raw_results:
            audio_norm = normalize_tid(audio_id)

            # filtramos el propio track
            if audio_norm == tid_norm:
                continue

            out.append((audio_norm, float(sim)))

        return out[:top_k]


# ============================================================
# BACKEND: KNN SECUENCIAL
# ============================================================

class KNNSequentialAudioBackend:
    """
    Backend de búsqueda de audio basado en KNN secuencial.
    """

    def __init__(self, hist_dir: str = HIST_DIR):
        self.hist_dir = hist_dir
        self.knn = KNNSequential(hist_dir=hist_dir)

    def search_similar(self, query_track_id: str, top_k: int = 50) -> List[Tuple[str, float]]:
        """
        Búsqueda usando KNN secuencial.
        """
        tid_norm = normalize_tid(query_track_id)
        query_hist = load_histogram(query_track_id, self.hist_dir)

        raw_results = self.knn.query(query_hist, k=top_k + 1)

        out: List[Tuple[str, float]] = []

        for sim, tid in raw_results:
            tid_norm_res = normalize_tid(tid)

            if tid_norm_res == tid_norm:
                continue

            out.append((tid_norm_res, float(sim)))

        # Orden descendente
        out.sort(key=lambda x: x[1], reverse=True)

        return out[:top_k]

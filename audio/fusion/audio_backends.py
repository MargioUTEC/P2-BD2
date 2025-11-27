from __future__ import annotations

"""
audio_backends.py
-----------------

Backends de búsqueda de audio (índice invertido y KNN secuencial)
con normalización correcta y consistente de track_id.

Corrección crítica:
- Eliminado el uso de `str(int(tid))` (que recortaba dígitos).
- Implementado formato SIEMPRE de 6 dígitos → f"{id:06d}".
"""

import os
from typing import List, Tuple
import numpy as np

from audio.config import HIST_DIR
from audio.index.inverted.search_inverted import InvertedIndexSearch
from audio.index.sequential.knn_sequential import KNNSequential


# ============================================================
# NORMALIZACIÓN CONSISTENTE DE TRACK_ID (SIEMPRE 6 DÍGITOS)
# ============================================================

def normalize_tid(tid: str | int) -> str:
    """
    Normaliza track_id a EXACTAMENTE 6 dígitos.
    Esto evita errores de padding y garantiza que:
    - Los histogramas .npy matchean.
    - La metadata matchea.
    - Los índices (B+-Tree, invertido, secuencial) sean consistentes.

    Ejemplos:
        "34996"   → "034996"
        "000012"  → "000012"
        "123456"  → "123456"
        "12"      → "000012"
    """
    try:
        tid_int = int(str(tid).strip())
        return f"{tid_int:06d}"
    except:
        # fallback seguro si viene algo extraño
        tid_str = str(tid).strip()
        return tid_str.zfill(6)


# ============================================================
# UTILIDAD: Cargar histograma
# ============================================================

def load_histogram(track_id: str, hist_dir: str = HIST_DIR) -> np.ndarray:
    """
    Carga el histograma .npy correspondiente a un track_id desde HIST_DIR.

    Lógica:
    1. Normaliza SIEMPRE a 6 dígitos.
    2. Intenta cargar "<tid_norm>.npy".
    3. Si falla, intenta "<tid_original>.npy" por seguridad.
    """

    tid_norm = normalize_tid(track_id)

    # Histograma con ID normalizado de 6 dígitos
    path_norm = os.path.join(hist_dir, f"{tid_norm}.npy")

    # Histograma con el ID original (por compatibilidad)
    path_raw = os.path.join(hist_dir, f"{track_id}.npy")

    # 1. priorizar el ID normalizado
    if os.path.exists(path_norm):
        return np.load(path_norm)

    # 2. fallback: intentar el ID tal cual estaba
    if os.path.exists(path_raw):
        return np.load(path_raw)

    # 3. Error claro
    raise FileNotFoundError(
        f"No se encontró histograma para track_id={track_id}.\n"
        f"Buscado en:\n"
        f" - {path_norm}\n"
        f" - {path_raw}\n"
        f"Verifica que los histogramas fueron generados correctamente."
    )


# ============================================================
# BACKEND: ÍNDICE INVERTIDO ACÚSTICO
# ============================================================

class InvertedIndexAudioBackend:
    """
    Backend de búsqueda basado en índice invertido acústico.
    """

    def __init__(self, hist_dir: str = HIST_DIR):
        self.hist_dir = hist_dir
        self.search_engine = InvertedIndexSearch()

    def search_similar(self, query_track_id: str, top_k: int = 50) -> List[Tuple[str, float]]:
        """
        Realiza búsqueda de similitud usando índice invertido.

        Retorna:
            Lista de tuplas (track_id_normalizado, similitud)
        """
        tid_query = normalize_tid(query_track_id)
        query_hist = load_histogram(query_track_id, self.hist_dir)

        raw_results = self.search_engine.search(query_hist, k=top_k + 1)

        out: List[Tuple[str, float]] = []

        for audio_id, sim in raw_results:
            tid_res = normalize_tid(audio_id)

            # Filtrar el propio track consultado
            if tid_res == tid_query:
                continue

            out.append((tid_res, float(sim)))

        return out[:top_k]


# ============================================================
# BACKEND: KNN SECUENCIAL
# ============================================================

class KNNSequentialAudioBackend:
    """
    Backend de búsqueda basado en KNN secuencial.
    """

    def __init__(self, hist_dir: str = HIST_DIR):
        self.hist_dir = hist_dir
        self.knn = KNNSequential(hist_dir=hist_dir)

    def search_similar(self, query_track_id: str, top_k: int = 50) -> List[Tuple[str, float]]:
        """
        Realiza búsqueda de similitud usando KNN secuencial.
        """
        tid_query = normalize_tid(query_track_id)
        query_hist = load_histogram(query_track_id, self.hist_dir)

        raw_results = self.knn.query(query_hist, k=top_k + 1)

        out: List[Tuple[str, float]] = []

        for sim, tid in raw_results:
            tid_res = normalize_tid(tid)

            if tid_res == tid_query:
                continue

            out.append((tid_res, float(sim)))

        # Ordenar por similitud descendente
        out.sort(key=lambda x: x[1], reverse=True)

        return out[:top_k]

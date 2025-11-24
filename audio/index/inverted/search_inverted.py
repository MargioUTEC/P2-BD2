"""
search_inverted.py
------------------
Búsqueda eficiente basada en Índice Invertido Acústico (TF-IDF).

Escenario actual del proyecto:
- build_inverted_index.py construye un índice invertido a partir de
  histogramas .npy ya TF-IDF (y normalizados) generados por generate_histograms.py.
- inverted_index.json almacena, por cada codeword, una posting list:
      word_id -> [ { "audio_id": ..., "score": tfidf_wd }, ... ]
- doc_norms.json almacena la norma L2 del vector tf-idf de cada documento.

Este módulo:
- Recibe como entrada un histograma de consulta (vector 1D de longitud K_CODEBOOK),
- Lo normaliza,
- Usa el índice invertido para acumular productos escalares parciales,
- Normaliza por las normas de los documentos -> similitud tipo coseno,
- Devuelve el Top-K como lista de (audio_id, similitud).
"""

import os
import json
import numpy as np
from heapq import heappush, heappop

from audio.config import (
    INDEX_INV_DIR,
    K_CODEBOOK
)


class InvertedIndexSearch:
    def __init__(self):
        print("[INFO] Cargando índice invertido...")

        index_path = os.path.join(INDEX_INV_DIR, "inverted_index.json")
        norms_path = os.path.join(INDEX_INV_DIR, "doc_norms.json")

        if not os.path.exists(index_path):
            raise FileNotFoundError(
                f"No se encontró {index_path}. Ejecuta build_inverted_index.py primero."
            )

        if not os.path.exists(norms_path):
            raise FileNotFoundError(
                f"No se encontró {norms_path}. Ejecuta build_inverted_index.py primero."
            )

        with open(index_path, "r") as f:
            self.inverted_index = json.load(f)

        with open(norms_path, "r") as f:
            self.doc_norms = json.load(f)

        print("[OK] Índice invertido cargado.")

    # ================================================================
    # Utilidad: normalizar vector de consulta
    # ================================================================
    def _normalize_query(self, hist_vector: np.ndarray):
        """
        Recibe un histograma 1D (longitud K_CODEBOOK),
        lo convierte a float, revisa tamaño y devuelve
        (vector_normalizado, norma_original).
        """
        hist_vector = np.asarray(hist_vector, dtype=float)

        # Asegurarnos de que sea 1D
        if hist_vector.ndim > 1:
            hist_vector = hist_vector.ravel()

        if hist_vector.shape[0] != K_CODEBOOK:
            raise ValueError(
                f"El histograma de consulta tiene tamaño {hist_vector.shape[0]}, "
                f"pero se esperaba K_CODEBOOK={K_CODEBOOK}."
            )

        norm = np.linalg.norm(hist_vector)
        if norm == 0.0:
            # Query sin información
            return hist_vector, 0.0

        q_normed = hist_vector / norm
        return q_normed, norm

    # ================================================================
    # BÚSQUEDA TOP-K POR ÍNDICE INVERTIDO
    # ================================================================
    def search(self, query_hist: np.ndarray, k: int = 5):
        """
        Realiza búsqueda usando el índice invertido.

        Parámetros
        ----------
        query_hist : np.ndarray
            Histograma de consulta (1D, longitud K_CODEBOOK), típicamente uno
            de los .npy en features/histograms/ (TF-IDF+L2).
        k : int
            Número de documentos a retornar.

        Retorna
        -------
        list[tuple[str, float]]
            Lista ordenada de (audio_id, similitud) de mayor a menor similitud.
        """
        print("[INFO] Ejecutando búsqueda por índice invertido...")

        q_vec, q_norm = self._normalize_query(query_hist)
        if q_norm == 0.0:
            # No hay información en el query
            return []

        # índices de palabras activas en el query
        active_words = np.where(q_vec > 0)[0]

        scores = {}  # doc_id -> acumulador de producto escalar

        # Acumular dot product parcial usando posting lists
        for w_idx in active_words:
            w_str = str(int(w_idx))
            q_weight = float(q_vec[w_idx])

            postings = self.inverted_index.get(w_str, [])
            if not postings:
                continue

            for entry in postings:
                doc_id = entry["audio_id"]
                d_weight = float(entry["score"])  # tfidf_wd

                scores.setdefault(doc_id, 0.0)
                scores[doc_id] += q_weight * d_weight

        # Pasar a similitud tipo coseno: sim = dot / (||q|| * ||d||)
        # q ya está normalizado a norma 1, así que ||q|| = 1.
        heap = []

        for doc_id, dot_val in scores.items():
            d_norm = float(self.doc_norms.get(doc_id, 0.0))
            if d_norm <= 0.0:
                continue

            sim = dot_val / d_norm  # ||q|| = 1

            # Mantenemos heap de tamaño K
            heappush(heap, (sim, doc_id))
            if len(heap) > k:
                heappop(heap)

        # Ordenar resultados del más similar al menos similar
        heap.sort(reverse=True, key=lambda x: x[0])

        # Formato de salida esperado por el test: (audio_id, similitud)
        results = [(doc_id, sim) for (sim, doc_id) in heap]

        return results

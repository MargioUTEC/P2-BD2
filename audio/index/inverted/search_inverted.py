# audio/index/inverted/search_inverted.py
"""
search_inverted.py
------------------
Búsqueda eficiente basada en Índice Invertido Acústico (TF–IDF).

Escenario actual del proyecto:
- build_inverted_index.py construye un índice invertido a partir de
  histogramas .npy de CONTEOS (uno por track) generados por generate_histograms.py.
- inverted_index.json almacena, por cada codeword, una posting list:
      term_idx -> [ { "audio_id": ..., "score": tfidf_wd }, ... ]
- doc_norms.json almacena la norma L2 del vector tf-idf de cada documento.
- idf.npy almacena el vector IDF global (longitud K_CODEBOOK).

Este módulo:
- Recibe como entrada un histograma de consulta (vector 1D de longitud K_CODEBOOK),
  con CONTEOS de codewords del audio de consulta.
- Lo convierte a TF–IDF usando el mismo IDF global.
- Normaliza el vector de consulta.
- Usa el índice invertido para acumular productos escalares parciales.
- Normaliza por las normas de los documentos -> similitud tipo coseno.
- Devuelve el Top-K como lista de (audio_id, similitud).
"""

import os
import json
from typing import List, Tuple, Dict, Optional

import numpy as np

from audio.config import INDEX_INV_DIR, K_CODEBOOK, TOP_K


class InvertedIndexSearch:
    """
    Buscador sobre índice invertido acústico basado en TF–IDF.

    Usa:
      - inverted_index.json
      - doc_norms.json
      - idf.npy

    construidos previamente con build_inverted_index.py.
    """

    def __init__(self, index_dir: Optional[str] = None):
        """
        index_dir:
          Carpeta donde se encuentran inverted_index.json, doc_norms.json e idf.npy.
          Si es None, se usa INDEX_INV_DIR de audio.config.
        """
        self.index_dir = index_dir or INDEX_INV_DIR

        self.inverted_index: Dict[str, List[Dict[str, float]]] = {}
        self.doc_norms: Dict[str, float] = {}
        self.idf: np.ndarray = np.empty(K_CODEBOOK, dtype=np.float32)

        self._load_index()

    # ------------------------------------------------------------------
    # Carga de índice
    # ------------------------------------------------------------------
    def _load_index(self):
        """
        Carga inverted_index.json, doc_norms.json e idf.npy desde index_dir.
        """
        index_path = os.path.join(self.index_dir, "inverted_index.json")
        norms_path = os.path.join(self.index_dir, "doc_norms.json")
        idf_path = os.path.join(self.index_dir, "idf.npy")

        if not os.path.exists(index_path):
            raise FileNotFoundError(
                f"No se encontró inverted_index.json en {index_path}. "
                f"Asegúrate de haber ejecutado build_inverted_index.py."
            )
        if not os.path.exists(norms_path):
            raise FileNotFoundError(
                f"No se encontró doc_norms.json en {norms_path}. "
                f"Asegúrate de haber ejecutado build_inverted_index.py."
            )
        if not os.path.exists(idf_path):
            raise FileNotFoundError(
                f"No se encontró idf.npy en {idf_path}. "
                f"Asegúrate de haber ejecutado build_inverted_index.py."
            )

        with open(index_path, "r", encoding="utf-8") as f:
            self.inverted_index = json.load(f)

        with open(norms_path, "r", encoding="utf-8") as f:
            self.doc_norms = json.load(f)

        self.idf = np.load(idf_path).astype(np.float32)

        if self.idf.ndim != 1 or self.idf.size != K_CODEBOOK:
            raise ValueError(
                f"Vector IDF inválido en {idf_path}: se esperaba shape ({K_CODEBOOK},), "
                f"y se obtuvo {self.idf.shape}"
            )

    # ------------------------------------------------------------------
    # Construcción del vector de consulta
    # ------------------------------------------------------------------
    def _build_query_vector(self, hist_vector: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Dado un histograma de CONTEOS (vector 1D de longitud K_CODEBOOK),
        construye el vector TF–IDF normalizado de la consulta.

        Retorna:
          - q_vec: vector TF–IDF normalizado (||q_vec|| = 1).
          - q_norm: norma L2 del vector TF–IDF original antes de normalizar.
        """
        if hist_vector is None:
            raise ValueError("hist_vector de consulta no puede ser None")

        hist_vector = np.asarray(hist_vector, dtype=np.float32)

        if hist_vector.ndim != 1:
            raise ValueError(
                f"Se esperaba hist_vector 1D, pero se recibió shape {hist_vector.shape}"
            )

        if hist_vector.size != K_CODEBOOK:
            raise ValueError(
                f"El hist_vector tiene longitud {hist_vector.size}, "
                f"se esperaba K_CODEBOOK={K_CODEBOOK}"
            )

        total = float(hist_vector.sum())
        if total <= 0.0:
            # Consulta vacía -> no hay información
            return np.zeros(K_CODEBOOK, dtype=np.float32), 0.0

        # TF (frecuencia relativa)
        tf = hist_vector / total  # shape (K_CODEBOOK,)

        # TF–IDF del query usando el mismo IDF que los documentos
        tfidf_q = tf * self.idf  # shape (K_CODEBOOK,)

        q_norm = float(np.linalg.norm(tfidf_q))
        if q_norm <= 0.0:
            # Todas las componentes quedaron a cero
            return np.zeros(K_CODEBOOK, dtype=np.float32), 0.0

        # Vector de consulta normalizado (norma 1)
        q_vec = tfidf_q / q_norm
        return q_vec.astype(np.float32), q_norm

    # ------------------------------------------------------------------
    # Búsqueda
    # ------------------------------------------------------------------
    def search(
        self,
        hist_vector: np.ndarray,
        k: Optional[int] = None,
        min_score: float = 0.0,
    ) -> List[Tuple[str, float]]:
        """
        Realiza la búsqueda dada una consulta en forma de histograma de CONTEOS.

        Parámetros:
          - hist_vector: vector 1D de longitud K_CODEBOOK con conteos por codeword.
          - k: número máximo de resultados a devolver. Si es None, usa TOP_K.
          - min_score: umbral mínimo de similitud coseno para incluir un resultado.

        Retorna:
          Lista de tuplas (audio_id, score), ordenada por score descendente.
        """
        if k is None:
            k = TOP_K

        if k <= 0:
            return []

        # 1. Construir vector de consulta normalizado
        q_vec, q_norm = self._build_query_vector(hist_vector)
        if q_norm <= 0.0:
            # Consulta sin información útil
            return []

        # 2. Acumular productos escalares parciales usando el índice invertido
        scores: Dict[str, float] = {}

        # Usamos solo los términos donde q_vec[j] != 0 para ahorrar trabajo
        nonzero_indices = np.nonzero(q_vec)[0]

        for term_idx in nonzero_indices:
            w_q = float(q_vec[term_idx])  # peso de la consulta (ya normalizada)
            term_key = str(int(term_idx))

            postings = self.inverted_index.get(term_key)
            if not postings:
                continue

            for posting in postings:
                audio_id = posting["audio_id"]
                w_d = float(posting["score"])  # tfidf_j del documento

                # Acumulamos q_vec · d (producto escalar no normalizado por ||d||)
                scores[audio_id] = scores.get(audio_id, 0.0) + w_q * w_d

        if not scores:
            return []

        # 3. Convertir a similitud coseno: cos(q, d) = (q_vec · d) / ||d||
        results: List[Tuple[str, float]] = []
        for audio_id, num in scores.items():
            doc_norm = float(self.doc_norms.get(audio_id, 0.0))
            if doc_norm <= 0.0:
                continue

            score = num / doc_norm  # cos(q, d)
            if score >= min_score:
                results.append((audio_id, score))

        # 4. Ordenar por score descendente y cortar top-k
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:k]

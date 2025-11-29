import os
import numpy as np
from heapq import heappush, heappop
from typing import Dict, List, Tuple
from audio.config import HIST_DIR, INDEX_INV_DIR, K_CODEBOOK, TOP_K


class KNNSequential:
    def __init__(
        self,
        hist_dir: str = HIST_DIR,
        idf_path: str | None = None,
        histograms: list[tuple[str, np.ndarray]] | None = None,
        max_files: int | None = None,
    ):
        """
        hist_dir:
            Directorio con histogramas .npy (solo se usa si ``histograms`` es None).
        idf_path:
            Ruta al vector IDF precomputado.
        histograms:
            Lista opcional de pares (track_id, hist_vector). Si se provee, se usa
            directamente y se evita recorrer el disco.
        max_files:
            Límite opcional de histogramas a cargar desde ``hist_dir``.
        """

        self.hist_dir = hist_dir

        self.idf_path = idf_path or os.path.join(INDEX_INV_DIR, "idf.npy")
        self.max_files = max_files

        self.idf_vector: np.ndarray = np.zeros(K_CODEBOOK, dtype=np.float32)
        self.database: Dict[str, np.ndarray] = {}  # { track_id: tfidf_normalized }

        self._load_idf()

        if histograms is not None:
            self._load_from_memory(histograms)
        else:
            self._load_histograms()


    def _load_histograms(self):
        print(f"[INFO] Cargando histogramas desde: {self.hist_dir}")

        if not os.path.exists(self.hist_dir):
            raise FileNotFoundError(f"No existe el directorio de histogramas: {self.hist_dir}")
        
        loaded = 0

        for root, _, files in os.walk(self.hist_dir):
            for file in sorted(files):
                if not file.endswith(".npy"):
                    continue

                track_id = os.path.splitext(file)[0]
                hist_path = os.path.join(root, file)
                hist = self._load_histogram(hist_path)

                tfidf_vec = self._build_tfidf_vector(hist)
                if tfidf_vec is None:
                    continue

                self.database[track_id] = tfidf_vec
                loaded += 1

                if self.max_files is not None and loaded >= self.max_files:
                    break

            if self.max_files is not None and loaded >= self.max_files:
                break

        print(f"[OK] Histogramas cargados: {len(self.database)}")

    def _load_from_memory(self, histograms: list[tuple[str, np.ndarray]]):
        """
        Construye la base desde una lista de (track_id, hist_vector) ya en memoria.
        """

        for track_id, hist in histograms:
            tfidf_vec = self._build_tfidf_vector(np.asarray(hist, dtype=np.float32))
            if tfidf_vec is None:
                continue

            self.database[str(track_id)] = tfidf_vec

        print(f"[OK] Histogramas cargados (memoria): {len(self.database)}")


#Carga de IDF
    def _load_idf(self):
        """Carga el vector IDF previo para el codebook"""

        if not os.path.exists(self.idf_path):
            raise FileNotFoundError(
                f"No se encontró el archivo de IDF en {self.idf_path}. "
                "Ejecuta primero build_inverted_index.py para generarlo."
            )

        idf = np.load(self.idf_path).astype(np.float32)
        if idf.ndim != 1 or idf.size != K_CODEBOOK:
            raise ValueError(
                f"Vector IDF inválido: se esperaba shape ({K_CODEBOOK},) y se obtuvo {idf.shape}"
            )

        self.idf_vector = idf

    # Utilidades de carga/transformación
    @staticmethod
    def _load_histogram(path: str) -> np.ndarray:
        """Carga un histograma y valida su formato (vector 1D)."""

        hist = np.load(path)
        if hist.ndim != 1:
            raise ValueError(
                f"Histograma inválido en {path}, se esperaba vector 1D y se obtuvo {hist.shape}"
            )
        if hist.size != K_CODEBOOK:
            raise ValueError(
                f"Histograma en {path} tiene longitud {hist.size}, se esperaba {K_CODEBOOK}"
            )
        return hist.astype(np.float32)

    def _build_tfidf_vector(self, hist: np.ndarray) -> np.ndarray | None:
        """
        Convierte un histograma de conteos en un vector TF–IDF normalizado.
        Si sum <= 0 o el vector queda degenerado, retorna None.
        """

        total = float(hist.sum())
        if total <= 0.0:
            return None

        tf = hist / total
        tfidf = tf * self.idf_vector

        norm = float(np.linalg.norm(tfidf))
        if norm <= 0.0:
            return None

        return (tfidf / norm).astype(np.float32)





    @staticmethod
    def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calcula la similitud coseno entre dos vectores normalizados."""

        if vec1.size != vec2.size:
            raise ValueError(
                f"Los vectores no tienen la misma dimensión: {vec1.shape} vs {vec2.shape}"
            )

        dot = float(np.dot(vec1, vec2))
        return dot

    # Búsqueda KNN secuencial con tf-idf y coseno.
    def query(self, query_hist: np.ndarray, k: int = TOP_K) -> List[Tuple[str, float]]:
        if k <= 0:
            return []

        query_tfidf = self._build_tfidf_vector(np.asarray(query_hist, dtype=np.float32))
        if query_tfidf is None:
            return []

        heap: List[Tuple[float, str]] = []

        for track_id, hist in self.database.items():
            sim = KNNSequential.cosine_similarity(query_tfidf, hist)

            heappush(heap, (sim, track_id))

            if len(heap) > k:
                heappop(heap)

        heap.sort(reverse=True, key=lambda x: x[0])

        return [(track_id, sim) for sim, track_id in heap]

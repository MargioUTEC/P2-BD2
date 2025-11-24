import os
import numpy as np
from heapq import heappush, heappop
from sklearn.preprocessing import normalize
from audio.config import HIST_DIR


class KNNSequential:
    """
    Implementación de KNN secuencial basada en histogramas de palabras acústicas.

    - Carga todos los histogramas desde features/histograms/
    - Normaliza vectores (L2)
    - Calcula la similitud de coseno
    - Usa un heap para mantener los K más similares
    """

    def __init__(self, hist_dir=HIST_DIR):
        self.hist_dir = hist_dir
        self.database = {}  # { track_id: hist_vector }
        self._load_histograms()

    # ----------------------------------------------------------------------
    # Cargar histogramas desde disco
    # ----------------------------------------------------------------------
    def _load_histograms(self):
        print(f"[INFO] Cargando histogramas desde: {self.hist_dir}")

        for file in os.listdir(self.hist_dir):
            if file.endswith(".npy"):
                track_id = file.replace(".npy", "")
                hist_path = os.path.join(self.hist_dir, file)
                hist = np.load(hist_path)

                # Normalizar cada histograma (L2)
                hist = normalize(hist.reshape(1, -1))[0]

                self.database[track_id] = hist

        print(f"[OK] Histogramas cargados: {len(self.database)}")

    # ----------------------------------------------------------------------
    # Similaridad de coseno
    # ----------------------------------------------------------------------
    @staticmethod
    def cosine_similarity(vec1, vec2):
        """Compute cosine similarity between two vectors."""
        dot = np.dot(vec1, vec2)
        norm = np.linalg.norm(vec1) * np.linalg.norm(vec2)
        if norm == 0:
            return 0.0
        return dot / norm

    # ----------------------------------------------------------------------
    # Búsqueda KNN secuencial
    # ----------------------------------------------------------------------
    def query(self, query_hist, k=5):
        print("[INFO] Ejecutando KNN secuencial...")

        query_hist = normalize(query_hist.reshape(1, -1))[0]
        heap = []

        for track_id, hist in self.database.items():
            sim = KNNSequential.cosine_similarity(query_hist, hist)

            heappush(heap, (sim, track_id))

            if len(heap) > k:
                heappop(heap)

        heap.sort(reverse=True, key=lambda x: x[0])

        return heap


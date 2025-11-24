"""
audio_search_controller.py
--------------------------

Controlador principal para búsqueda de audios combinando:

1. KNN secuencial (similitud de histogramas MFCC)
2. Índice invertido TF-IDF (búsqueda eficiente)
3. Metadata → B+Tree
4. FusionEngine → Combina puntajes (audio + metadata)
5. API de alto nivel → search(query_audio_id, method="hybrid")

Este módulo es el que usará el frontend o notebook.
"""

import os
import numpy as np
from typing import List, Dict, Tuple

# Motores de búsqueda
from audio.index.sequential.knn_sequential import KNNSequential
from audio.index.inverted.search_inverted import InvertedIndexSearch

# Metadata
from metadata.metadata_query import MetadataQuery

# Motor de fusión
from fusion.fusion_engine import FusionEngine

# Config
from config import HIST_DIR, MFCC_DIR


class AudioSearchController:
    """
    Clase principal que expone TODOS los métodos de búsqueda.
    Esta es la capa donde debe conectarse tu frontend o API REST.
    """

    def __init__(self):
        print("\n=== Inicializando AudioSearchController ===")

        # -----------------------------
        # Motores individuales
        # -----------------------------
        print("[INIT] Cargando KNN secuencial…")
        self.knn = KNNSequential()

        print("[INIT] Cargando índice invertido…")
        self.inverted = InvertedIndexSearch()

        print("[INIT] Cargando B+Tree de metadata…")
        self.metadata = MetadataQuery()

        print("[INIT] Cargando motor de fusión…")
        self.fusion = FusionEngine()

        print("[OK] Todos los módulos cargados.\n")

    # ===============================================================
    # Utilidades internas
    # ===============================================================

    def _load_histogram(self, audio_id: str):
        """
        Carga el histograma TF-IDF ya generado.
        """
        path = os.path.join(HIST_DIR, f"{audio_id}.npy")
        if not os.path.exists(path):
            raise FileNotFoundError(f"No existe histograma para {audio_id}")
        return np.load(path)

    def _load_mfcc(self, audio_id: str):
        """
        Carga los MFCC originales del audio.
        """
        path = os.path.join(MFCC_DIR, f"{audio_id}.npy")
        if not os.path.exists(path):
            raise FileNotFoundError(f"No existe MFCC para {audio_id}")
        return np.load(path)

    # ===============================================================
    # Métodos de búsqueda independientes
    # ===============================================================

    def search_knn(self, audio_id: str, k: int = 10):
        """Búsqueda usando solo KNN secuencial."""
        hist = self._load_histogram(audio_id)
        return self.knn.query(hist, k)

    def search_inverted(self, audio_id: str, k: int = 10):
        """Búsqueda usando índice invertido TF-IDF."""
        hist = self._load_histogram(audio_id)
        mfcc = self._load_mfcc(audio_id)
        return self.inverted.search(mfcc, k)

    def search_metadata(self, key: str, value):
        """Consultas de metadata con B+Tree."""
        return self.metadata.search(key, value)

    # ===============================================================
    # BÚSQUEDA HÍBRIDA (AUDIO + METADATA)
    # ===============================================================

    def search_hybrid(
        self,
        audio_id: str,
        k: int = 10,
        metadata_filters: Dict[str, str] = None,
        audio_weight: float = 0.7,
        metadata_weight: float = 0.3,
    ):
        """
        Realiza una búsqueda híbrida:
        - Primero obtiene candidatos por audio (inverted index)
        - Luego filtra y reordena según metadata
        - Finalmente aplica fusión multimodal de scores
        """

        print("[INFO] Ejecutando búsqueda híbrida…")

        # 1) Obtener candidatos por audio
        audio_candidates = self.search_inverted(audio_id, k=50)

        # 2) Si hay filtros de metadata, consultarlos
        if metadata_filters:
            meta_candidates = set()
            for key, val in metadata_filters.items():
                results = self.metadata.search(key, val)
                meta_candidates.update([r["track_id"] for r in results])
        else:
            meta_candidates = None  # no filtrar

        # 3) Fusionar resultados
        fused = self.fusion.combine_scores(
            audio_id=audio_id,
            audio_candidates=audio_candidates,
            metadata_candidates=meta_candidates,
            audio_weight=audio_weight,
            metadata_weight=metadata_weight,
            top_k=k
        )

        return fused

    # ===============================================================
    # API pública para el frontend
    # ===============================================================

    def search(
        self,
        audio_id: str,
        mode: str = "hybrid",
        k: int = 10,
        metadata_filters: Dict[str, str] = None
    ):
        """
        Punto de entrada principal de búsqueda.
        mode: "knn", "inverted", "metadata", "hybrid"
        """

        mode = mode.lower()

        if mode == "knn":
            return self.search_knn(audio_id, k)

        if mode == "inverted":
            return self.search_inverted(audio_id, k)

        if mode == "metadata":
            if not metadata_filters:
                raise ValueError("metadata_filters es obligatorio para modo 'metadata'")
            return self.search_metadata(**metadata_filters)

        if mode == "hybrid":
            return self.search_hybrid(
                audio_id=audio_id,
                k=k,
                metadata_filters=metadata_filters
            )

        raise ValueError(f"Modo de búsqueda desconocido: {mode}")


# ===============================================================
# Ejemplo rápido si se ejecuta por terminal
# ===============================================================
if __name__ == "__main__":
    controller = AudioSearchController()
    results = controller.search("000001", mode="hybrid", k=5)
    print("\nTOP 5 RESULTADOS HÍBRIDOS:")
    for r in results:
        print(r)

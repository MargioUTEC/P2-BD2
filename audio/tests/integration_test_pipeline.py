"""
integration_test_pipeline.py
----------------------------
Prueba integral de toda la tubería del proyecto:

1. MFCC → Histogramas → Codebook
2. Índice invertido acústico
3. Índice metadata B+Tree
4. Motor de fusión (audio + metadata)
5. Controlador de búsquedas

El propósito de este test es validar que todos los módulos
funcionan de extremo a extremo en una búsqueda real.
"""

import os
import random
import numpy as np

# ==============================
# IMPORTAR MÓDULOS DEL PROYECTO
# ==============================

from scripts.generate_histograms import load_all_mfcc_paths
from index.sequential.knn_sequential import KNNSequential
from index.inverted.search_inverted import InvertedIndexSearch

from metadata.metadata_index_bptree import MetadataBPlusTree
from metadata.metadata_query import MetadataQuery
from fusion.fusion_engine import FusionEngine
from controller.audio_search_controller import AudioSearchController

from config import HIST_DIR
from config_metadata import METADATA_DIR


# =========================================================
# FUNCIÓN PRINCIPAL DE PRUEBA
# =========================================================

def main():
    print("\n========== TEST INTEGRADO COMPLETO ==========\n")

    # ======================================================
    # 0. Seleccionar un audio al azar del set
    # ======================================================
    hist_files = [f for f in os.listdir(HIST_DIR) if f.endswith(".npy")]

    if not hist_files:
        raise RuntimeError("No existen histogramas en features/histograms.")

    query_file = random.choice(hist_files)
    audio_id_query = query_file.replace(".npy", "")
    query_hist = np.load(os.path.join(HIST_DIR, query_file))

    print(f"Audio seleccionado como consulta → {audio_id_query}")
    print(f"Shape histograma: {query_hist.shape}")
    print("\n---------------------------------------------\n")

    # ======================================================
    # 1. Inicializar motores de búsqueda
    # ======================================================

    print("Cargando KNN secuencial...")
    knn = KNNSequential()

    print("Cargando buscador de índice invertido...")
    inv = InvertedIndexSearch()

    print("Cargando índice B+Tree de metadata...")
    meta_index = MetadataBPlusTree()

    print("Inicializando motor de queries metadata...")
    meta_query = MetadataQuery(meta_index)

    print("Inicializando motor de fusión...")
    fusion = FusionEngine()

    print("Inicializando controlador global de búsqueda...")
    controller = AudioSearchController(
        knn_search=knn,
        inverted_search=inv,
        metadata_query=meta_query,
        fusion_engine=fusion
    )

    print("\n---------------------------------------------\n")

    # ======================================================
    # 2. Ejecutar búsqueda final unificada
    # ======================================================

    print("Ejecutando búsqueda global unificada...\n")

    results = controller.search(
        audio_id_query=audio_id_query,
        query_hist=query_hist,
        top_k=10,
        metadata_filters={
            "genre": "Electronic"      # Ejemplo opcional
        },
        fusion_weights={
            "audio": 0.7,
            "metadata": 0.3
        }
    )

    print("\n========== RESULTADOS FINALES ==========\n")

    for rank, (track_id, score) in enumerate(results, start=1):
        print(f"{rank:2d}. {track_id}   score={score:.4f}")

    print("\nTEST INTEGRADO COMPLETADO CON ÉXITO.\n")


# =========================================================
# EJECUCIÓN DIRECTA
# =========================================================

if __name__ == "__main__":
    main()

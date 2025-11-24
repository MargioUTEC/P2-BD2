# proyecto_2/tests/test_search_inverted.py

import os
import json
import random
import numpy as np

from config import (
    INDEX_INV_DIR,
    HIST_DIR,
    K_CODEBOOK
)

# Importa el módulo que vamos a probar
from index.inverted.search_inverted import InvertedIndexSearch


def main():
    print("=== TEST: BÚSQUEDA CON ÍNDICE INVERTIDO ===\n")

    index_path = os.path.join(INDEX_INV_DIR, "inverted_index.json")
    norms_path = os.path.join(INDEX_INV_DIR, "doc_norms.json")

    # 1. Verificar que el índice existe
    if not os.path.exists(index_path):
        raise FileNotFoundError(
            f"No se encontró el archivo {index_path}\n"
            "Ejecuta build_inverted_index.py antes."
        )
    if not os.path.exists(norms_path):
        raise FileNotFoundError(
            f"No se encontró el archivo {norms_path}\n"
            "Ejecuta build_inverted_index.py antes."
        )

    print("Índice invertido ubicado correctamente.")
    print(f"- {index_path}")
    print(f"- {norms_path}\n")

    # 2. Cargar buscador
    print("Cargando searcher...")
    searcher = InvertedIndexSearch()
    print("OK — Searcher cargado.\n")

    # 3. Seleccionar histograma aleatorio de consulta
    hist_files = [f for f in os.listdir(HIST_DIR) if f.endswith(".npy")]

    if not hist_files:
        raise RuntimeError("No hay histogramas en features/histograms/. Ejecuta generate_histograms.py")

    query_file = random.choice(hist_files)
    query_path = os.path.join(HIST_DIR, query_file)

    query_hist = np.load(query_path)
    audio_id_query = query_file.replace(".npy", "")

    print(f"Archivo de consulta: {query_file}")
    print("Shape del histograma:", query_hist.shape)
    print()

    # 4. Ejecutar búsqueda
    print("Ejecutando búsqueda invertida (k=5)...")
    results = searcher.search(query_hist, k=5)

    # 5. Mostrar resultados
    print("\nResultados:")
    for audio_id, sim in results:
        print(f" - Track {audio_id} | similitud={sim:.4f}")

    # 6. Validaciones básicas
    assert len(results) <= 5, "K debe retornar a lo más 5 elementos."
    assert len(results) > 0, "El índice invertido debe retornar al menos un resultado."

    # Similitudes en rango correcto
    for _, sim in results:
        assert 0 <= sim <= 1, "Similitud fuera del rango esperado [0,1]."

    print("\nTEST ÍNDICE INVERTIDO (BÚSQUEDA) COMPLETADO CON ÉXITO.\n")


if __name__ == "__main__":
    main()

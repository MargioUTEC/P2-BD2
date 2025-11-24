# === TEST: KNN SECUENCIAL ===

import os
import random
import numpy as np
from config import HIST_DIR
from index.sequential.knn_sequential import KNNSequential

def main():
    print("=== TEST: KNN SECUENCIAL ===\n")

    hist_files = [f for f in os.listdir(HIST_DIR) if f.endswith(".npy")]
    print(f"Histogramas encontrados: {len(hist_files)}\n")

    if len(hist_files) == 0:
        raise RuntimeError("No hay histogramas en features/histograms/. Ejecuta generate_histograms.py")

    print("Cargando base de datos de KNNSequential...")
    knn = KNNSequential()
    print(f"Total de items cargados: {len(knn.database)}\n")

    # Elegir archivo de consulta
    query_file = random.choice(hist_files)
    query_path = os.path.join(HIST_DIR, query_file)
    query_hist = np.load(query_path)

    print(f"Archivo de consulta: {query_file}")
    print(f"Shape del histograma: {query_hist.shape}\n")

    print("Ejecutando búsqueda KNN (k=5)...")
    results = knn.query(query_hist, k=5)

    print("\nResultados del KNN:")
    for sim, track_id in results:
        print(f" - Track {track_id} | similitud={sim:.4f}")

    # Verificar que la similitud sea válida
    assert 0.0 <= results[0][0] <= 1.0, "Similitud fuera de rango (0–1)."

    print("\nTEST KNN SECUENCIAL COMPLETADO CON ÉXITO.\n")


if __name__ == "__main__":
    main()

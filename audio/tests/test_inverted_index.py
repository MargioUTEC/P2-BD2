# tests/test_inverted_index.py

import os
import json
import random
import numpy as np

from config import HIST_DIR, INDEX_INV_DIR, K_CODEBOOK
from index.inverted.build_inverted_index import build_inverted_index


def main():
    print("=== TEST: ÍNDICE INVERTIDO ===\n")

    # 1) Verificar existencia de histogramas
    hist_files = [f for f in os.listdir(HIST_DIR) if f.endswith(".npy")]
    print(f"Histogramas encontrados: {len(hist_files)}")

    if len(hist_files) == 0:
        raise RuntimeError("No hay archivos .npy en HIST_DIR. Ejecuta generate_histograms.py")

    # 2) Construir índice invertido
    print("\nConstruyendo índice invertido...\n")
    build_inverted_index()

    # 3) Verificar archivos generados
    index_path = os.path.join(INDEX_INV_DIR, "inverted_index.json")
    norms_path = os.path.join(INDEX_INV_DIR, "doc_norms.json")

    if not os.path.exists(index_path):
        raise FileNotFoundError("ERROR: No se generó inverted_index.json")

    if not os.path.exists(norms_path):
        raise FileNotFoundError("ERROR: No se generó doc_norms.json")

    print("Archivos generados correctamente:")
    print(" -", index_path)
    print(" -", norms_path)

    # 4) Cargar índice y revisar integridad
    with open(index_path, "r") as f:
        index_data = json.load(f)

    with open(norms_path, "r") as f:
        norms_data = json.load(f)

    print("\nValidando integridad del índice...")

    # Verificar número de entradas = K_CODEBOOK
    assert len(index_data) == K_CODEBOOK, "El índice no tiene K_CODEBOOK entradas."

    # Tomar codeword aleatorio
    random_word = str(random.randint(0, K_CODEBOOK - 1))
    posting_list = index_data[random_word]

    print(f"\nEjemplo: codeword {random_word}, postings = {len(posting_list)}")

    if posting_list:
        entry = posting_list[0]
        print("Ejemplo de entrada:", entry)

        assert "audio_id" in entry
        assert "score" in entry

    # Verificar normas
    print("\nValidando normas de documentos...")
    assert len(norms_data) == len(hist_files), "Cantidad de normas no coincide con cantidad de histogramas."

    any_norm = next(iter(norms_data.values()))
    print("Ejemplo de norma:", any_norm)

    assert float(any_norm) >= 0.0, "Norma negativa no permitida."

    print("\nTEST ÍNDICE INVERTIDO COMPLETADO CON ÉXITO.")


if __name__ == "__main__":
    main()

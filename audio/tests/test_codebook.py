# proyecto_2/tests/test_codebook.py

import os
import random
import numpy as np
import joblib

from config import MFCC_DIR, CODEBOOK_DIR, K_CODEBOOK
from codebook.build_codebook import build_codebook


def main():
    print("=== TEST: CONSTRUCCIÓN DEL CODEBOOK ===\n")

    # 1) Verificar que existan MFCC ya generados
    mfcc_files = [f for f in os.listdir(MFCC_DIR) if f.endswith(".npy")]
    print(f"MFCC encontrados: {len(mfcc_files)}")

    if len(mfcc_files) == 0:
        raise RuntimeError(
            "No se encontraron MFCC en MFCC_DIR.\n"
            "Ejecuta test_extract_mfcc primero."
        )

    # 2) Construir el codebook con pocos descriptores (ej: 20,000)
    #    Esto hace el test MUCHO más rápido
    print("\nConstruyendo codebook de prueba...")

    # sample_limit controla cuántos vectores MFCC se usan
    kmeans = build_codebook(
        n_clusters=K_CODEBOOK,
        sample_limit=20000      # <= usa solo 20k MFCC para el test
    )

    # 3) Verificar que el archivo pkl exista
    codebook_path = os.path.join(CODEBOOK_DIR, "codebook_kmeans.pkl")

    if not os.path.isfile(codebook_path):
        raise RuntimeError(" No se generó el archivo del codebook.")

    print(f"\nCodebook generado en: {codebook_path}")

    # 4) Cargarlo para verificar consistencia
    model = joblib.load(codebook_path)

    print("\nInformación del modelo cargado:")
    print(" - Clusters (k):", model.n_clusters)
    print(" - Dimensión de centroides:", model.cluster_centers_.shape)

    assert model.n_clusters == K_CODEBOOK
    assert len(model.cluster_centers_.shape) == 2

    print("\nTEST CODEBOOK COMPLETADO CON ÉXITO.")


if __name__ == "__main__":
    main()

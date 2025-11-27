# proyecto_2/tests/test_histograms.py

import os
import random
import numpy as np

from audio.config import (
    MFCC_DIR,
    HIST_DIR,
    CODEBOOK_DIR,
    K_CODEBOOK
)

from audio.scripts.generate_histograms import main as generate_histograms


def main():
    print("\n=== TEST: GENERACIÓN DE HISTOGRAMAS ===\n")

    # 1) Verificar que existan MFCC previamente generados
    if not os.path.isdir(MFCC_DIR):
        raise FileNotFoundError(
            f"No existe MFCC_DIR: {MFCC_DIR}\nEjecuta antes test_extract_mfcc."
        )

    mfcc_files = [f for f in os.listdir(MFCC_DIR) if f.endswith(".npy")]
    print(f"MFCC encontrados: {len(mfcc_files)}")

    if len(mfcc_files) == 0:
        raise RuntimeError(
            "No hay archivos MFCC. Ejecuta extract_mfcc antes de este test."
        )

    # 2) Verificar que el codebook exista
    codebook_path = os.path.join(CODEBOOK_DIR, "codebook_kmeans.pkl")
    if not os.path.exists(codebook_path):
        raise FileNotFoundError(
            f"No existe el codebook: {codebook_path}\n"
            f"Ejecuta antes test_codebook."
        )

    print("\nGenerando histogramas de prueba...\n")

    # Limpiar carpeta histograms
    os.makedirs(HIST_DIR, exist_ok=True)

    for f in os.listdir(HIST_DIR):
        os.remove(os.path.join(HIST_DIR, f))

    # 3) Ejecutar script de histogramas (usa TF-IDF por defecto)
    generate_histograms(apply_tfidf_flag=True)

    # 4) Verificar que se hayan generado archivos
    hist_files = [f for f in os.listdir(HIST_DIR) if f.endswith(".npy")]
    # Validar que todos los histogramas tengan track_id de 6 dígitos
    for fname in hist_files:
        tid = fname.replace(".npy", "")
        assert len(tid) == 6 and tid.isdigit(), \
            f"track_id inválido: {tid}. Debe tener exactamente 6 dígitos."

    print(f"Histogramas generados: {len(hist_files)}")

    if len(hist_files) == 0:
        raise RuntimeError(
            "No se generaron histogramas. Algo falló en generate_histograms."
        )

    # 5) Cargar uno y revisarlo
    sample_file = random.choice(hist_files)
    sample_path = os.path.join(HIST_DIR, sample_file)

    hist = np.load(sample_path)

    print(f"\nEjemplo: {sample_file}")
    print(f"Shape del histograma: {hist.shape}")
    print(f"Datos (primeros 10 valores): {hist[:10]}")

    # Validaciones importantes
    assert hist.shape == (K_CODEBOOK,), \
        f"El histograma no tiene dimensión correcta: {hist.shape}"

    assert np.isfinite(hist).all(), \
        "El histograma contiene valores NaN o infinitos."

    # Después de TF-IDF + normalización, la norma debe ser ~1
    norm = np.linalg.norm(hist)
    print(f"Norma L2 del histograma: {norm:.4f}")
    assert 0.9 <= norm <= 1.1, \
        f"La norma L2 debería ser ~1 pero es {norm}"

    print("\nTEST HISTOGRAMAS COMPLETADO CON ÉXITO.\n")


if __name__ == "__main__":
    main()

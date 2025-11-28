# test_external_audio_similarity.py

"""
Test de búsqueda de vecinos usando un ARCHIVO DE AUDIO externo.

Uso:
    python test_external_audio_similarity.py ruta/a/mi_audio.mp3

Requisitos:
    - Haber ejecutado antes:
        python build_codebook.py
        python generate_histograms.py
        python build_inverted_index.py
    - Tener:
        * codebook_kmeans.pkl en CODEBOOK_DIR
        * inverted_index.json, doc_norms.json, idf.npy en INDEX_INV_DIR
"""

import sys
import os
import numpy as np

from audio.config import K_CODEBOOK
from audio.index.inverted.search_inverted import InvertedIndexSearch

# Importamos helpers del pipeline actual
from audio.scripts.extract_mfcc import extract_mfcc_from_audio
from audio.scripts.generate_histograms import load_codebook, compute_histogram, normalize_mfcc


def build_query_hist_from_file(audio_path: str) -> np.ndarray:
    """
    Dado un archivo de audio (mp3/wav), construye el histograma de
    CONTEOS crudos, usando el mismo codebook y la misma normalización
    de MFCC que el resto del pipeline.
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"No existe el archivo de audio: {audio_path}")

    print(f"[INFO] Extrayendo MFCC de: {audio_path}")
    mfcc_matrix = extract_mfcc_from_audio(audio_path)

    if mfcc_matrix is None or mfcc_matrix.size == 0:
        raise RuntimeError("MFCC vacío o None al extraer del audio externo.")

    # Normalizar MFCC igual que para los histogramas del dataset
    mfcc_matrix = normalize_mfcc(mfcc_matrix)

    # Cargar codebook
    kmeans = load_codebook()

    # Construir histograma de codewords (conteos)
    hist = compute_histogram(mfcc_matrix, kmeans)

    if hist.ndim != 1 or hist.shape[0] != K_CODEBOOK:
        raise ValueError(
            f"Histograma de query inválido: shape={hist.shape}, "
            f"esperado=({K_CODEBOOK},)"
        )

    print(f"[INFO] Histograma de query construido. Sum={hist.sum():.1f}")
    return hist


def main():
    if len(sys.argv) < 2:
        print("Uso: python test_external_audio_similarity.py ruta/a/mi_audio.mp3")
        sys.exit(1)

    audio_path = sys.argv[1]

    print("\n=== TEST AUDIO SIMILARITY (audio externo) ===\n")
    print(f"Archivo de consulta: {audio_path}\n")

    # 1) Construir histograma del audio externo
    q_hist = build_query_hist_from_file(audio_path)

    # 2) Crear buscador
    searcher = InvertedIndexSearch()

    # 3) Buscar vecinos
    top_k = 10
    results = searcher.search(q_hist, k=top_k)

    if not results:
        print("\n[WARN] No se obtuvieron resultados para este audio.")
        return

    print(f"\nTop-{top_k} vecinos para el archivo externo:\n")
    for rank, (tid, score) in enumerate(results, start=1):
        print(f"{rank:2d}. track_id={tid}  score={score:.4f}")


if __name__ == "__main__":
    main()

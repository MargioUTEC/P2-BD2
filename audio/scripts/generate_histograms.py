# scripts/generate_histograms.py
"""
Generación de histogramas de codewords a partir de MFCC normalizados
con estadísticas globales.

Pipeline:
  1. Cargar MFCC de MFCC_DIR (matrices (n_frames, n_mfcc)).
  2. Normalizar cada matriz MFCC con las stats globales (mfcc_stats.npz).
  3. Asignar cada frame al centroide más cercano del codebook (MiniBatchKMeans).
  4. Construir un histograma de conteos por codeword de tamaño K_CODEBOOK.
  5. Guardar el histograma en HIST_DIR con la misma estructura de subcarpetas.
"""

import os
import numpy as np
from tqdm import tqdm
import joblib

from audio.config import (
    MFCC_DIR,
    HIST_DIR,
    CODEBOOK_DIR,
    K_CODEBOOK,
)


STATS_PATH = os.path.join(CODEBOOK_DIR, "mfcc_stats.npz")
CODEBOOK_PATH = os.path.join(CODEBOOK_DIR, "codebook_kmeans.joblib")


def _iter_mfcc_paths():
    """
    Recorre MFCC_DIR recursivamente y devuelve rutas a archivos .npy de MFCC.
    """
    mfcc_paths = []
    for root, _, files in os.walk(MFCC_DIR):
        for fname in files:
            if fname.lower().endswith(".npy"):
                mfcc_paths.append(os.path.join(root, fname))
    mfcc_paths.sort()
    return mfcc_paths


def _load_mfcc(path: str) -> np.ndarray:
    """
    Carga un archivo .npy de MFCC y valida su forma.
    Esperamos una matriz 2D de shape (n_frames, n_mfcc).
    """
    mfcc = np.load(path)
    if mfcc.ndim != 2:
        raise ValueError(f"MFCC inválido en {path}, se esperaba matriz 2D, got {mfcc.shape}")
    if mfcc.shape[0] == 0:
        raise ValueError(f"MFCC vacío en {path}")
    return mfcc.astype(np.float32)


def _load_global_stats():
    """
    Carga media y desviación estándar globales de MFCC desde STATS_PATH.
    Estas deben haberse guardado en build_codebook.py.
    """
    if not os.path.exists(STATS_PATH):
        raise FileNotFoundError(
            f"No se encontró {STATS_PATH}. "
            f"Primero ejecuta build_codebook.py para generar las estadísticas globales."
        )

    stats = np.load(STATS_PATH)
    mean = stats["mean"].astype(np.float32)
    std = stats["std"].astype(np.float32)
    std[std == 0.0] = 1e-8
    return mean, std


def normalize_mfcc(mfcc_matrix: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    """
    Normaliza una matriz de MFCC (n_frames, n_mfcc) usando media y std globales.

    mean y std son vectores de longitud n_mfcc.
    """
    if mfcc_matrix is None or mfcc_matrix.size == 0:
        return mfcc_matrix
    if mfcc_matrix.ndim != 2:
        raise ValueError(
            f"MFCC inválido, se esperaba matriz 2D y se recibió shape {mfcc_matrix.shape}"
        )

    # Broadcast: (n_frames, n_mfcc) - (1, n_mfcc)
    return (mfcc_matrix - mean[None, :]) / std[None, :]


def _build_histogram(mfcc_matrix: np.ndarray, kmeans) -> np.ndarray:
    """
    Dada una matriz MFCC normalizada (n_frames, n_mfcc), asigna cada frame
    a un codeword y construye un histograma de conteos de tamaño K_CODEBOOK.

    No se normaliza el histograma aquí (se deja en conteos absolutos),
    ya que build_inverted_index.py se encarga de calcular TF / TF-IDF.
    """
    if mfcc_matrix.shape[0] == 0:
        raise ValueError("Matriz MFCC vacía al construir histograma.")

    # labels: shape (n_frames,)
    labels = kmeans.predict(mfcc_matrix)

    # Histograma de conteos por codeword
    hist = np.bincount(labels, minlength=K_CODEBOOK).astype(np.float32)
    return hist


def _hist_path_for_mfcc(mfcc_path: str) -> str:
    """
    Construye la ruta de salida en HIST_DIR correspondiente a un archivo MFCC en MFCC_DIR,
    preservando la estructura de subcarpetas.

    Ejemplo:
        MFCC_DIR = /.../features/mfcc
        mfcc_path = /.../features/mfcc/folder/123.npy

        → HIST_DIR/folder/123.npy
    """
    rel_path = os.path.relpath(mfcc_path, MFCC_DIR)
    rel_dir, fname = os.path.split(rel_path)
    base, _ = os.path.splitext(fname)

    out_dir = os.path.join(HIST_DIR, rel_dir)
    os.makedirs(out_dir, exist_ok=True)

    return os.path.join(out_dir, f"{base}.npy")


def generate_histograms():
    """
    Genera histogramas para todos los archivos MFCC en MFCC_DIR
    y los guarda en HIST_DIR.
    """
    if not os.path.exists(CODEBOOK_PATH):
        raise FileNotFoundError(
            f"No se encontró el codebook en {CODEBOOK_PATH}. "
            f"Primero ejecuta build_codebook.py."
        )

    print(f"[INFO] Cargando codebook desde: {CODEBOOK_PATH}")
    kmeans = joblib.load(CODEBOOK_PATH)

    print(f"[INFO] Cargando estadísticas globales de MFCC desde: {STATS_PATH}")
    mean, std = _load_global_stats()

    mfcc_paths = _iter_mfcc_paths()
    if not mfcc_paths:
        raise RuntimeError(f"No se encontraron archivos .npy en {MFCC_DIR}")

    print(f"[INFO] Generando histogramas para {len(mfcc_paths)} archivos MFCC...\n")

    n_ok = 0
    n_fail = 0

    for mfcc_path in tqdm(mfcc_paths, desc="Histogramas"):
        try:
            mfcc = _load_mfcc(mfcc_path)
            mfcc_norm = normalize_mfcc(mfcc, mean, std)
            hist = _build_histogram(mfcc_norm, kmeans)

            out_path = _hist_path_for_mfcc(mfcc_path)
            np.save(out_path, hist)

            n_ok += 1
        except Exception as e:
            print(f"[WARN] Falló {mfcc_path}: {e}")
            n_fail += 1

    print("\n[RESUMEN] Generación de histogramas completada.")
    print(f"  - Histogramas generados correctamente: {n_ok}")
    print(f"  - Archivos con error:                 {n_fail}")
    print(f"  - Directorio de salida:               {HIST_DIR}")


if __name__ == "__main__":
    generate_histograms()

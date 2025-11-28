# scripts/build_codebook.py
import os
import numpy as np
from tqdm import tqdm
from sklearn.cluster import MiniBatchKMeans
import joblib

from audio.config import (
    MFCC_DIR,
    CODEBOOK_DIR,
    K_CODEBOOK,
    MAX_KMEANS_ITER,
    N_INIT,
)


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


def _collect_training_samples(
    mfcc_paths,
    max_files=None,
    max_frames_per_file=1000,
) -> np.ndarray:
    """
    Recolecta frames de MFCC de múltiples archivos para entrenar el codebook.

    - max_files: Máx. número de archivos MFCC a usar (None = todos).
    - max_frames_per_file: Máx. número de frames por archivo (muestra aleatoria).
    """
    all_samples = []
    n_files_used = 0

    if max_files is not None:
        mfcc_paths = mfcc_paths[:max_files]

    print(f"[INFO] Recolectando frames de MFCC para el entrenamiento...")
    print(f"       Archivos MFCC a usar: {len(mfcc_paths)}")
    print(f"       Máx. frames por archivo: {max_frames_per_file}\n")

    for path in tqdm(mfcc_paths, desc="Recolectando MFCC"):
        try:
            mfcc = _load_mfcc(path)
        except Exception as e:
            print(f"[WARN] Saltando {path}: {e}")
            continue

        n_frames = mfcc.shape[0]

        if max_frames_per_file is None or n_frames <= max_frames_per_file:
            samples = mfcc
        else:
            # Muestra aleatoria sin reemplazo
            idx = np.random.choice(n_frames, size=max_frames_per_file, replace=False)
            samples = mfcc[idx, :]

        all_samples.append(samples)
        n_files_used += 1

    if not all_samples:
        raise RuntimeError("No se pudieron recolectar MFCC válidos para el entrenamiento.")

    training_data = np.vstack(all_samples).astype(np.float32)
    print(f"\n[INFO] Total de frames recolectados: {training_data.shape[0]}")
    print(f"       Dimensión de cada frame:     {training_data.shape[1]}")
    print(f"       Archivos MFCC usados:        {n_files_used}")
    return training_data


def build_codebook(
    max_files=None,
    max_frames_per_file=1000,
    batch_size=4096,
    max_iter=None,
    random_state=42,
):
    """
    Entrena el codebook (MiniBatchKMeans) y guarda:
      - codebook_kmeans.joblib  (modelo KMeans)
      - mfcc_stats.npz          (media y std globales de MFCC)

    La normalización que se usará luego en generate_histograms.py
    será consistente con estas estadísticas globales.
    """
    if max_iter is None:
        max_iter = MAX_KMEANS_ITER

    np.random.seed(random_state)

    os.makedirs(CODEBOOK_DIR, exist_ok=True)

    mfcc_paths = _iter_mfcc_paths()
    if not mfcc_paths:
        raise RuntimeError(f"No se encontraron archivos .npy en {MFCC_DIR}")

    # 1. Recolectar frames para entrenamiento
    training_data = _collect_training_samples(
        mfcc_paths,
        max_files=max_files,
        max_frames_per_file=max_frames_per_file,
    )

    # 2. Calcular media y std globales y guardarlas
    print("\n[INFO] Calculando media y desviación estándar globales de MFCC...")
    global_mean = training_data.mean(axis=0)
    global_std = training_data.std(axis=0)
    # Evitar división por cero
    global_std[global_std == 0.0] = 1e-8

    stats_path = os.path.join(CODEBOOK_DIR, "mfcc_stats.npz")
    np.savez(
        stats_path,
        mean=global_mean.astype(np.float32),
        std=global_std.astype(np.float32),
    )
    print(f"[OK] Estadísticas globales guardadas en: {stats_path}")

    # 3. Normalizar training_data con las stats globales
    training_data = (training_data - global_mean[None, :]) / global_std[None, :]
    training_data = training_data.astype(np.float32)

    # 4. Entrenar MiniBatchKMeans
    print("\n[INFO] Entrenando MiniBatchKMeans (codebook)...\n")
    kmeans = MiniBatchKMeans(
        n_clusters=K_CODEBOOK,
        batch_size=batch_size,
        max_iter=max_iter,
        random_state=random_state,
        n_init=N_INIT,
        verbose=1,
    )

    kmeans.fit(training_data)

    # 5. Guardar modelo
    model_path = os.path.join(CODEBOOK_DIR, "codebook_kmeans.joblib")
    joblib.dump(kmeans, model_path)

    print(f"\n[OK] Codebook entrenado y guardado en: {model_path}")
    print(f"    - K = {K_CODEBOOK}")
    print(f"    - Total frames usados = {training_data.shape[0]}")
    print(f"    - max_iter = {max_iter}, batch_size = {batch_size}, n_init = {N_INIT}")


if __name__ == "__main__":
    # Ajusta estos parámetros según la capacidad de tu máquina
    build_codebook(
        max_files=None,            # None = usar todos los MFCC disponibles
        max_frames_per_file=1500,  # un poco más de frames por archivo
        batch_size=4096,
        max_iter=200,              # más iteraciones que antes
        random_state=42,
    )

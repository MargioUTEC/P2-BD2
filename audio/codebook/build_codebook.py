import os
import numpy as np
import joblib
from sklearn.cluster import MiniBatchKMeans
import logging
from sklearn.exceptions import ConvergenceWarning
import warnings

warnings.simplefilter("ignore", ConvergenceWarning)

from audio.config import MFCC_DIR, CODEBOOK_DIR, K_CODEBOOK

# ============================================================
# LOGGING
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(message)s"
)


# ============================================================
# CARGAR TODOS LOS MFCC
# ============================================================
def load_all_mfccs(max_descriptors=None):
    """
    Carga todos los MFCC .npy de MFCC_DIR.
    Devuelve una matriz (N, D), donde N = total de frames
    y D = número de coeficientes (N_MFCC).
    """

    logging.info("Cargando MFCC desde: %s", MFCC_DIR)

    all_vectors = []

    for fname in os.listdir(MFCC_DIR):
        if not fname.endswith(".npy"):
            continue

        path = os.path.join(MFCC_DIR, fname)

        try:
            mfcc_matrix = np.load(path)

            # ------------------------------------------------------------------
            # Normalización frame-wise para evitar sesgo por volumen
            # Esto sí mejora la similitud entre audios.
            # ------------------------------------------------------------------
            mfcc_matrix = (mfcc_matrix - mfcc_matrix.mean(axis=0)) / (
                mfcc_matrix.std(axis=0) + 1e-8
            )

        except Exception as e:
            logging.warning(f"Error leyendo {fname}: {e}")
            continue

        all_vectors.append(mfcc_matrix)

    if len(all_vectors) == 0:
        raise RuntimeError(
            f"No se encontraron archivos MFCC en {MFCC_DIR}. Ejecuta extract_mfcc.py primero."
        )

    # Concatenación global
    all_vectors = np.concatenate(all_vectors, axis=0)
    logging.info(f"MFCC totales cargados: {all_vectors.shape}")

    # Submuestreo (si hay demasiados)
    if max_descriptors is not None and all_vectors.shape[0] > max_descriptors:
        logging.info(f"Aplicando muestreo aleatorio: {max_descriptors} descriptores…")
        idx = np.random.choice(all_vectors.shape[0], max_descriptors, replace=False)
        all_vectors = all_vectors[idx]

    logging.info(f"Tamaño final para K-Means: {all_vectors.shape}")
    return all_vectors


# ============================================================
# ENTRENAR CODEBOOK
# ============================================================
def build_codebook(n_clusters=K_CODEBOOK, sample_limit=200000):
    """
    Entrena un dictionary-learning (MiniBatchKMeans) para crear K centroides
    que representan "palabras acústicas".
    """

    logging.info("=== CONSTRUCCIÓN DEL CODEBOOK ===")
    logging.info(f"Clusters (k): {n_clusters}")
    logging.info(f"Muestreo máximo: {sample_limit}")

    # 1. Cargar MFCC
    mfcc_vectors = load_all_mfccs(max_descriptors=sample_limit)

    # 2. Entrenar K-Means
    logging.info("Entrenando MiniBatchKMeans...")

    kmeans = MiniBatchKMeans(
        n_clusters=n_clusters,
        batch_size=4096,
        n_init="auto",
        max_no_improvement=30,
        reassignment_ratio=0.01,
        random_state=42,
        verbose=1
    )

    kmeans.fit(mfcc_vectors)

    logging.info("Entrenamiento terminado.")
    logging.info(f"Inercia final del modelo: {kmeans.inertia_:.4f}")

    # 3. Guardar modelo
    os.makedirs(CODEBOOK_DIR, exist_ok=True)
    codebook_path = os.path.join(CODEBOOK_DIR, "codebook_kmeans.pkl")

    joblib.dump(kmeans, codebook_path)
    logging.info(f"Codebook guardado en: {codebook_path}")

    return kmeans

import os
import numpy as np
from tqdm import tqdm
from sklearn.preprocessing import normalize
from sklearn.feature_extraction.text import TfidfTransformer
import joblib

from audio.config import (
    MFCC_DIR,
    HIST_DIR,
    CODEBOOK_DIR,
    K_CODEBOOK
)


# ============================================================
# CARGA DEL CODEBOOK
# ============================================================

def load_codebook():
    """
    Carga el modelo MiniBatchKMeans previamente entrenado.
    """
    model_path = os.path.join(CODEBOOK_DIR, "codebook_kmeans.pkl")

    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"No se encontró el codebook en {model_path}. "
            "Ejecuta antes: build_codebook.py"
        )

    try:
        kmeans = joblib.load(model_path)
    except Exception as e:
        raise RuntimeError(f"Error cargando codebook: {e}")

    return kmeans


# ============================================================
# GENERACIÓN DE HISTOGRAMAS
# ============================================================

def compute_histogram(mfcc_vectors, kmeans):
    """
    Asigna cada MFCC al codeword más cercano (nearest centroid)
    y retorna un histograma de tamaño K_CODEBOOK.
    """
    if mfcc_vectors is None or mfcc_vectors.size == 0:
        return np.zeros(K_CODEBOOK, dtype=np.float32)

    # Asegurar shape correcto
    if mfcc_vectors.ndim != 2:
        raise ValueError(
            f"MFCC inválido, se esperaba matriz 2D y se recibió shape {mfcc_vectors.shape}"
        )

    try:
        labels = kmeans.predict(mfcc_vectors)
    except Exception as e:
        raise RuntimeError(f"Error prediciendo codewords: {e}")

    hist = np.bincount(labels, minlength=K_CODEBOOK).astype(np.float32)
    return hist


def load_all_mfcc_paths():
    """Obtiene la lista de archivos .npy de MFCC almacenados."""
    if not os.path.exists(MFCC_DIR):
        raise FileNotFoundError(f"El directorio MFCC no existe: {MFCC_DIR}")

    return [
        os.path.join(MFCC_DIR, f)
        for f in os.listdir(MFCC_DIR)
        if f.lower().endswith(".npy")
    ]


# ============================================================
# TF-IDF (global sobre todos los histogramas)
# ============================================================

def apply_tfidf(hist_matrix):
    """
    Aplica TF-IDF global y normalización L2.
    Esto mejora bastante la discriminación en búsqueda.
    """
    transformer = TfidfTransformer(norm=None, sublinear_tf=True)

    tfidf = transformer.fit_transform(hist_matrix).toarray()

    # Normalizar por L2 → necesario para similitud coseno
    tfidf = normalize(tfidf, norm="l2")

    return tfidf


# ============================================================
# GUARDADO
# ============================================================

def save_histogram(audio_id, hist_vector):
    """Guarda el histograma TF-IDF (o crudo) en formato .npy."""
    os.makedirs(HIST_DIR, exist_ok=True)

    out_path = os.path.join(HIST_DIR, audio_id + ".npy")
    np.save(out_path, hist_vector)


# ============================================================
# MAIN
# ============================================================

def main(apply_tfidf_flag=True):

    print("\n=== GENERACIÓN DE HISTOGRAMAS ===\n")

    # 1. Cargar codebook
    print("Cargando codebook...")
    kmeans = load_codebook()

    # 2. Obtener lista de MFCC
    print("Buscando archivos MFCC...")
    mfcc_files = load_all_mfcc_paths()

    if len(mfcc_files) == 0:
        raise RuntimeError(
            f"No se encontraron MFCC en {MFCC_DIR}. Ejecuta extract_mfcc.py primero."
        )

    print(f"MFCC encontrados: {len(mfcc_files)}")

    all_hists = []
    audio_ids = []

    # 3. Generación de histogramas
    print("\nGenerando histogramas...\n")

    for mf_path in tqdm(mfcc_files):
        audio_id = os.path.splitext(os.path.basename(mf_path))[0]

        try:
            mfcc_matrix = np.load(mf_path)
        except Exception as e:
            raise RuntimeError(f"Error cargando MFCC {mf_path}: {e}")

        hist = compute_histogram(mfcc_matrix, kmeans)

        all_hists.append(hist)
        audio_ids.append(audio_id)

    all_hists = np.array(all_hists, dtype=np.float32)

    # 4. TF-IDF opcional
    if apply_tfidf_flag:
        print("\nAplicando TF-IDF global...")
        all_hists = apply_tfidf(all_hists)

    # 5. Guardar uno por uno
    print("\nGuardando histogramas individuales...\n")
    for audio_id, hist in zip(audio_ids, all_hists):
        save_histogram(audio_id, hist)

    print("\nHistograms generados correctamente en:", HIST_DIR)
    print("Cantidad total:", len(audio_ids))

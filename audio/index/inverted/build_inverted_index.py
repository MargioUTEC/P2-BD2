
import os
import json
import numpy as np
from tqdm import tqdm

from config import (
    HIST_DIR,
    INDEX_INV_DIR,
    K_CODEBOOK
)

# =========================================================
# Funciones auxiliares
# =========================================================

def load_histograms():
    """Carga histogramas .npy desde features/histograms/."""
    histograms = {}

    for fname in os.listdir(HIST_DIR):
        if fname.endswith(".npy"):
            audio_id = fname.replace(".npy", "")
            path = os.path.join(HIST_DIR, fname)
            hist = np.load(path).astype(float)
            histograms[audio_id] = hist

    if len(histograms) == 0:
        raise RuntimeError("No se encontraron histogramas .npy en HIST_DIR.")

    return histograms


def compute_idf(histograms):
    """Calcula IDF para cada palabra acústica."""
    n_docs = len(histograms)
    df = np.zeros(K_CODEBOOK)

    for hist in histograms.values():
        df += (hist > 0).astype(int)

    idf = np.log((n_docs + 1) / (df + 1)) + 1
    return idf


def ensure_output_dirs():
    os.makedirs(INDEX_INV_DIR, exist_ok=True)

# =========================================================
# Construcción del índice
# =========================================================

def build_inverted_index():
    print("\n=== CONSTRUYENDO ÍNDICE INVERTIDO ACÚSTICO ===")

    ensure_output_dirs()

    print("Cargando histogramas...")
    histograms = load_histograms()

    print("Calculando IDF...")
    idf = compute_idf(histograms)

    print("Construyendo índice invertido...")
    inverted_index = {str(i): [] for i in range(K_CODEBOOK)}
    doc_norms = {}

    for audio_id, hist in tqdm(histograms.items()):
        tf = hist / np.sum(hist) if np.sum(hist) > 0 else hist
        tfidf = tf * idf

        norm = float(np.linalg.norm(tfidf))
        doc_norms[audio_id] = norm

        # Insertar tfidf en la posting list
        for word_id, value in enumerate(tfidf):
            if value > 0:
                inverted_index[str(word_id)].append({
                    "audio_id": audio_id,
                    "score": float(value)
                })

    # Guardar índice invertido
    index_path = os.path.join(INDEX_INV_DIR, "inverted_index.json")
    with open(index_path, "w") as f:
        json.dump(inverted_index, f, indent=4)

    norms_path = os.path.join(INDEX_INV_DIR, "doc_norms.json")
    with open(norms_path, "w") as f:
        json.dump(doc_norms, f, indent=4)

    print("\nÍndice invertido creado con éxito:")
    print(f" -> {index_path}")
    print(f" -> {norms_path}")

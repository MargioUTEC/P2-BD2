# scripts/build_inverted_index.py
"""
Construcción de Índice Invertido Acústico (TF–IDF) a partir de histogramas
de CONTEOS (no normalizados) guardados en HIST_DIR.

Pipeline:
  1. Recorrer todos los .npy de HIST_DIR (cada uno es un histograma 1D).
  2. Interpretar cada histograma como conteos de codewords por documento.
  3. Primer pasada:
       - Calcular df_j = número de documentos donde term j aparece (hist[j] > 0).
  4. Calcular IDF global:
       idf_j = log( (N + 1) / (df_j + 1) ) + 1
  5. Segunda pasada:
       - Para cada documento:
           * TF_j = count_j / sum(counts)
           * TF–IDF_j = TF_j * idf_j
           * norma L2 del vector TF–IDF (||d||)
           * Actualizar posting lists con (audio_id, TF–IDF_j)
  6. Guardar:
       - inverted_index.json
       - doc_norms.json
       - idf.npy
"""

import os
import json
from typing import Dict, List, Tuple

import numpy as np
from tqdm import tqdm

from audio.config import (
    HIST_DIR,
    INDEX_INV_DIR,
    K_CODEBOOK,
)


def _iter_hist_paths() -> List[str]:
    """
    Recorre HIST_DIR recursivamente y devuelve rutas a archivos .npy de histogramas.
    """
    hist_paths: List[str] = []
    for root, _, files in os.walk(HIST_DIR):
        for fname in files:
            if fname.lower().endswith(".npy"):
                hist_paths.append(os.path.join(root, fname))
    hist_paths.sort()
    return hist_paths


def _load_hist(path: str) -> np.ndarray:
    """
    Carga un histograma .npy y valida su forma.

    Esperamos un vector 1D de longitud K_CODEBOOK con conteos (float o int).
    """
    hist = np.load(path)
    if hist.ndim != 1:
        raise ValueError(f"Histograma inválido en {path}, se esperaba vector 1D, got {hist.shape}")
    if hist.size != K_CODEBOOK:
        raise ValueError(
            f"Histograma en {path} tiene longitud {hist.size}, "
            f"pero se esperaba K_CODEBOOK={K_CODEBOOK}"
        )
    return hist.astype(np.float32)


def _audio_id_from_path(path: str) -> str:
    """
    Obtiene el ID de audio a partir del nombre del archivo.

    Ejemplo:
        .../histograms/000/092556.npy -> "092556"
    """
    fname = os.path.basename(path)
    base, _ = os.path.splitext(fname)
    return base  # suele coincidir con el track_id padded (ej. "092556")


def _compute_df_and_doc_count(hist_paths: List[str]) -> Tuple[np.ndarray, int]:
    """
    Primera pasada sobre los histogramas para calcular:

      - df[j] = cantidad de documentos donde term j aparece (hist[j] > 0)
      - N = número total de documentos válidos
    """
    df = np.zeros(K_CODEBOOK, dtype=np.int64)
    N = 0

    print("[INFO] Primera pasada: calculando df (document frequency) por codeword...\n")
    for hist_path in tqdm(hist_paths, desc="DF pass"):
        try:
            hist = _load_hist(hist_path)
        except Exception as e:
            print(f"[WARN] Saltando {hist_path}: {e}")
            continue

        # Documento sin información (suma 0) no aporta a df
        if hist.sum() <= 0.0:
            continue

        # Terminos presentes en este documento (bool)
        present = hist > 0
        df += present.astype(np.int64)
        N += 1

    if N == 0:
        raise RuntimeError("No se encontró ningún documento válido (histogramas con suma > 0).")

    return df, N


def _compute_idf(df: np.ndarray, N: int) -> np.ndarray:
    """
    Calcula el vector IDF usando una fórmula suavizada:

        idf_j = log( (N + 1) / (df_j + 1) ) + 1
    """
    # Para evitar dividir por cero o df_j = 0
    df_safe = df.astype(np.float32)
    idf = np.log((N + 1.0) / (df_safe + 1.0)) + 1.0
    return idf.astype(np.float32)


def build_inverted_index():
    """
    Construye el índice invertido acústico a partir de los histogramas
    en HIST_DIR y guarda:

      - inverted_index.json  (posting lists)
      - doc_norms.json       (normas L2 de documentos)
      - idf.npy              (vector IDF global)
    """
    os.makedirs(INDEX_INV_DIR, exist_ok=True)

    hist_paths = _iter_hist_paths()
    if not hist_paths:
        raise RuntimeError(f"No se encontraron histogramas .npy en {HIST_DIR}")

    print(f"[INFO] Histogramas encontrados: {len(hist_paths)}")
    print(f"[INFO] K_CODEBOOK = {K_CODEBOOK}")
    print()

    # ------------------------------------------------------------------
    # 1) Primera pasada: calcular df y N
    # ------------------------------------------------------------------
    df, N = _compute_df_and_doc_count(hist_paths)

    print("\n[INFO] Documentos válidos (N) =", N)
    print("[INFO] Algunos df de ejemplo (primeros 10 términos):", df[:10].tolist())

    # ------------------------------------------------------------------
    # 2) Calcular IDF global
    # ------------------------------------------------------------------
    print("\n[INFO] Calculando IDF global...")
    idf = _compute_idf(df, N)

    idf_path = os.path.join(INDEX_INV_DIR, "idf.npy")
    np.save(idf_path, idf.astype(np.float32))
    print(f"[OK] IDF guardado en: {idf_path}")

    # ------------------------------------------------------------------
    # 3) Segunda pasada: construir posting lists + normas de documentos
    # ------------------------------------------------------------------
    inverted_index: Dict[str, List[Dict[str, float]]] = {
        str(term_idx): [] for term_idx in range(K_CODEBOOK)
    }
    doc_norms: Dict[str, float] = {}

    print("\n[INFO] Segunda pasada: construyendo índice invertido y normas de documentos...\n")

    n_docs_indexed = 0
    n_docs_skipped = 0

    for hist_path in tqdm(hist_paths, desc="Index pass"):
        try:
            hist = _load_hist(hist_path)
        except Exception as e:
            print(f"[WARN] Saltando {hist_path}: {e}")
            n_docs_skipped += 1
            continue

        audio_id = _audio_id_from_path(hist_path)

        total_count = float(hist.sum())
        if total_count <= 0.0:
            # Documento sin información útil
            n_docs_skipped += 1
            continue

        # TF: frecuencias relativas
        tf = hist / total_count  # shape (K_CODEBOOK,)

        # TF–IDF
        tfidf = tf * idf  # shape (K_CODEBOOK,)

        # Norma L2 del documento
        norm = float(np.linalg.norm(tfidf, ord=2))
        if norm <= 0.0:
            # Vector degenerado -> se descarta
            n_docs_skipped += 1
            continue

        doc_norms[audio_id] = norm

        # Para cada término presente, añadir posting (audio_id, tfidf_j)
        nonzero_indices = np.nonzero(tfidf)[0]
        for term_idx in nonzero_indices:
            score = float(tfidf[term_idx])
            if score == 0.0:
                continue

            term_key = str(int(term_idx))
            inverted_index[term_key].append({
                "audio_id": audio_id,
                "score": score,
            })

        n_docs_indexed += 1

    # Limpieza opcional: eliminar términos sin postings
    empty_terms = [t for t, postings in inverted_index.items() if len(postings) == 0]
    for t in empty_terms:
        del inverted_index[t]

    # ------------------------------------------------------------------
    # 4) Guardar índice invertido y normas de documentos
    # ------------------------------------------------------------------
    index_path = os.path.join(INDEX_INV_DIR, "inverted_index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(inverted_index, f)

    norms_path = os.path.join(INDEX_INV_DIR, "doc_norms.json")
    with open(norms_path, "w", encoding="utf-8") as f:
        json.dump(doc_norms, f)

    print("\n[OK] Índice invertido creado con éxito:")
    print(f"  -> Index:     {index_path}")
    print(f"  -> Doc norms: {norms_path}")
    print(f"  -> IDF:       {idf_path}")
    print(f"  -> Docs indexados: {n_docs_indexed}")
    print(f"  -> Docs omitidos:  {n_docs_skipped}")


if __name__ == "__main__":
    build_inverted_index()

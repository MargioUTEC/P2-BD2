import os
import time
from typing import Dict, Iterable, List, Tuple

import numpy as np

from audio.config import HIST_DIR, INDEX_INV_DIR, K_CODEBOOK, TOP_K
from audio.index.inverted.search_inverted import InvertedIndexSearch
from audio.index.sequential.knn_sequential import KNNSequential

N_VALUES = [2000, 4000, 8000, 16000, 32000]
RNG_SEED = 42
IDF_PATH = os.path.join(INDEX_INV_DIR, "idf.npy")


def _iter_hist_paths() -> List[str]:
    hist_paths: List[str] = []
    for root, _, files in os.walk(HIST_DIR):
        for fname in files:
            if fname.lower().endswith(".npy"):
                hist_paths.append(os.path.join(root, fname))
    hist_paths.sort()
    return hist_paths


def _load_hist(path: str) -> np.ndarray:
    hist = np.load(path)
    if hist.ndim != 1:
        raise ValueError(f"Histograma inválido en {path}, se esperaba vector 1D, got {hist.shape}")
    if hist.size != K_CODEBOOK:
        raise ValueError(
            f"Histograma en {path} tiene longitud {hist.size}, se esperaba K_CODEBOOK={K_CODEBOOK}"
        )
    return hist.astype(np.float32)


def _audio_id_from_path(path: str) -> str:
    fname = os.path.basename(path)
    base, _ = os.path.splitext(fname)
    return base


def cargar_histogramas_base() -> List[Tuple[str, np.ndarray]]:
    hist_data: List[Tuple[str, np.ndarray]] = []
    for hist_path in _iter_hist_paths():
        try:
            hist_data.append((_audio_id_from_path(hist_path), _load_hist(hist_path)))
        except Exception as exc:  # noqa: PERF203 - logueamos y continuamos
            print(f"[WARN] Saltando {hist_path}: {exc}")
    return hist_data


def expandir_histogramas(base: List[Tuple[str, np.ndarray]], n: int) -> List[Tuple[str, np.ndarray]]:
    if not base:
        raise RuntimeError("No hay histogramas disponibles en HIST_DIR.")

    if len(base) >= n:
        return base[:n]

    resultado: List[Tuple[str, np.ndarray]] = []
    copias: Dict[str, int] = {}
    idx = 0

    while len(resultado) < n:
        track_id, hist = base[idx % len(base)]

        if idx < len(base):
            nuevo_id = track_id
        else:
            copias[track_id] = copias.get(track_id, 0) + 1
            nuevo_id = f"{track_id}_dup{copias[track_id]}"

        resultado.append((nuevo_id, hist))
        idx += 1

    return resultado


def construir_indice_invertido(
    histograms: Iterable[Tuple[str, np.ndarray]], idf_vector: np.ndarray
) -> Tuple[Dict[str, List[Dict[str, float]]], Dict[str, float]]:
    inverted_index: Dict[str, List[Dict[str, float]]] = {}
    doc_norms: Dict[str, float] = {}

    for track_id, hist in histograms:
        total_count = float(hist.sum())
        if total_count <= 0.0:
            continue

        tf = hist / total_count
        tfidf = tf * idf_vector
        norm = float(np.linalg.norm(tfidf, ord=2))
        if norm <= 0.0:
            continue

        doc_norms[str(track_id)] = norm

        nonzero_indices = np.nonzero(tfidf)[0]
        for term_idx in nonzero_indices:
            score = float(tfidf[term_idx])
            if score == 0.0:
                continue

            term_key = str(int(term_idx))
            postings = inverted_index.setdefault(term_key, [])
            postings.append({"audio_id": str(track_id), "score": score})

    return inverted_index, doc_norms


def generar_consulta() -> np.ndarray:
    rng = np.random.default_rng(RNG_SEED)
    # Vector aleatorio de conteos positivos para simular el histograma de consulta
    return rng.random(K_CODEBOOK, dtype=np.float32)


def medir_tiempo(func):
    inicio = time.perf_counter()
    resultado = func()
    fin = time.perf_counter()
    return resultado, fin - inicio


def main():
    base_hist = cargar_histogramas_base()
    if not base_hist:
        raise RuntimeError(f"No se encontraron histogramas .npy en {HIST_DIR}")

    if not os.path.exists(IDF_PATH):
        raise FileNotFoundError(f"No se encontró el vector IDF en {IDF_PATH}. Ejecuta build_inverted_index.py.")

    idf_vector = np.load(IDF_PATH).astype(np.float32)
    if idf_vector.ndim != 1 or idf_vector.size != K_CODEBOOK:
        raise ValueError(f"Vector IDF inválido en {IDF_PATH}: shape {idf_vector.shape}")

    query_hist = generar_consulta()

    print("\n=== Experimento: KNN Secuencial vs Índice Invertido (audio) ===")
    print(f"Consulta aleatoria (seed={RNG_SEED}), K={TOP_K}")
    print(f"Histogramas base disponibles: {len(base_hist)}")
    print("N | Tiempo Secuencial (s) | Tiempo Invertido (s) | Top-K coincide | IDs (secuencial)")
    print("-" * 110)

    for n in N_VALUES:
        subset = expandir_histogramas(base_hist, n)

        knn_seq = KNNSequential(histograms=subset, idf_path=IDF_PATH)
        seq_results, tiempo_seq = medir_tiempo(lambda: knn_seq.query(query_hist, k=TOP_K))

        inv_index, doc_norms = construir_indice_invertido(subset, idf_vector)
        inverted = InvertedIndexSearch(inverted_index=inv_index, doc_norms=doc_norms, idf=idf_vector)
        inv_results, tiempo_inv = medir_tiempo(lambda: inverted.search(query_hist, k=TOP_K))

        seq_ids = [doc for doc, _ in seq_results]
        inv_ids = [doc for doc, _ in inv_results]
        coincide = seq_ids == inv_ids
        coincide_txt = "Sí" if coincide else "No"

        print(
            f"{n:<6} | {tiempo_seq:>21.6f} | {tiempo_inv:>20.6f} | {coincide_txt:^14} | "
            f"{', '.join(seq_ids)}"
        )


if __name__ == "__main__":
    main()
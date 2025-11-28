# api/routers/audio.py

from pathlib import Path
import os
from tempfile import NamedTemporaryFile
from typing import Tuple, Optional

import numpy as np
import joblib
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse

from api.models.audio import AudioSearchResult

from audio.config import (
    HIST_DIR,
    K_CODEBOOK,
    AUDIO_DIR,
    CODEBOOK_DIR,
)

from audio.scripts.extract_mfcc import extract_mfcc_from_audio
from audio.index.inverted.search_inverted import InvertedIndexSearch

router = APIRouter()

# ============================================================
# Carga de CODEBOOK + STATS GLOBALes de MFCC
# ============================================================

def _load_codebook_and_stats() -> Tuple[object, np.ndarray, np.ndarray]:
    """
    Carga el modelo KMeans (codebook) y las estadísticas globales de MFCC
    generadas en build_codebook.py:
      - CODEBOOK_DIR / "codebook_kmeans.joblib"
      - CODEBOOK_DIR / "mfcc_stats.npz"
    """
    model_path = CODEBOOK_DIR / "codebook_kmeans.joblib"
    stats_path = CODEBOOK_DIR / "mfcc_stats.npz"

    if not model_path.exists():
        raise FileNotFoundError(
            f"No se encontró el codebook en {model_path}. "
            "Ejecuta antes scripts/build_codebook.py."
        )

    if not stats_path.exists():
        raise FileNotFoundError(
            f"No se encontraron las estadísticas globales de MFCC en {stats_path}. "
            "Ejecuta antes scripts/build_codebook.py."
        )

    try:
        kmeans = joblib.load(model_path)
    except Exception as e:
        raise RuntimeError(f"Error cargando codebook: {e}")

    stats = np.load(stats_path)
    mean = stats["mean"].astype(np.float32)
    std = stats["std"].astype(np.float32)
    std[std == 0.0] = 1e-8

    return kmeans, mean, std


def _normalize_mfcc_query(mfcc_matrix: np.ndarray,
                          mean: np.ndarray,
                          std: np.ndarray) -> np.ndarray:
    """
    Normaliza la matriz de MFCC de la consulta usando las mismas stats
    globales (media/std) que se usaron en generate_histograms.py.
    """
    if mfcc_matrix is None or mfcc_matrix.size == 0:
        raise ValueError("MFCC de consulta vacío o inválido.")

    if mfcc_matrix.ndim != 2:
        raise ValueError(
            f"MFCC de consulta inválido, se esperaba matriz 2D y se recibió {mfcc_matrix.shape}"
        )

    return (mfcc_matrix - mean[None, :]) / std[None, :]


def _compute_histogram_query(mfcc_matrix_norm: np.ndarray,
                             kmeans) -> np.ndarray:
    """
    Dada la matriz MFCC normalizada de la consulta y el codebook KMeans,
    construye un histograma de CONTEOS por codeword de tamaño K_CODEBOOK.

    Este histograma debe ser del mismo formato que los histogramas almacenados
    en HIST_DIR y que espera el InvertedIndexSearch (conteos crudos).
    """
    if mfcc_matrix_norm.shape[0] == 0:
        raise ValueError("Matriz MFCC normalizada vacía al construir histograma de consulta.")

    labels = kmeans.predict(mfcc_matrix_norm)
    hist = np.bincount(labels, minlength=K_CODEBOOK).astype(np.float32)
    return hist


# ============================================================
# Objetos globales del motor acústico
# ============================================================

try:
    _SEARCHER: Optional[InvertedIndexSearch] = InvertedIndexSearch()
except Exception as e:
    print(f"[WARN] No se pudo inicializar el motor de búsqueda acústica: {e}")
    _SEARCHER = None

try:
    _CODEBOOK, _MFCC_MEAN, _MFCC_STD = _load_codebook_and_stats()
except Exception as e:
    print(f"[WARN] No se pudo cargar codebook/stats de MFCC: {e}")
    _CODEBOOK = None
    _MFCC_MEAN = None
    _MFCC_STD = None


# ============================================================
# Helper: cargar histograma de un track_id FMA
# ============================================================

def _load_hist_from_track_id(track_id: str) -> np.ndarray:
    """
    Carga el histograma (de CONTEOS) asociado a un track_id FMA.

    Intenta primero en HIST_DIR/xxxxxx.npy y luego en HIST_DIR/subdir/xxxxxx.npy
    por si usas subcarpetas tipo '092/'.
    """
    tid = str(track_id).zfill(6)
    fname = f"{tid}.npy"

    candidates = [
        os.path.join(HIST_DIR, fname),
        os.path.join(HIST_DIR, tid[:3], fname),  # opcional, por si usas subdirs
    ]

    for path in candidates:
        if os.path.exists(path):
            hist = np.load(path).astype(np.float32)
            if hist.ndim != 1 or hist.shape[0] != K_CODEBOOK:
                raise ValueError(
                    f"Histograma inválido para {tid}: shape={hist.shape}, "
                    f"esperado=({K_CODEBOOK},)"
                )
            return hist

    raise FileNotFoundError(
        f"No existe histograma para {tid}. "
        f"Buscado en: {candidates}"
    )


# ============================================================
# 1) BÚSQUEDA POR AUDIO (track_id FMA ya existente)
# ============================================================

@router.get("/search/{track_id}", response_model=list[AudioSearchResult])
def search_audio(track_id: str, k: int = 10):
    """
    Devuelve top-k tracks más similares a un track_id FMA,
    usando el motor:
      - histograma .npy de CONTEOS
      - InvertedIndexSearch (TF–IDF + coseno sobre índice invertido)
    """
    if _SEARCHER is None:
        raise HTTPException(
            status_code=500,
            detail="Motor acústico no inicializado (revisa índice invertido)."
        )

    if k <= 0:
        raise HTTPException(status_code=400, detail="k debe ser > 0.")

    try:
        q_hist = _load_hist_from_track_id(track_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    results = _SEARCHER.search(q_hist, k=k)

    return [
        AudioSearchResult(track_id=str(tid), score=float(score))
        for tid, score in results
    ]


# ============================================================
# 2) SERVIR ARCHIVOS DE AUDIO
# ============================================================

@router.get("/file/{track_id}")
def get_audio_file(track_id: str):
    """
    Devuelve el archivo de audio (mp3/wav) asociado a un track_id.
    """
    tid = str(track_id).zfill(6)
    subdir = tid[:3]  # carpetas tipo '092', '044', etc.

    file_mp3 = Path(AUDIO_DIR) / subdir / f"{tid}.mp3"
    file_wav = Path(AUDIO_DIR) / subdir / f"{tid}.wav"

    if file_mp3.exists():
        return FileResponse(str(file_mp3), media_type="audio/mpeg")

    if file_wav.exists():
        return FileResponse(str(file_wav), media_type="audio/wav")

    raise HTTPException(status_code=404, detail=f"Audio para {tid} no encontrado.")


# ============================================================
# 3) BÚSQUEDA POR ARCHIVO DE AUDIO EXTERNO
# ============================================================

@router.post("/search_file", response_model=list[AudioSearchResult])
async def search_audio_file(
    file: UploadFile = File(...),
    k: int = 10
):
    """
    Recibe un archivo de audio SUBIDO y retorna top-k tracks FMA similares,
    usando EXACTAMENTE el mismo pipeline que el index:
      - extract_mfcc_from_audio
      - normalización con stats globales (mfcc_stats.npz)
      - codebook KMeans (codebook_kmeans.joblib)
      - histograma de CONTEOS
      - InvertedIndexSearch (TF–IDF + coseno)
    """
    if _SEARCHER is None:
        raise HTTPException(
            status_code=500,
            detail="El motor de búsqueda acústica no está inicializado "
                   "(revisa índice invertido)."
        )

    if _CODEBOOK is None or _MFCC_MEAN is None or _MFCC_STD is None:
        raise HTTPException(
            status_code=500,
            detail="Codebook o estadísticas globales de MFCC no inicializadas "
                   "(revisa build_codebook.py)."
        )

    if k <= 0:
        raise HTTPException(status_code=400, detail="k debe ser > 0.")

    # Guardar el archivo subido en un temporal
    try:
        suffix = ""
        if file.filename:
            _, ext = os.path.splitext(file.filename)
            suffix = ext if ext else ""

        with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            temp_path = tmp.name
            content = await file.read()
            tmp.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error guardando archivo temporal: {e}")

    try:
        # 1) Extraer MFCC del audio externo
        mfcc_matrix = extract_mfcc_from_audio(temp_path)
        if mfcc_matrix is None or mfcc_matrix.size == 0:
            raise RuntimeError("MFCC vacío o inválido al procesar el audio de consulta.")

        # 2) Normalizar MFCC con stats globales (igual que en generate_histograms.py)
        mfcc_norm = _normalize_mfcc_query(mfcc_matrix, _MFCC_MEAN, _MFCC_STD)

        # 3) Construir histograma de codewords (CONTEOS crudos)
        hist = _compute_histogram_query(mfcc_norm, _CODEBOOK)

        # 4) Buscar en el índice invertido (TF–IDF + coseno)
        results = _SEARCHER.search(hist, k=k)

        return [
            AudioSearchResult(track_id=str(tid), score=float(score))
            for tid, score in results
        ]

    except HTTPException:
        # Re-lanzar HTTPException tal cual
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando audio de consulta: {e}")

    finally:
        # Borrar temporal
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            print(f"[WARN] No se pudo borrar temporal: {temp_path}")

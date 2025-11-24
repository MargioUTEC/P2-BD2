"""
config.py
---------
Configuración para el módulo AUDIO:
 - MFCC
 - histogramas
 - codebook
 - índices invertidos
 - KNN secuencial
"""

from pathlib import Path

# ============================================================
# RUTA EXTERNA donde está el dataset FMA SMALL (mp3)
# ============================================================
AUDIO_DIR = Path(r"D:/fma_small")

# ============================================================
# Estructura interna del proyecto (audio/)
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

FEATURES_DIR    = BASE_DIR / "features"
MFCC_DIR        = FEATURES_DIR / "mfcc"
HIST_DIR        = FEATURES_DIR / "histograms"
CODEBOOK_DIR    = BASE_DIR / "codebook"
INDEX_DIR       = BASE_DIR / "index"
INDEX_SEQ_DIR   = INDEX_DIR / "sequential"
INDEX_INV_DIR   = INDEX_DIR / "inverted"
RESULTS_DIR     = BASE_DIR / "results"
DOCS_DIR        = BASE_DIR / "docs"

# Crear directorios
for d in [
    FEATURES_DIR,
    MFCC_DIR,
    HIST_DIR,
    CODEBOOK_DIR,
    INDEX_DIR,
    INDEX_SEQ_DIR,
    INDEX_INV_DIR,
    RESULTS_DIR,
    DOCS_DIR
]:
    d.mkdir(parents=True, exist_ok=True)

# ============================================================
# PARÁMETROS DE AUDIO
# ============================================================

SAMPLE_RATE = 22050
N_MFCC = 20
FRAME_SIZE = 2048
HOP_LENGTH = 512

# ============================================================
# PARÁMETROS PARA K-MEANS
# ============================================================

K_CODEBOOK = 128
MAX_KMEANS_ITER = 300
N_INIT = 10

# ============================================================
# PARÁMETROS DE BÚSQUEDA
# ============================================================

TOP_K = 10
USE_TFIDF = True

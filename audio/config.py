"""
config.py
---------
Config for audio module:
 - MFCC
 - histograms
 - codebook
 - inverted indices
 - sequential KNN
"""

import os
from pathlib import Path

# Ruta a audio
AUDIO_DIR = Path(os.getenv("AUDIO_DIR") or (Path.home() / "Downloads" / "fma_small"))


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

#parametros de audio
SAMPLE_RATE = 22050
N_MFCC = 20
FRAME_SIZE = 2048
HOP_LENGTH = 512

#parametros para k-means
K_CODEBOOK = 128
MAX_KMEANS_ITER = 300
N_INIT = 10
TOP_K = 10
USE_TFIDF = True

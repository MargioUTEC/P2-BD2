import os
AUDIO_DIR = r"D:\fma_small"

# Directorio base del proyecto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Directorios internos
FEATURES_DIR = os.path.join(BASE_DIR, "features")
MFCC_DIR = os.path.join(FEATURES_DIR, "mfcc")
HIST_DIR = os.path.join(FEATURES_DIR, "histograms")
CODEBOOK_DIR = os.path.join(BASE_DIR, "codebook")
INDEX_DIR = os.path.join(BASE_DIR, "index")
INDEX_SEQ_DIR = os.path.join(INDEX_DIR, "sequential")
INDEX_INV_DIR = os.path.join(INDEX_DIR, "inverted")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
DOCS_DIR = os.path.join(BASE_DIR, "docs")

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
N_INIT = 10              # número de inicializaciones para mayor estabilidad

# ============================================================
# PARÁMETROS DE BÚSQUEDA
# ============================================================

TOP_K = 10               # para KNN
USE_TFIDF = True

def ensure_directories():
    dirs = [
        FEATURES_DIR,
        MFCC_DIR,
        HIST_DIR,
        CODEBOOK_DIR,
        INDEX_DIR,
        INDEX_SEQ_DIR,
        INDEX_INV_DIR,
        RESULTS_DIR,
        DOCS_DIR,
    ]
    for d in dirs:
        if not os.path.exists(d):
            os.makedirs(d)
            print(f"[CREADO] {d}")

# Crear directorios automáticamente al importar config
ensure_directories()

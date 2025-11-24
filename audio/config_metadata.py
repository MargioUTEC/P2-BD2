"""
config_metadata.py
-------------------
Configuración centralizada para el módulo de METADATA.
Ahora compatible con SQLite.
"""

from pathlib import Path

# ============================================================
# RUTA EXTERNA donde el usuario colocó los CSV originales
# ============================================================
METADATA_DIR = Path("D:/fma_metadata")  # Ajustar según tu PC

# ============================================================
# RUTAS INTERNAS (dentro del proyecto)
# ============================================================

# Carpeta raíz del proyecto (audio/)
BASE_DIR = Path(__file__).resolve().parents[2]

# Carpeta donde guardaremos JSON + SQLite
METADATA_STORE = BASE_DIR / "metadata_store"
# Subcarpetas internas
TABULAR_DIR = METADATA_STORE / "tabular"


# Archivo final de metadata procesada (JSON)
PARSED_METADATA_PATH = TABULAR_DIR / "parsed_metadata.json"

# Archivo SQLite generado a partir del JSON
SQLITE_DB_PATH = METADATA_STORE / "metadata.db"

# NUEVO: Carpeta de salida para módulos antiguos
METADATA_OUT_DIR = METADATA_STORE

# Crear directorio si no existe
METADATA_STORE.mkdir(parents=True, exist_ok=True)

# ============================================================
# CONSTANTES OPCIONALES
# ============================================================

CSV_TRACKS = "tracks.csv"
CSV_FEATURES = "features.csv"
CSV_GENRES = "genres.csv"
CSV_ECHONEST = "echonest.csv"

CSV_RAW_TRACKS = "raw_tracks.csv"
CSV_RAW_ARTISTS = "raw_artists.csv"
CSV_RAW_ALBUMS = "raw_albums.csv"

CHUNK_SIZE = 5000

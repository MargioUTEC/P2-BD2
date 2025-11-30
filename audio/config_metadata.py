"""
config_metadata.py
-------------------
Configuración centralizada para el módulo de METADATA.
Ahora compatible con SQLite.
"""

from pathlib import Path

# Ir a la sección data del README.md de esta repo "https://github.com/mdeff/fma/tree/master" para cambiar
#Para esta ruta usar el archivo fma_metadata.zip

METADATA_DIR = Path("/Users/margio/Downloads/fma_metadata")
#METADATA_DIR = Path(r"D:\fma_metadata")

BASE_DIR = Path(__file__).resolve().parents[1]


METADATA_STORE = BASE_DIR / "metadata_store"
TABULAR_DIR = METADATA_STORE / "tabular"


PARSED_METADATA_PATH = TABULAR_DIR / "parsed_metadata.json"

SQLITE_DB_PATH = METADATA_STORE / "metadata.db"

METADATA_OUT_DIR = METADATA_STORE

METADATA_STORE.mkdir(parents=True, exist_ok=True)


CSV_TRACKS = "tracks.csv"
CSV_FEATURES = "features.csv"
CSV_GENRES = "genres.csv"
CSV_ECHONEST = "echonest.csv"

CSV_RAW_TRACKS = "raw_tracks.csv"
CSV_RAW_ARTISTS = "raw_artists.csv"
CSV_RAW_ALBUMS = "raw_albums.csv"

CHUNK_SIZE = 5000

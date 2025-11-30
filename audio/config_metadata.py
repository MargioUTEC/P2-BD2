"""
config_metadata.py
-------------------
Centralized configuration for the METADATA module (SQLite friendly).
"""

import os
from pathlib import Path

#Ruta a metadata
METADATA_DIR = Path(os.getenv("METADATA_DIR") or (Path.home() / "Downloads" / "fma_metadata"))

# Project root folder (audio/)
BASE_DIR = Path(__file__).resolve().parents[1]

METADATA_STORE = BASE_DIR / "metadata_store"
TABULAR_DIR = METADATA_STORE / "tabular"

# Output files
PARSED_METADATA_PATH = TABULAR_DIR / "parsed_metadata.json"
SQLITE_DB_PATH = METADATA_STORE / "metadata.db"
METADATA_OUT_DIR = METADATA_STORE

# Ensure store dir exists
METADATA_STORE.mkdir(parents=True, exist_ok=True)

CSV_TRACKS = "tracks.csv"
CSV_FEATURES = "features.csv"
CSV_GENRES = "genres.csv"
CSV_ECHONEST = "echonest.csv"

CSV_RAW_TRACKS = "raw_tracks.csv"
CSV_RAW_ARTISTS = "raw_artists.csv"
CSV_RAW_ALBUMS = "raw_albums.csv"

CHUNK_SIZE = 5000

"""
config_metadata.py
-------------------
Configuración centralizada para el módulo de METADATA del proyecto.

Este archivo define:
 - La ruta EXTERNA de la carpeta fma_metadata (donde están todos los CSV).
 - Las rutas internas donde guardaremos índices B+ y archivos procesados.
 - Constantes globales relacionadas al manejo de metadata tabular.
"""

import os


# ============================================================
# RUTA EXTERNA: Carpeta fma_metadata (proporcionada por el usuario)
# ============================================================
# Ejemplo:
# METADATA_DIR = r"D:/fma_metadata"
# Ajusta la ruta según tu máquina REAL.
from pathlib import Path
from pathlib import Path
METADATA_DIR = Path("D:/fma_metadata")

#METADATA_DIR = r"D:/fma_metadata"   # <-- cámbiala si es necesario


# ============================================================
# RUTAS INTERNAS DEL PROYECTO
# ============================================================

# Carpeta raíz del proyecto (un nivel arriba de este archivo)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Carpeta donde guardaremos los índices B+ y tablas preprocesadas
METADATA_OUT_DIR = os.path.join(BASE_DIR, "metadata_store")

# Carpeta para tablas normalizadas (por ejemplo CSV limpios)
TABULAR_DIR = os.path.join(METADATA_OUT_DIR, "tabular")

# Carpeta para índices B+ generados por nosotros
BPTREE_DIR = os.path.join(METADATA_OUT_DIR, "bptree")

#PARSED_METADATA_PATH = os.path.join(TABULAR_DIR, "parsed_metadata.json")
PARSED_METADATA_PATH = Path(TABULAR_DIR) / "parsed_metadata.json"

# Crear directorios si no existen
os.makedirs(METADATA_OUT_DIR, exist_ok=True)
os.makedirs(TABULAR_DIR, exist_ok=True)
os.makedirs(BPTREE_DIR, exist_ok=True)


# ============================================================
# CONSTANTES GLOBALES PARA PROCESAR METADATA
# ============================================================

# Archivos CSV relevantes del dataset FMA
CSV_TRACKS = "tracks.csv"
CSV_FEATURES = "features.csv"
CSV_GENRES = "genres.csv"
CSV_ECHONEST = "echonest.csv"

CSV_RAW_TRACKS = "raw_tracks.csv"
CSV_RAW_ARTISTS = "raw_artists.csv"
CSV_RAW_ALBUMS = "raw_albums.csv"

# Tamaño máximo de registros a cargar en RAM durante el preprocesamiento
# (El B+ almacenará todo en disco, pero el procesamiento normaliza por lotes)
CHUNK_SIZE = 5000

# Profundidad máxima del B+ Tree
BPLUS_ORDER = 32


"""
parser_metadata.py (VERSIÓN FINAL – COMPLETA Y BLINDADA)
--------------------------------------------------------

Reconstruye correctamente toda la metadata del dataset FMA
a partir de tracks.csv, features.csv, echonest.csv y genres.csv.

Características clave:
- track_id SIEMPRE normalizado a 6 dígitos (ej: 000002, 034996, 122911).
- Limpieza de headers multinivel.
- Alineación por posición para features.csv y echonest.csv (NO contienen track_id).
- Reparación completa de genres.csv (que viene corrupto).
- Inserción recursiva de estructuras anidadas.
- Conversión segura a JSON.
- Compatible con FastAPI para /metadata/track/<id>.
"""

import os
import ast
import json
import numpy as np
import pandas as pd
from pathlib import Path

from audio.config_metadata import (
    METADATA_DIR,
    PARSED_METADATA_PATH
)

# ============================================================
# NORMALIZACIÓN GLOBAL DEL TRACK ID (siempre 6 dígitos)
# ============================================================

def normalize_tid(tid):
    tid = str(tid).strip()
    try:
        return f"{int(tid):06d}"
    except:
        return tid.zfill(6)


# ============================================================
# HELPERS
# ============================================================

def clean_for_json(obj):
    if obj is None or obj is ...:
        return None
    if obj is pd.NA:
        return None
    if isinstance(obj, float) and np.isnan(obj):
        return None

    if isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [clean_for_json(v) for v in obj]

    return obj


def load_multilevel_csv(path: Path):
    """Carga MultiIndex CSV del FMA con dtype=str."""
    df = pd.read_csv(path, header=[0, 1, 2], dtype=str, low_memory=False)
    df = df.replace({np.nan: None})
    return df


def clean_header(col_tuple):
    cleaned = []
    for c in col_tuple:
        if c is None:
            continue
        s = str(c)
        if s.lower().startswith("unnamed"):
            continue
        if s.strip() == "":
            continue
        cleaned.append(s)
    return tuple(cleaned)


def apply_string_eval(v):
    if isinstance(v, str):
        t = v.strip()
        if (t.startswith("{") and t.endswith("}")) or (t.startswith("[") and t.endswith("]")):
            try:
                return ast.literal_eval(t)
            except:
                return v
    return v


def recursive_insert(target, key_tuple, value):
    if len(key_tuple) == 1:
        target[key_tuple[0]] = value
        return

    head, tail = key_tuple[0], key_tuple[1:]

    if head not in target:
        target[head] = {}

    recursive_insert(target[head], tail, value)


def row_to_nested(row: pd.Series):
    nested = {}
    for raw_col, value in row.items():
        header = clean_header(raw_col)
        if not header:
            continue
        value = apply_string_eval(value)
        recursive_insert(nested, header, value)
    return nested


# ============================================================
# CARGA REPARADA DE GENRES.CSV
# ============================================================

def load_genres_csv(path: Path) -> pd.DataFrame:
    """
    Corrige el MultiIndex corrupto de genres.csv.
    Nivel 1 y 2 contienen basura → solo usamos nivel 0.
    Consumimos filas 2+ como datos reales.
    """
    df_raw = pd.read_csv(path, header=[0, 1, 2], dtype=str, low_memory=False)

    # Extraer SOLO el PRIMER nivel de cada columna
    real_cols = [col[0] for col in df_raw.columns]

    df = df_raw.copy()
    df.columns = real_cols

    # Remover primeras dos filas corruptas
    df = df.iloc[2:].reset_index(drop=True)
    df = df.replace({np.nan: None})

    return df


# ============================================================
# PARSER PRINCIPAL
# ============================================================

def parse_fma_metadata():
    print("\n=== PARSEANDO METADATA FMA — VERSIÓN FINAL ===")

    # --------------------
    # 1. Cargar CSVs
    # --------------------
    csv_paths = {
        "tracks": Path(METADATA_DIR) / "tracks.csv",
        "features": Path(METADATA_DIR) / "features.csv",
        "echonest": Path(METADATA_DIR) / "echonest.csv",
        "genres": Path(METADATA_DIR) / "genres.csv",
    }

    loaded = {}

    for key, path in csv_paths.items():
        if not path.exists():
            print(f"[WARN] Falta archivo: {path.name}")
            continue

        print(f"Cargando {path.name}...")
        if key == "genres":
            loaded[key] = load_genres_csv(path)
        else:
            loaded[key] = load_multilevel_csv(path)

    if "tracks" not in loaded:
        raise RuntimeError("ERROR: tracks.csv es obligatorio.")

    tracks_df = loaded["tracks"]

    # --------------------
    # 2. Obtener track_ids REALES
    # --------------------
    print("Procesando tracks.csv...")

    tid_col = ('Unnamed: 0_level_0', 'Unnamed: 0_level_1', 'track_id')

    if tid_col not in tracks_df.columns:
        raise RuntimeError("No se encuentra la columna real del track_id en tracks.csv")

    tid_list = [normalize_tid(t) for t in tracks_df[tid_col].tolist()]

    metadata = {
        tid: {
            "track": {},
            "artist": {},
            "album": {},
            "genre": {},
            "features": {},
            "echonest": {}
        }
        for tid in tid_list
    }

    # Llenar track/artist/album
    for i, row in tracks_df.iterrows():
        tid = tid_list[i]
        nested = row_to_nested(row)

        for sec in ["track", "artist", "album"]:
            if sec in nested:
                metadata[tid][sec] = nested[sec]

    # 3. features.csv (alineación POR TRACK_ID REAL)
    # --------------------
    if "features" in loaded:
        print("Procesando features.csv...")

        df = loaded["features"]

        # Ubicar columna donde vienen los track_id reales
        tid_col = ('feature', 'statistics', 'number')

        # Extraer lista de track_ids REALES (sin la fila basura)
        real_features = df[tid_col].tolist()

        # Detectar fila basura "track_id"
        if real_features[0].lower() == "track_id":
            df = df.iloc[1:].reset_index(drop=True)
            real_features = real_features[1:]

        # Normalizar track_id de features
        real_features = [normalize_tid(t) for t in real_features]

        # Crear mapa: track_id → fila
        feature_map = {tid: df.iloc[i] for i, tid in enumerate(real_features) if tid in metadata}

        # Insertar en metadata
        for tid in metadata:
            if tid in feature_map:
                metadata[tid]["features"] = row_to_nested(feature_map[tid])

    # --------------------
    # 4. echonest.csv (alineación POR TRACK_ID REAL)
    # --------------------
    if "echonest" in loaded:
        print("Procesando echonest.csv...")

        df = loaded["echonest"]

        # track_id real está en la PRIMERA columna del MultiIndex
        tid_col = df.columns[0]

        # Extraer todos los valores
        real_tids = df[tid_col].tolist()

        # Detectar y eliminar la fila basura 'track_id'
        if isinstance(real_tids[0], str) and real_tids[0].lower() == "track_id":
            df = df.iloc[1:].reset_index(drop=True)
            real_tids = real_tids[1:]

        # Normalizar track_ids
        real_tids = [normalize_tid(t) for t in real_tids]

        # Crear mapa: track_id → fila
        echo_map = {
            tid: df.iloc[i]
            for i, tid in enumerate(real_tids)
            if tid in metadata
        }

        # Insertar en metadata
        for tid in metadata:
            if tid in echo_map:
                metadata[tid]["echonest"] = row_to_nested(echo_map[tid])

    # --------------------
    # 5. genres.csv (mapeo por genre_top)
    # --------------------
    if "genres" in loaded:
        print("Procesando genres.csv...")

        genres_df = loaded["genres"]

        # Buscar columna genre_id
        genre_col = next((c for c in genres_df.columns if "genre_id" in str(c).lower()), None)
        if genre_col is None:
            raise RuntimeError("No se encontró genre_id en genres.csv")

        genres_df = genres_df.rename(columns={genre_col: "genre_id"})
        genres_df = genres_df.set_index("genre_id")
        genres_df = genres_df.replace({np.nan: None})

        genre_map = genres_df.to_dict(orient="index")

        # Asignar a cada track
        for tid in metadata:
            gtop = metadata[tid]["track"].get("genre_top")
            if gtop and gtop in genre_map:
                metadata[tid]["genre"] = genre_map[gtop]

    # --------------------
    # 6. Guardar JSON final
    # --------------------
    Path(PARSED_METADATA_PATH).parent.mkdir(parents=True, exist_ok=True)

    with open(PARSED_METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(clean_for_json(metadata), f, indent=4)

    print("\nMetadata final guardada en:")
    print(f" → {PARSED_METADATA_PATH}")
    print(f"Total tracks procesados: {len(metadata)}")

    return metadata


if __name__ == "__main__":
    parse_fma_metadata()

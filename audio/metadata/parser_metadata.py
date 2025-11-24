"""
parser_metadata.py (VERSIÓN DEFINITIVA – MODELO C)
--------------------------------------------------

Reconstruye correctamente la metadata del dataset FMA
a partir de tracks.csv, features.csv, echonest.csv y genres.csv.

SALIDA:
parsed_metadata.json organizado así:

{
  "track_id": {
     "track": { ... },
     "artist": { ... },
     "album":  { ... },
     "genre":  { ... },
     "features": { ... },
     "echonest": { ... }
  },
  ...
}

FUNCIONALIDADES:
- Detecta headers multinivel reales
- Aplana MultiIndex: (nivel1, nivel2) → dict anidado
- Elimina columnas "Unnamed"
- Convierte listas/dicts representados como strings
- Convierte NaN → None
"""

import os
import json
import ast
import numpy as np
import pandas as pd
from pathlib import Path

from audio.config_metadata import (
    METADATA_DIR,
    PARSED_METADATA_PATH
)

# ============================================================
# Helpers
# ============================================================
def clean_for_json(obj):
    """Convierte valores no serializables (como ellipsis) a None."""
    if isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_for_json(v) for v in obj]
    if obj is ...:      # <-- esta línea mata el error
        return None
    return obj

def _load_csv_multi(path: Path) -> pd.DataFrame:
    """Carga CSV con headers multinivel."""
    df = pd.read_csv(path, header=[0, 1, 2], low_memory=False)
    df = df.replace({np.nan: None})
    return df


def _clean_header(col_tuple):
    """
    Toma un tuple de 3 niveles y elimina "Unnamed".
    Ejemplo:
        ("track", "genre_top", "") → ("track", "genre_top")
    """
    cleaned = [c for c in col_tuple if c and not str(c).startswith("Unnamed")]
    return tuple(cleaned)


def _apply_string_eval(v):
    """
    Convierte strings tipo '[1,2]' o '{"a":1}' en objetos reales.
    """
    if isinstance(v, str):
        v = v.strip()
        if (v.startswith("{") and v.endswith("}")) or (v.startswith("[") and v.endswith("]")):
            try:
                return ast.literal_eval(v)
            except:
                return v
    return v


def _recursive_insert(target_dict, key_tuple, value):
    """
    Inserta un valor en un dict anidado siguiendo el tuple:
    ("track", "genre_top") → dict["track"]["genre_top"]
    """
    if len(key_tuple) == 1:
        target_dict[key_tuple[0]] = value
        return

    head = key_tuple[0]
    tail = key_tuple[1:]

    if head not in target_dict:
        target_dict[head] = {}

    _recursive_insert(target_dict[head], tail, value)


def _df_to_nested_dict(df: pd.DataFrame) -> dict:
    """
    Convierte un dataframe con headers multinivel a dict anidado.
    """
    result = {}
    for raw_col, value in df.items():

        cleaned = _clean_header(raw_col)
        if not cleaned:
            continue

        v = _apply_string_eval(value)
        _recursive_insert(result, cleaned, v)

    return result


# ============================================================
# PARSER PRINCIPAL
# ============================================================

def parse_fma_metadata():
    print("\n=== PARSEANDO METADATA FMA (VERSIÓN C: JSON ANIDADO) ===")

    metadata = {}
    csv_files = {
        "tracks": "tracks.csv",
        "features": "features.csv",
        "echonest": "echonest.csv",
        "genres": "genres.csv"
    }

    loaded_tables = {}

    # --------------------------------------------------------
    # 1. Cargar todos los CSV
    # --------------------------------------------------------
    for key, fname in csv_files.items():
        path = Path(METADATA_DIR) / fname

        if not path.exists():
            print(f"[WARN] No existe {fname}, se omite.")
            continue

        print(f"Cargando {fname} con header multinivel...")
        df = _load_csv_multi(path)
        df.index = df.index.astype(str)
        loaded_tables[key] = df

    # --------------------------------------------------------
    # 2. Procesar tracks primero (contiene artist/album/track)
    # --------------------------------------------------------
    print("Procesando tracks.csv...")

    tracks_df = loaded_tables.get("tracks")
    if tracks_df is None:
        raise RuntimeError("tracks.csv es obligatorio y no fue cargado")

    # Crear estructura base por track_id
    for tid, row in tracks_df.iterrows():
        metadata[tid] = {
            "track": {},
            "artist": {},
            "album": {},
            "genre": {},
            "features": {},
            "echonest": {}
        }

        # Convertir row → dict anidado
        nested = _df_to_nested_dict(row)
        # fusionar en metadata[tid]
        for section in ["track", "artist", "album", "genre"]:
            if section in nested:
                metadata[tid][section].update(nested[section])

    # --------------------------------------------------------
    # 3. Añadir features.csv
    # --------------------------------------------------------
    if "features" in loaded_tables:
        print("Procesando features.csv...")
        df_feat = loaded_tables["features"]

        for tid, row in df_feat.iterrows():
            if tid not in metadata:
                continue
            nested = _df_to_nested_dict(row)
            metadata[tid]["features"] = nested

    # --------------------------------------------------------
    # 4. Añadir echonest.csv
    # --------------------------------------------------------
    if "echonest" in loaded_tables:
        print("Procesando echonest.csv...")
        df_echo = loaded_tables["echonest"]
        for tid, row in df_echo.iterrows():
            if tid not in metadata:
                continue
            nested = _df_to_nested_dict(row)
            metadata[tid]["echonest"] = nested

    # --------------------------------------------------------
    # 5. Añadir genres.csv (tabla simple)
    # --------------------------------------------------------
    if "genres" in loaded_tables:
        print("Procesando genres.csv (corrigiendo header multinivel)...")

        df_gen_raw = loaded_tables["genres"]

        # Aplanar columnas multinivel
        flat_cols = []
        for col in df_gen_raw.columns:
            clean = []
            for c in col:
                if c is None:
                    continue
                if c is ...:  # <-- evitar ellipsis en headers
                    continue
                if str(c).startswith("Unnamed"):
                    continue
                if str(c).strip() == "":
                    continue
                clean.append(str(c))
            flat_cols.append("_".join(clean) if clean else None)

        df_gen_raw.columns = flat_cols

        # Buscar columna genre_id real
        genre_id_col = None
        for c in df_gen_raw.columns:
            if c is None:
                continue
            if "genre_id" in c.lower():
                genre_id_col = c
                break

        if genre_id_col is None:
            print("[WARN] No se encontró genre_id en genres.csv → Se omite asignación de géneros.")
        else:
            df_gen = df_gen_raw.rename(columns={genre_id_col: "genre_id"})
            df_gen = df_gen.set_index("genre_id").replace({np.nan: None})
            genre_dict = df_gen.to_dict(orient="index")

            for tid in metadata:
                gtop = metadata[tid]["track"].get("genre_top")
                if gtop and gtop in genre_dict:
                    metadata[tid]["genre"] = genre_dict[gtop]

    # --------------------------------------------------------
    # 6. Guardar JSON final
    # --------------------------------------------------------
    Path(PARSED_METADATA_PATH).parent.mkdir(parents=True, exist_ok=True)

    with open(PARSED_METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(clean_for_json(metadata), f, indent=4)

    print("\nMetadata final guardada en:")
    print(f" → {PARSED_METADATA_PATH}")
    print(f"Total tracks procesados: {len(metadata)}")

    return metadata


if __name__ == "__main__":
    parse_fma_metadata()

"""
Test completo del flujo de metadata FMA:
1. Parseo de CSV → JSON unificado
2. Carga del JSON y validación básica
3. Construcción del índice B+Tree
4. Consultas exactas y por rango
"""

import os
import json
import random

import pandas as pd

from config_metadata import (
    METADATA_DIR,
    PARSED_METADATA_PATH,
    CSV_TRACKS,
    BPLUS_ORDER
)

from metadata.parser_metadata import parse_fma_metadata
from metadata.metadata_index_bptree import (
    build_metadata_bptree,
    MetadataBPlusTree
)


# ===============================================================
# UTILIDADES DEL TEST
# ===============================================================

def _get_some_track_ids(n=5):
    import pandas as pd
    from pathlib import Path
    from config_metadata import METADATA_DIR, CSV_TRACKS

    # Asegurar Path
    metadata_dir = Path(METADATA_DIR)
    tracks_csv = metadata_dir / CSV_TRACKS

    # Cargar el CSV real (track_id está en el índice)
    df = pd.read_csv(tracks_csv, low_memory=False, index_col=0)

    # Normalizar a string
    df.index = df.index.astype(str)

    # Cambiar index → columna
    df = df.reset_index().rename(columns={"index": "track_id"})

    return df["track_id"].sample(n).tolist()



# ===============================================================
# TEST PRINCIPAL DEL PIPELINE DE METADATA
# ===============================================================

def main():
    print("\n========== TEST: PIPELINE COMPLETO DE METADATA ==========\n")

    # -----------------------------------------------------------------
    # 1) EJECUTAR PARSER
    # -----------------------------------------------------------------
    print("→ Ejecutando parser_metadata.parse_fma_metadata()...")
    parse_fma_metadata()

    if not os.path.exists(PARSED_METADATA_PATH):
        raise AssertionError("❌ No se generó parsed_metadata.json")

    print("✓ Archivo parsed_metadata.json generado correctamente.")

    # -----------------------------------------------------------------
    # 2) VALIDAR JSON PARSEADO
    # -----------------------------------------------------------------
    print("→ Cargando JSON parseado para validación...")

    with open(PARSED_METADATA_PATH, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    assert isinstance(metadata, dict) and len(metadata) > 0, \
        "❌ El archivo de metadata está vacío o mal formado"

    print(f"✓ JSON cargado. Total de tracks: {len(metadata)}")

    # Validar estructura de un track al azar
    sample_tid = random.choice(list(metadata.keys()))
    print(f"→ Verificando estructura de track_id={sample_tid}")

    entry = metadata[sample_tid]

    required_fields = ["track", "genre", "features", "echonest"]

    for field in required_fields:
        assert field in entry, f"❌ Falta campo '{field}' en metadata."
        # No siempre existe metadata completa, pero al menos debe estar el campo
        assert isinstance(entry[field], (dict, type(None))), \
            f"❌ Campo '{field}' debe ser dict o None."

    print("✓ Estructura de metadata válida.")

    # -----------------------------------------------------------------
    # 3) CONSTRUIR ÍNDICE B+TREE
    # -----------------------------------------------------------------
    print("\n→ Construyendo índice B+Tree...")

    # Convertir claves string → int para el índice
    metadata_int_keys = {int(k): v for k, v in metadata.items()}

    bpt = build_metadata_bptree(
        track_metadata=metadata_int_keys,
        order=BPLUS_ORDER
    )

    assert isinstance(bpt, MetadataBPlusTree), \
        "❌ build_metadata_bptree no devolvió un BPlusTree válido."

    print("✓ B+Tree construido correctamente.")

    # -----------------------------------------------------------------
    # 4) CONSULTAS EXACTAS
    # -----------------------------------------------------------------
    track_ids = _get_some_track_ids(3)
    print(f"\n→ Probando búsquedas exactas con track_ids: {track_ids}")

    for tid in track_ids:
        tid_int = int(tid)
        res = bpt.search(tid_int)
        assert res is not None, f"❌ El B+Tree no encontró el track {tid}"
        assert isinstance(res, dict), "❌ El valor devuelto no es un diccionario."
        print(f"  • Track {tid} encontrado correctamente.")

    print("✓ Búsquedas exactas verificadas.")

    # -----------------------------------------------------------------
    # 5) CONSULTA POR RANGO
    # -----------------------------------------------------------------
    print("\n→ Probando búsqueda por rango (range_search)...")

    ids_int = sorted([int(t) for t in track_ids])
    low, high = ids_int[0], ids_int[-1]

    range_results = bpt.range_search(low, high)

    assert isinstance(range_results, list), "❌ range_search debe devolver una lista."

    assert len(range_results) > 0, \
        "❌ range_search devolvió lista vacía (esperaba mínimo 1 resultado)."

    print(f"✓ range_search({low}, {high}) devolvió {len(range_results)} resultados.")

    print("\n🎉 TEST COMPLETO DE METADATA SUPERADO CON ÉXITO.\n")


if __name__ == "__main__":
    main()

"""
test_fusion.py
--------------
Test de integración para la fusión AUDIO + METADATA.

Flujo:
1. Escoger un track_id que tenga histograma (.npy)
2. Inicializar:
    - InvertedIndexAudioBackend
    - MetadataQuery
    - AudioMetadataFusion
3. Ejecutar búsqueda fusionada y validar estructura básica.
"""

import os
import random

from config import HIST_DIR
from fusion.audio_backends import InvertedIndexAudioBackend, normalize_tid
from fusion.audio_metadata_fusion import AudioMetadataFusion
from metadata.metadata_query import MetadataQuery


# ============================================================
# UTILIDAD: elegir un track_id QUE SÍ TENGA HISTOGRAMA
# ============================================================

def _pick_track_with_hist() -> str:
    """
    Inspecciona HIST_DIR y selecciona un track_id válido (archivo .npy).
    """
    if not os.path.isdir(HIST_DIR):
        raise AssertionError(f"❌ HIST_DIR no existe: {HIST_DIR}")

    npy_files = [f for f in os.listdir(HIST_DIR) if f.endswith(".npy")]

    if not npy_files:
        raise AssertionError(
            f"❌ No se encontraron histogramas en {HIST_DIR}. "
            "Ejecuta generate_histograms.py"
        )

    track_ids = [os.path.splitext(f)[0] for f in npy_files]

    # Aleatorio pero válido
    random.shuffle(track_ids)
    return track_ids[0]


# ============================================================
# TEST PRINCIPAL
# ============================================================

def main():
    print("\n========== TEST: FUSIÓN AUDIO + METADATA ==========\n")

    # 1) Elegir track_id con histograma
    query_tid_raw = _pick_track_with_hist()
    query_tid = normalize_tid(query_tid_raw)

    print(f"→ Usando track_id (raw):      {query_tid_raw}")
    print(f"→ Usando track_id (normal.):  {query_tid}")

    # 2) Inicializar componentes
    print("\n→ Inicializando InvertedIndexAudioBackend...")
    audio_backend = InvertedIndexAudioBackend()

    print("→ Inicializando MetadataQuery...")
    md_query = MetadataQuery()

    # Validación adicional
    if query_tid not in md_query.table:
        print(f"⚠ ADVERTENCIA: El track_id {query_tid} no existe en metadata.")
        print("  Probando otro track_id automáticamente...")
        query_tid = _pick_track_with_hist()

    print("→ Inicializando AudioMetadataFusion...")
    fusion = AudioMetadataFusion(
        audio_backend=audio_backend,
        metadata_query=md_query,
        alpha=0.7
    )

    # 3) Ejecutar búsqueda fusionada
    print("\n→ Ejecutando búsqueda fusionada search_by_track()...")
    recs = fusion.search_by_track(query_tid, top_k=10)

    assert isinstance(recs, list), "❌ search_by_track debe devolver una lista."
    print(f"✓ search_by_track devolvió {len(recs)} resultados.")

    # Validación de estructura del primer resultado
    if recs:
        first = recs[0]
        assert isinstance(first, dict), "❌ Cada resultado debe ser un dict."
        assert "track_id" in first, "❌ Falta campo 'track_id'."
        assert "score" in first, "❌ Falta campo 'score'."

        print("\nEjemplo de resultado fusionado:")
        for k in ["track_id", "score", "title", "artist", "genre", "year"]:
            print(f"  {k}: {first.get(k)}")

    print("\n🎉 TEST DE FUSIÓN AUDIO + METADATA SUPERADO.\n")


if __name__ == "__main__":
    main()

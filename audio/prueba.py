import os
from config import HIST_DIR
from fusion.audio_backends import InvertedIndexAudioBackend

# ====================================================================
# 1) Seleccionar automáticamente un track_id que sí tenga histograma
# ====================================================================
def pick_valid_track_id():
    if not os.path.isdir(HIST_DIR):
        raise RuntimeError(f"HIST_DIR no existe: {HIST_DIR}")

    # Buscar todos los .npy
    npy_files = [f for f in os.listdir(HIST_DIR) if f.endswith(".npy")]
    if not npy_files:
        raise RuntimeError(
            f"No hay histogramas .npy en {HIST_DIR}. "
            f"Ejecuta generate_histograms.py primero."
        )

    # Tomar un track válido
    track_ids = [os.path.splitext(f)[0] for f in npy_files]
    track_ids.sort()  # opcional: para tener un orden estable
    return track_ids[0]


# ====================================================================
# 2) Ejecutar prueba real de búsqueda por audio (TOP-5)
# ====================================================================
if __name__ == "__main__":
    print("\n========== PRUEBA DE BÚSQUEDA POR AUDIO ==========\n")

    # Elegir track real con histograma
    query_tid = pick_valid_track_id()
    print(f"[INFO] Usando track_id válido con histograma: {query_tid}")

    # Inicializar backend acústico
    backend = InvertedIndexAudioBackend()

    # Ejecutar búsqueda
    print("\n[INFO] Ejecutando búsqueda TOP-5...\n")
    results = backend.search_similar(query_tid, top_k=5)

    # Mostrar resultados
    print("=== TOP 5 SIMILARES ===")
    for tid, score in results:
        print(f"  {tid:>10}   {score:.6f}")

    print("\n🎉 Búsqueda terminada con éxito.\n")

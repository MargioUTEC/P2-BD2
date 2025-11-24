"""
dependencies.py
Carga centralizada de backends para que la API no recargue todo cada request.
"""

from fusion.audio_backends import InvertedIndexAudioBackend
from metadata.metadata_query import MetadataQuery
from fusion.audio_metadata_fusion import AudioMetadataFusion


# ============================
# SINGLETONS
# ============================

print("[INIT] Cargando backend de audio…")
audio_backend = InvertedIndexAudioBackend()

print("[INIT] Cargando metadata…")
metadata_query = MetadataQuery()

print("[INIT] Instanciando fusionador…")
fusion = AudioMetadataFusion(
    audio_backend=audio_backend,
    metadata_query=metadata_query,
    alpha=0.7,
)

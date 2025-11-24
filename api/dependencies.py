from audio.fusion.audio_backends import InvertedIndexAudioBackend
from audio.metadata.metadata_sqlite import MetadataSQLite
from audio.fusion.audio_metadata_fusion import AudioMetadataFusion

print("[INIT] Cargando backend de audio…")
audio_backend = InvertedIndexAudioBackend()

print("[INIT] Conectando metadata (SQLite)…")
metadata_query = MetadataSQLite()

print("[INIT] Instanciando fusionador…")
fusion = AudioMetadataFusion(
    audio_backend=audio_backend,
    metadata_query=metadata_query,
    alpha=0.7,
)

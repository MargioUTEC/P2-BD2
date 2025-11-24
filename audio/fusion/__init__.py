# fusion/__init__.py

"""
Paquete de fusión audio + metadata.

Contiene componentes que combinan:
- Resultados de similitud de audio (MFCC, CLIP, etc.)
- Metadata tabular parseada del dataset FMA

Uso típico:

    from fusion.audio_metadata_fusion import AudioMetadataFusion

    fusion = AudioMetadataFusion(audio_backend=my_audio_backend)
    recs = fusion.search_by_track(
        query_track_id="68580",
        genre=30,
        year=2012,
        top_k_final=20,
    )
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

from api.dependencies import audio_backend
from api.models.audio import AudioSearchResult
router = APIRouter()

# ============================================================
# Ruta donde viven tus audios (ajusta si es diferente)
# ============================================================
AUDIO_DIR = Path(r"D:\fma_small")  # <-- AJUSTA ESTA RUTA A LA TUYA REAL


# ============================================================
# 1) BÚSQUEDA POR AUDIO (TU ENDPOINT ORIGINAL)
# ============================================================
@router.get("/search/{track_id}", response_model=list[AudioSearchResult])
def search_audio(track_id: str, k: int = 5):
    """
    Devuelve top-k tracks más similares usando el backend de audio.
    """
    try:
        results = audio_backend.search_similar(track_id, top_k=k)
        return [
            AudioSearchResult(track_id=tid, score=score)
            for tid, score in results
        ]
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
# ============================================================
# 2) NUEVO: SERVIR ARCHIVOS DE AUDIO
# ============================================================
@router.get("/file/{track_id}")
def get_audio_file(track_id: str):

    tid = track_id.zfill(6)

    subdir = tid[:3]  # carpetas tipo '092', '044', etc.

    file_mp3 = AUDIO_DIR / subdir / f"{tid}.mp3"
    file_wav = AUDIO_DIR / subdir / f"{tid}.wav"

    if file_mp3.exists():
        return FileResponse(str(file_mp3), media_type="audio/mpeg")

    if file_wav.exists():
        return FileResponse(str(file_wav), media_type="audio/wav")

    raise HTTPException(status_code=404, detail=f"Audio para {tid} no encontrado.")
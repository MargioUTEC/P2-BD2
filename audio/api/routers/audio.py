from fastapi import APIRouter, HTTPException
from api.dependencies import audio_backend
from api.models.audio import AudioSearchResult

router = APIRouter()

@router.get("/search/{track_id}", response_model=list[AudioSearchResult])
def search_audio(track_id: str, k: int = 5):
    try:
        results = audio_backend.search_similar(track_id, top_k=k)
        return [
            AudioSearchResult(track_id=tid, score=score)
            for tid, score in results
        ]
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

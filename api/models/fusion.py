from pydantic import BaseModel
from typing import Optional

class FusionResult(BaseModel):
    track_id: str
    score: float
    score_audio: float
    score_metadata: float
    title: Optional[str]
    artist: Optional[str]
    genre: Optional[str]
    year: Optional[str]

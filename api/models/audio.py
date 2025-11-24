from pydantic import BaseModel

class AudioSearchResult(BaseModel):
    track_id: str
    score: float

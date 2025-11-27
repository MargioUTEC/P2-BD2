# api2/models/text.py

from pydantic import BaseModel

class TextSearchResult(BaseModel):
    track_id: str
    score: float
    title: str
    artist: str
    lyrics_excerpt: str
    genre: str
    album: str
    playlist: str
    elapsed_ms: float

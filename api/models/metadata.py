from pydantic import BaseModel
from typing import Any, Dict

class MetadataRecord(BaseModel):
    track_id: str
    data: Dict[str, Any]

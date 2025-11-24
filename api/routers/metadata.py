from fastapi import APIRouter, HTTPException
from api.dependencies import metadata_query
from api.models.metadata import MetadataRecord

router = APIRouter()


@router.get("/track/{track_id}", response_model=MetadataRecord)
def get_metadata(track_id: str):
    md = metadata_query.get_metadata(track_id)
    if md is None:
        raise HTTPException(status_code=404, detail="Track no encontrado en metadata")

    # Aseguramos que el track_id que devolvemos es el normalizado
    return MetadataRecord(track_id=str(track_id), data=md)

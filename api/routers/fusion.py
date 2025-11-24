from fastapi import APIRouter, HTTPException
from api.dependencies import fusion
from api.models.fusion import FusionResult

router = APIRouter()

@router.get("/{track_id}", response_model=list[FusionResult])
def search_fusion(track_id: str, k: int = 10, alpha: float = 0.7):

    try:
        # Cambia el alpha en caliente si lo mandas por parámetro
        fusion.alpha = alpha

        results = fusion.search_by_track(track_id, top_k=k)

        return [FusionResult(**r) for r in results]

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

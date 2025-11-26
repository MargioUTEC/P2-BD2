# api2/routers/text.py

from fastapi import APIRouter, Query
from api2.backend.text_backend import TextSearchBackend
from api2.models.text import TextSearchResult

import os

router = APIRouter()

# Ruta donde está tu índice invertido real
INDEX_DIR = os.path.abspath("Indice_invertido/dataset")

backend = TextSearchBackend(INDEX_DIR)


@router.get("/search", response_model=list[TextSearchResult])
def text_search(
    q: str = Query(..., description="Consulta textual"),
    k: int = Query(5, description="Top-K resultados")
):
    return backend.search(q, top_k=k)

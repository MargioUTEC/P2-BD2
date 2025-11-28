# api/routers/metadata.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.dependencies import metadata_query
from api.models.metadata import MetadataRecord
from test_parser.sql.metadata_query_engine import MetadataQueryEngine

router = APIRouter()

# Motor SQL sobre metadata.db (usa el parser + AST + engine)
_sql_engine = MetadataQueryEngine()


# ==========================
# 1) Metadata por track_id
# ==========================

@router.get("/track/{track_id}", response_model=MetadataRecord)
def get_metadata(track_id: str):
    """
    Devuelve la metadata completa para un track_id específico,
    usando el acceso directo (metadata_query.get_metadata).
    """
    md = metadata_query.get_metadata(track_id)
    if md is None:
        raise HTTPException(status_code=404, detail="Track no encontrado en metadata")

    return MetadataRecord(track_id=track_id, data=md)


# ==========================
# 2) Endpoint SQL genérico
# ==========================

class SqlQuery(BaseModel):
    query: str


@router.post("/query")
def run_metadata_query(payload: SqlQuery):
    """
    Ejecuta una consulta sobre metadata.db usando el parser SQL propio.

    Comportamiento del engine:
      - Si payload.query comienza con SELECT:
            se interpreta como SQL completo (con columnas explícitas o '*').
      - Si NO comienza con SELECT:
            se asume que es solo la condición WHERE y se envuelve como:
                SELECT * FROM metadata WHERE {user_text}

    Devuelve un dict con:
      - "sql":    consulta SQL final ejecutada (str)
      - "params": lista de parámetros (list)
      - "rows":   lista de filas (cada fila es dict con solo las columnas pedidas)
    """
    q = (payload.query or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="La consulta no puede estar vacía.")

    try:
        result = _sql_engine.run_query(q)
        return result
    except Exception as e:
        # Errores de sintaxis, columnas no permitidas, etc.
        raise HTTPException(status_code=400, detail=str(e))

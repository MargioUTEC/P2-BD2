# api/routers/fusion.py

from typing import Optional, Any, List, Set

from fastapi import APIRouter, HTTPException, Query

from api.dependencies import fusion
from api.models.fusion import FusionResult

# Importamos el motor de queries de metadata que construimos antes
from test_parser.sql.metadata_query_engine import MetadataQueryEngine

router = APIRouter()

# Instancia única del motor de metadata para reutilizar conexiones/parsing
metadata_engine = MetadataQueryEngine()


# ============================================================
# Helpers
# ============================================================

def normalize_tid(tid: Any) -> str:
    """
    Normaliza un track_id a 6 dígitos si es numérico.
    Ejemplos:
        34996   -> "034996"
        "34996" -> "034996"
        "034996"-> "034996"
    """
    s = str(tid).strip()
    return s.zfill(6) if s.isdigit() else s


# ============================================================
# Endpoint de Fusión con filtro opcional de metadata
# ============================================================

@router.get("/{track_id}", response_model=List[FusionResult])
def search_fusion(
    track_id: str,
    k: int = 10,
    alpha: float = 0.7,
    q: Optional[str] = Query(
        None,
        description=(
            'Filtro de metadata opcional. '
            'Ej: genre = "Electronic" AND year >= 2010'
        ),
    ),
):
    """
    Búsqueda híbrida (audio + metadata) con filtro opcional de metadata.

    - track_id: ID del track de referencia para la similitud acústica.
    - k: número máximo de vecinos a devolver.
    - alpha: peso de la parte de audio en la fusión interna (fusion.alpha).
    - q: condición sobre la tabla metadata (forma corta o SELECT completo).
    """
    try:
        # Normalizar track_id antes de pasarlo al backend de fusión (por si acaso)
        norm_tid = normalize_tid(track_id)

        # Actualizar alpha en el backend de fusión
        fusion.alpha = alpha

        # -----------------------------------------
        # 1) Si viene un filtro de metadata (q), lo resolvemos primero
        # -----------------------------------------
        allowed_ids: Optional[Set[str]] = None

        if q is not None and q.strip():
            try:
                query_result = metadata_engine.run_query(q)
            except Exception as e:
                # Error en la sintaxis o semántica de la query de metadata
                raise HTTPException(
                    status_code=400,
                    detail=f"Error en query de metadata: {e}",
                )

            rows = query_result.get("rows", [])
            # Conjunto de track_id permitidos, normalizados a 6 dígitos
            allowed_ids = {
                normalize_tid(row["track_id"])
                for row in rows
                if "track_id" in row
            }

            # Si no hay ningún track que cumpla el filtro, podemos devolver vacío directo
            if not allowed_ids:
                return []

        # -----------------------------------------
        # 2) Ejecutar la búsqueda de fusión por audio
        # -----------------------------------------
        base_results = fusion.search_by_track(norm_tid, top_k=k)

        # base_results se espera como lista de dicts con al menos "track_id" y "score"
        if not isinstance(base_results, list):
            raise ValueError("El backend de fusión retornó un tipo inesperado.")

        # -----------------------------------------
        # 3) Filtrar por metadata (si corresponde)
        # -----------------------------------------
        if allowed_ids is not None:
            filtered_results = []
            for r in base_results:
                r_tid = normalize_tid(r.get("track_id", ""))
                if r_tid in allowed_ids:
                    filtered_results.append(r)
            base_results = filtered_results

        # -----------------------------------------
        # 4) Convertir al modelo de respuesta
        # -----------------------------------------
        return [FusionResult(**r) for r in base_results]

    except FileNotFoundError as e:
        # Error típico de audio o índice no encontrado
        raise HTTPException(status_code=404, detail=str(e))

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

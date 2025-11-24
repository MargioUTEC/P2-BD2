from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers.audio import router as audio_router
from api.routers.metadata import router as metadata_router
from api.routers.fusion import router as fusion_router

app = FastAPI(
    title="FMA Audio+Metadata API",
    description="API para búsqueda por audio, metadata y fusión híbrida.",
    version="1.0.0"
)

# ============================
# CORS (permitir todo)
# ============================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================
# RUTAS
# ============================
app.include_router(audio_router, prefix="/audio", tags=["audio"])
app.include_router(metadata_router, prefix="/metadata", tags=["metadata"])
app.include_router(fusion_router, prefix="/fusion", tags=["fusion"])


@app.get("/")
def root():
    return {"message": "API FMA funcionando correctamente"}

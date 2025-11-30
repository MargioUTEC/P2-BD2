# frontend/web_frontend.py
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# ================================
# Importación de APIs
# ================================

# API original (audio + metadata + fusion)
from api.main import app as backend_app

# API de texto (inverted index)
from api2.main2 import app as text_app


# ================================
# Configuración del Frontend
# ================================

ROOT_DIR = Path(__file__).resolve().parent
#app = FastAPI(title="Proyecto 2 - Frontend + API")


# ================================
# Montaje de Backends
# ================================

# # Backend 1: Audio / Metadata / Fusion
# app.mount("/api", backend_app)

# # Backend 2: Búsqueda de Texto (Inverted Index)
# app.mount("/api2", text_app)



API_BASE_URL = os.getenv("API_BASE_URL", "")
app = FastAPI(title="Proyecto 2 - Frontend")


# ================================
# Archivos estáticos y templates
# ================================

templates = Jinja2Templates(directory=str(ROOT_DIR / "templates"))

app.mount(
    "/static",
    StaticFiles(directory=str(ROOT_DIR / "static")),
    name="static",
)


# ================================
# RUTAS UI
# ================================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """
    Página principal: UI de audio + metadata + texto.
    """
    return templates.TemplateResponse(
        "index.html", {"request": request, "api_base_url": API_BASE_URL}
    )
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.main import app as audio_app
from api2.main2 import app as text_app

app = FastAPI(title="Proyecto 2 - Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/api", audio_app)
app.mount("/api2", text_app)


@app.get("/")
async def root():
    return {"message": "Backend en funcionamiento"}
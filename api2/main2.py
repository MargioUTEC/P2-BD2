# api2/main2.py

from fastapi import FastAPI
from api2.routers.text import router as text_router

app = FastAPI(title="Text Search API", version="1.0")

app.include_router(text_router, prefix="/text")


@app.get("/")
def root():
    return {"message": "Texto funcionando correctamente"}

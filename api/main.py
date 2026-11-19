"""FastAPI app factory. `uvicorn api.main:app --reload` for local dev."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import calculate, confirm, consent, consultant, demo, documents

app = FastAPI(title="Paisa Pilot API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(consent.router)
app.include_router(documents.router)
app.include_router(confirm.router)
app.include_router(calculate.router)
app.include_router(consultant.router)
app.include_router(demo.router)


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}

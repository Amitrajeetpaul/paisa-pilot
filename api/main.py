"""FastAPI app factory. `uvicorn api.main:app --reload` for local dev."""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import agents, calculate, confirm, consent, consultant, demo, documents

app = FastAPI(title="Paisa Pilot API", version="0.1.0")

# ALLOWED_ORIGINS is a comma-separated list; defaults to the Vite dev
# server so local dev works unconfigured. In production, set it to the
# deployed web service's URL (see infra/deploy.md step 5).
_default_origins = "http://localhost:5173"
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ALLOWED_ORIGINS", _default_origins).split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(consent.router)
app.include_router(documents.router)
app.include_router(confirm.router)
app.include_router(calculate.router)
app.include_router(consultant.router)
app.include_router(agents.router)
app.include_router(demo.router)


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}

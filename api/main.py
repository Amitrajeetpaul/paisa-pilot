"""FastAPI app factory. `uvicorn api.main:app --reload` for local dev."""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import agents, calculate, confirm, consent, consultant, demo, documents, pilot, session, usage, gst, tax_advice, me

app = FastAPI(title="Paisa Pilot API", version="0.1.0")

# ALLOWED_ORIGINS is a comma-separated list; defaults to Vite dev server + Capacitor mobile schemes.
_default_origins = [
    "http://localhost:5173",
    "http://localhost",
    "https://localhost",
    "capacitor://localhost",
    "ionic://localhost",
]
configured = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]
origins = list(set(_default_origins + configured)) if configured else _default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$|^capacitor://localhost$",
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
app.include_router(session.router)
app.include_router(pilot.router)
app.include_router(usage.router)
app.include_router(gst.router)
app.include_router(tax_advice.router)
app.include_router(me.router)


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}

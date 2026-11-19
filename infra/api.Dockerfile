# Build from the REPO ROOT (not infra/), since the api service needs
# rules_engine/, llm/, agents/, skills/, config/, and ai_studio/ (prompts +
# schemas + the fixtures llm/reader.py's fixture mode serves):
#   docker build -f infra/api.Dockerfile -t paisa-pilot-api .
# See infra/deploy.md for the full Cloud Run deploy sequence.

FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY rules_engine/ ./rules_engine/
COPY llm/ ./llm/
COPY agents/ ./agents/
COPY api/ ./api/
COPY skills/ ./skills/
COPY config/ ./config/
COPY ai_studio/ ./ai_studio/

ENV STORAGE_BACKEND=gcs \
    DB_BACKEND=firestore \
    READER_MODE=live \
    PYTHONUNBUFFERED=1

# Cloud Run sets $PORT (default 8080); never hard-code a port.
CMD exec uvicorn api.main:app --host 0.0.0.0 --port "${PORT:-8080}"

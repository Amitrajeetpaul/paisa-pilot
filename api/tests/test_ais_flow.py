import json
from pathlib import Path

import jsonschema
from fastapi.testclient import TestClient

from api.main import app
from llm.reader import read_document

client = TestClient(app)
SCHEMA = Path(__file__).resolve().parents[2] / "ai_studio" / "schema" / "ais_schema.json"


def test_ais_fixture_matches_locked_schema():
    out = read_document("ais", mode="fixture").model_dump(mode="json")
    jsonschema.validate(out, json.loads(SCHEMA.read_text()))


def test_demo_session_surfaces_ais_extra_tds_card():
    sid = client.post("/demo/sample-session").json()["session_id"]
    cards = client.post(f"/sessions/{sid}/calculate/money-finder").json()["cards"]
    card = next(c for c in cards if c["card_id"] == "ais_extra_tds")
    assert card["amount"] == 2500
    trail = client.get(f"/sessions/{sid}/source-trail/ais_extra_tds").json()
    assert trail["inputs_used"]["tds_credited_in_your_ais"] == 92500

# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from main import app, API_KEY

client = TestClient(app)
headers = {"x-api-key": API_KEY}

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_ingest_and_suggest_reply():
    # ingest sample
    sample = [
        {"id": 1001, "location": "TEST", "rating": 1, "text": "Test poor experience, app crashed", "date": "2025-01-01"}
    ]
    r = client.post("/ingest", json=sample, headers=headers)
    assert r.status_code == 200
    assert 1001 in r.json()["ingested"] or r.json()["ingested"] == []

    # fetch
    r2 = client.get("/reviews/1001", headers=headers)
    assert r2.status_code == 200
    assert "analysis" in r2.json()

    # suggest reply happy path
    r3 = client.post("/reviews/1001/suggest-reply", headers=headers)
    assert r3.status_code == 200
    assert "reply" in r3.json()

def test_unauthorized():
    r = client.get("/reviews")
    assert r.status_code == 401

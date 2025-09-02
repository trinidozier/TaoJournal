from fastapi.testclient import TestClient
import pytest

from your_app.main import app   # adjust import to your FastAPI app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()

def test_protected_journal_requires_auth():
    response = client.get("/journal")  # your protected route
    assert response.status_code == 401

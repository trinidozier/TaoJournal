from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_long_trade():
    resp = client.post("/score-trade", json={
        "buy_price": 50, "sell_price": 75, "stop": 45, "direction": "Long"
    })
    assert resp.status_code == 200
    assert resp.json() == {"PnL": 25.0, "R-Multiple": 5.0}

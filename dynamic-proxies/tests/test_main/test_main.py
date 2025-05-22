from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_healthcheck_returns():
    response = client.get("/api/dynamic-proxies/healthcheck")
    assert response.status_code == 200
    assert response.json() == {"status": 200}

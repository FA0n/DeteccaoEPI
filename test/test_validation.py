from fastapi.testclient import TestClient
from ultralytics import YOLO
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app

client = TestClient(app)
os.environ["TEST_ENV"] = "True"

def test_serve_homepage():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert b"<title>Iniciar API</title>" in response.content

def test_websocket_endpoint():
    with client.websocket_connect("/ws") as websocket:
        assert websocket is not None

def test_start_endpoint():
    response = client.post("/start")
    assert response.status_code == 200
    assert response.json() == {"message": "A API já está em execução!"}

def test_stop_endpoint():
    response = client.get("/stop")
    assert response.status_code == 200
    assert response.json() == {"message": "Captura encerrada com sucesso!"}

def test_invalid_endpoint():
    response = client.get("/invalid-endpoint")
    assert response.status_code == 404

def test_yolo_model_loading():
    model = YOLO("models/best.pt")
    assert model is not None

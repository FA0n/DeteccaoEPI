from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from ultralytics import YOLO

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app
client = TestClient(app)

os.environ["TEST_ENV"] = "True"

class TestAPI:
    def test_serve_homepage(self):
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"<title>VisionSafe - Detector de Capacete</title>" in response.content

    def test_websocket_endpoint(self):
        with client.websocket_connect("/ws") as websocket:
            websocket.send_text("Ping")
            assert websocket is not None

    def test_start_endpoint(self):
        response = client.post("/start")
        assert response.status_code == 200
        assert response.json() == {"message": "Captura das cameras iniciada com sucesso!"}

    def test_stop_endpoint(self):
        response = client.get("/stop")
        assert response.status_code == 200
        assert response.json() == {"message": "Captura das cameras encerrada com sucesso!"}

    def test_invalid_endpoint(self):
        response = client.get("/invalid-endpoint")
        assert response.status_code == 404

    def test_yolo_model_loading(self):
        model = YOLO("models/best.pt")
        assert model is not None

    @patch("cv2.VideoCapture")
    def test_start_camera(self, mock_video): # Mock sendo usado para o teste
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_video.return_value = mock_cap

        response = client.post("/start")
        assert response.status_code == 200
        assert response.json() == {"message": "Captura das cameras iniciada com sucesso!"}

    def test_notifications_file_read(self, tmp_path, monkeypatch):
        fake_file = tmp_path / "notifications.json"
        fake_file.write_text('[{"classe_name" : "not_helmet", "filename" : "test.jpg", "timestamp" : "2025-01-01 10:00:00"}]')

        monkeypatch.setattr("main.NOTIFICATIONS_FILE", str(fake_file))

        response = client.get("/notifications")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["classe_name"] == "not_helmet"
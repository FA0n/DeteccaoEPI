import cv2, time, asyncio, os, torch
import numpy as np

from utils import send_alert, VIOLATIONS_DIR
from ultralytics import YOLO

model = YOLO(os.path.join("models", "best.pt"))

class CameraManager:
    def __init__(self, src, name):
        self.src = src
        self.name = name
        self.cap = cv2.VideoCapture(self.src)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.last_saved_time = 0
        self.delay = 5
        self.max_retries = 5

    def is_opened(self):
        return self.cap.isOpened()
    
    def reconnect(self):
        print(f"Reconectando à câmera {self.name}...")
        self.cap.release()
        attenmpts = 0

        while not self.cap.isOpened() and attenmpts < self.max_retries:
            self.cap = cv2.VideoCapture(self.src)
            if self.cap.isOpened():
                print(f"Câmera {self.name} reconectada com sucesso.")
                return True
            attenmpts += 1
            print(f"Tentativa {attenmpts} de {self.max_retries} para reconectar à câmera {self.name}.")
            time.sleep(2)

        print(f"Falha ao reconectar à câmera {self.name}.")
        return False
    
    def release(self):
        if self.cap.isOpened():
            self.cap.release()


    def process_frame(self):
        if not self.cap.isOpened():
            if not self.reconnect():
                print(f"Falha ao reconectar à câmera {self.name}.")
                return None
            
        success, frame = self.cap.read()
        if not success:
            print(f"Falha ao capturar o frame da câmera {self.name}.")
            if not self.reconnect():
                print(f"Falha ao reconectar à câmera {self.name}.")
                return None
            success, frame = self.cap.read()
            if not success:
                print(f"Falha ao capturar o frame da câmera {self.name} após reconexão.")
                return None
        
        camera_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        camera_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frame = cv2.resize(frame, (camera_width, camera_height))

        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        with torch.no_grad():
            results = model.predict(frame, conf=0.5, device=device)

        # annotated_frame = results[0].plot()
        boxes = results[0].boxes
        annotated_frame = frame.copy()

        CLASS_COLORS = {
            0: (0, 0, 255),      # not_helmet - vermelho
            1: (0, 165, 255),    # not_reflective - laranja
            2: (0, 255, 0),      # helmet - verde
            3: (255, 255, 0),    # reflective - ciano
        }

        for box in boxes.data:
            x1, y1, x2, y2 = map(int, box[:4])
            confidence = float(box[4])
            class_id = int(box[-1])
            class_name = model.names[class_id]
            
            is_violation = class_name in ['not_helmet', 'not_reflective']
            color = (0, 0, 255) if is_violation else CLASS_COLORS.get(class_id, (0, 255, 0))

            if is_violation:
                marker = "[!!!]"
            else:
                marker = "[OK]"

            # Desenha a bounding box
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
            label = f"{marker}{class_name} {confidence:.2f}"

            # Tamnho do texto
            (text_width, text_height), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)

            # Canvas
            text_img = np.zeros((text_height + baseline + 4, text_width + 4, 4), dtype=np.uint8)

            # Preenche o fundo
            text_img[:, :, :3] = color
            text_img[:, :, 3]  = 128 

            # Desenha o texto
            cv2.putText(text_img, label, (2, text_height + 2), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)

            gray = cv2.cvtColor(text_img[:, :, :3], cv2.COLOR_BGR2GRAY)
            text_img[:, :, 3] = np.where(gray > 0, 255, text_img[:, :, 3]).astype(np.uint8)

            text_img = cv2.rotate(text_img, cv2.ROTATE_90_COUNTERCLOCKWISE)
            
            #Posição do texto
            text_x, text_y = x1 + 5, y1 + text_height
            text_x = max(0, x1 - text_img.shape[1] - 10)
            text_y = max(0, y1)

            height, width = annotated_frame.shape[:2]
            if text_x + text_img.shape[1] > width:
                text_x = max(0, width - text_img.shape[1])
            if text_y + text_img.shape[0] > height:
                text_y = max(0, height - text_img.shape[0])

            # Extrai canal alfa para máscara
            alpha_mask = text_img[:, :, 3] / 255.0
            alpha_inv = 1.0 - alpha_mask
            text_rgb = text_img[:, :, :3]

            roi = annotated_frame[text_y:text_y + text_img.shape[0], text_x:text_x + text_img.shape[1]]

            for c in range(3):
                roi[:, :, c] = (alpha_inv * roi[:, :, c] + alpha_mask * text_rgb[:, :, c])

            annotated_frame[text_y:text_y + text_img.shape[0], text_x:text_x + text_img.shape[1]] = roi

            # Desenha a bounding box depois, para garantir que fique à vista
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)

            if is_violation:
                current_time = time.time()
                if current_time - self.last_saved_time > self.delay:
                    self.last_saved_time = current_time
                    timestamp = time.strftime("%Y%m%d-%H%M%S")
                    filename = os.path.join(VIOLATIONS_DIR, f"{self.name}_{class_name}_{timestamp}.jpg")
                    cv2.imwrite(filename, annotated_frame)
                    print(f"Imagem salva: {filename}")

                    # Envia uma notificação
                    try:
                        asyncio.run(send_alert(class_name, filename))
                    except Exception as e:
                        print(f"Erro ao enviar notificação: {e}")

        _, buffer = cv2.imencode('.jpg', annotated_frame)
         
        return buffer.tobytes()
        
# Dicionário de câmeras
cameras = {
    # "webcam": CameraManager(0, "webcam"),
    # "ip_cam1": CameraManager("rtsp://eu:357800!9@10.0.0.103:554/stream1", "ip_cam1"),
    # "ip_cam2": CameraManager("rtsp://usuario:senha@192.168.1.101:554/stream2", "ip_cam2"),
} 

def start_cameras():
    for cam in cameras.values():
        if not cam.is_opened():
            cam.cap.open(cam.src)

def stop_cameras():
    for cam in cameras.values():
        if cam.is_opened():
            cam.release()

def generate_frames(camera_name):
    camera = cameras[camera_name]
    if camera is None:
        return

    while True:
        frame = camera.process_frame()
        if frame is None:
            break
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
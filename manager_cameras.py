from utils import send_alert, VIOLATIONS_DIR
import cv2, time, asyncio, os, platform
from ultralytics import YOLO

model = YOLO(os.path.join("models", "best.pt"))

class CameraManager:
    def __init__(self, src, name):
        self.src = src
        self.name = name
        if platform.system() == "Windows":
            self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        else:
            self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.last_savad_time = 0
        self.delay = 5

    def is_opened(self):
        return self.cap.isOpened()
    
    # def read_frame(self):
    #     return self.cap.read()
    
    def release(self):
        if self.cap.isOpened():
            self.cap.release()

    def process_frame(self):
        success, frame = self.cap.read()
        if not success:
            return None
        
        camera_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        camera_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frame = cv2.resize(frame, (camera_width, camera_height))
        results = model.predict(frame, conf=0.5, device='cpu')
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

            if class_name in ['not_helmet', 'not_reflective']:
                color = (0, 0, 255)
            else:
                color = CLASS_COLORS.get(class_id, (0, 255, 0))

            label = f"{class_name} {confidence:.2f}"
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(annotated_frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                
            (text_width, text_height), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(annotated_frame, (x1, y1 - text_height - baseline), (x1 + text_width, y1), color, -1)
            cv2.putText(annotated_frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        for box in results[0].boxes.data:
            class_id = int(box[-1])
            class_name = model.names[class_id]

            if class_name in ['not_helmet', 'not_reflective']:
                current_time = time.time()
                if current_time - self.last_savad_time > self.delay:
                    self.last_savad_time = current_time
                    timestamp = time.strftime("%Y%m%d-%H%M%S")
                    filename = os.path.join(VIOLATIONS_DIR, f"{class_name}_{timestamp}.jpg")
                    cv2.imwrite(filename, frame)
                    print(f"Imagem salva: {filename}")

                    # Envia uma notificação
                    try:
                        asyncio.run(send_alert(class_name, filename))
                    except Exception as e:
                        print(f"Erro ao enviar notificação: {e}")

        _, buffer = cv2.imencode('.jpg', annotated_frame)
         
        return buffer.tobytes()
        

cameras = {
    "webcam": CameraManager(0, "webcam")
}   # Adicione outras câmeras aqui, como IPs:
    # "ip_cam1": CameraManager("rtsp://usuario:senha@192.168.0.10:554/stream", "ip_cam1")
    

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
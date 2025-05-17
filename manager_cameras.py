import cv2, time, asyncio, os, platform
from ultralytics import YOLO
from utils import send_alert

model = YOLO(os.path.join("models", "best.pt"))

VIOLATIONS_DIR = "violations"

class CameraManager:
    def __init__(self, src, name):
        self.src = src
        self.name = name
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
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
        annotated_frame = results[0].plot()

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
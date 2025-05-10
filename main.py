from fastapi import FastAPI, UploadFile, File, WebSocket
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from ultralytics import YOLO
import webbrowser
import cv2
import time
import asyncio
import base64

app = FastAPI()

model = YOLO('models/best.pt')  # Carregar o modelo treinado

# Inicializa a webcam
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
if not cap.isOpened():
    print("Erro ao acessar a webcam")

@app.get("/")
def serve_homepage():
    return FileResponse("static/index.html")

# Lista de conexões WebSocket ativas
active_connections = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()  # Mantém a conexão aberta
    except:
        active_connections.remove(websocket)

# Função para enviar notificações via WebSocket
async def send_alert(class_name: str, filename: str):
    # Lê a imagem salva e converte para base64
    with open(filename, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
    
    # Cria a mensagem com a imagem em base64
    message = {
        "class_name": class_name,
        "image": encoded_string
    }
    
    # Envia a mensagem para todas as conexões WebSocket ativas
    for connection in active_connections:
        await connection.send_json(message)

# Função para capturar frames da webcam e detectar
def generate_frames():

    last_saved_time = 0
    delay = 5

    while True:
        success, frame = cap.read()
        if not success:
            break

        # Redimensiona e processa o frame
        frame = cv2.resize(frame, (1280, int((1280 / frame.shape[1]) * frame.shape[0])))
        results = model.predict(frame, conf=0.5, device='cpu')
        annotated_frame = results[0].plot()

        for box in results[0].boxes.data:
            class_id = int(box[-1])
            class_name = model.names[class_id]
        
            if class_name in ['not_helmet', 'not_reflective']:
                current_time = time.time()
                if current_time - last_saved_time > delay:
                    last_saved_time = current_time
                    timestamp = time.strftime("%Y%m%d-%H%M%S")
                    filename = f"violations/{class_name}_{timestamp}.jpg"
                    cv2.imwrite(filename, frame)
                    print(f"Imagem salva: {filename}")

                    # Envia uma notificação
                    asyncio.run(send_alert(class_name, filename))

        _, buffer = cv2.imencode('.jpg', annotated_frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

# Endpoint para vídeo em tempo real
@app.get("/video_feed")
def video_feed():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.post("/start")
def start_api():
    # Retorna uma mensagem indicando que a API foi iniciada
    return JSONResponse(content={"message": "A API já está em execução!"})

if __name__ == "__main__":
    import uvicorn
    webbrowser.open("http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)
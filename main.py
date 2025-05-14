from fastapi import FastAPI, UploadFile, File, WebSocket
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from ultralytics import YOLO
import webbrowser, cv2, uvicorn
import os, sys, signal, time, asyncio, base64, threading

app = FastAPI()

is_capturing = False

model = YOLO('models/best.pt')  # Carregar o modelo treinado

# Inicializa a webcam
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
if not cap.isOpened():
    raise RuntimeError("Erro ao acessar a webcam")

if not os.path.exists("violations"):
    os.makedirs("violations")

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
    except Exception as e:
        print(f"Erro no WebSocket: {e}")
        active_connections.remove(websocket)
    finally:
        if websocket in active_connections:
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
    global cap, is_capturing
    # if cap is None or not cap.isOpened():
    #     cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # Recria o objeto cap
    #     if not cap.isOpened():
    #         raise RuntimeError("Erro ao acessar a câmera!")

    last_saved_time = 0
    delay = 5

    while True:
        if not is_capturing:
            time.sleep(0.1)
            continue

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
    global cap, is_capturing
    if cap is None or not cap.isOpened():
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            return JSONResponse(content={"message": "Erro ao acessar a câmera!"}, status_code=500)
    is_capturing = True
    return JSONResponse(content={"message": "A API já está em execução!"})

@app.get("/stop")
def stop_api():
    global cap, is_capturing
    if cap is not None and cap.isOpened():
        cap.release()
        cap = None
    is_capturing = False
    return JSONResponse(content={"message": "Captura encerrada com sucesso!"})

def open_browser():
    webbrowser.open("http://127.0.1:8000")

def signal_handler(sig, frame):
    print("Encerrando o servidor...")

    if cap is not None and cap.isOpened():
        cap.release()
    
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    threading.Thread(target=open_browser, daemon=True).start()
    asyncio.run(uvicorn.run(app, host="127.0.0.1", port=8000))
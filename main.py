from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi import FastAPI, UploadFile, File, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi import BackgroundTasks
from ultralytics import YOLO
import webbrowser, cv2, uvicorn, json
import os, sys, signal, time, asyncio, base64, threading, platform

#Variaveis globais
app = FastAPI()
is_capturing = False
cap = None
camera_width = 1080
camera_height = 720
active_connections = [] # Lista de conexões WebSocket ativas

# Carregar o modelo treinado
model = YOLO(os.path.join('models', 'best.pt'))
             
# Diretórios
STATIC_DIR = "static"
IMG_DIR = os.path.join(STATIC_DIR, "img")
VIOLATIONS_DIR = "violations"
NOTIFICATIONS_FILE = "notifications.json"

#Verifica se as pastas existem, se não existir cria
os.makedirs(VIOLATIONS_DIR, exist_ok=True)
os.makedirs(IMG_DIR, exist_ok=True)

# Deixa os arquivos estáticos para o Frontend
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/static/img", StaticFiles(directory=IMG_DIR), name="img")
app.mount("/violations", StaticFiles(directory=VIOLATIONS_DIR), name="violations")

@app.get("/")
def serve_homepage():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.get("/status")
def serve_status():
    return JSONResponse(content={"status": "OK"})

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

@app.get("/notifications")
def listar_notificacoes():
    try:
        with open(NOTIFICATIONS_FILE, "r") as file:
            notificacoes = json.load(file)
    except FileNotFoundError:
        notificacoes = []
    return notificacoes

def salvar_notificacao(class_name: str, filename: str):
    notificacao = {
        "class_name": class_name,
        "filename": f'/violations/{os.path.basename(filename)}',
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    try:
        with open(NOTIFICATIONS_FILE, "r") as file:
            notificacoes = json.load(file)
    except FileNotFoundError:
        notificacoes = []
    notificacoes.append(notificacao)
    with open(NOTIFICATIONS_FILE, "w") as file:
        json.dump(notificacoes, file, indent=2)

# Função para enviar notificações via WebSocket
async def send_alert(class_name: str, filename: str):
    # Lê a imagem salva e converte para base64
    with open(filename, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
    # Cria a mensagem com a imagem em base64
    message = {
        "class_name": class_name,
        "filename": f'violations/{os.path.basename(filename)}',
        "image": encoded_string
    }
    salvar_notificacao(class_name, filename)
    # Envia a mensagem para todas as conexões WebSocket ativas
    for connection in active_connections:
        await connection.send_json(message)

# Função para capturar frames da webcam e detectar
def generate_frames():
    global cap, is_capturing, camera_width, camera_height

    # if cap is None or not cap.isOpened():
    #     if platform.system() == "Windows":
    #         cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    #         cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1080)
    #         cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    #     else:
    #         cap = cv2.VideoCapture(0)
    #         cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1080)
    #         cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
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
            continue

        # Redimensiona e processa o frame
        frame = cv2.resize(frame, (camera_width, camera_height))
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
                    filename = os.path.join(VIOLATIONS_DIR, f"{class_name}_{timestamp}.jpg")
                    cv2.imwrite(filename, frame)
                    print(f"Imagem salva: {filename}")

                    # Envia uma notificação
                    try:
                        asyncio.run(send_alert(class_name, filename))
                    except Exception as e:
                        print(f"Erro ao enviar notificação: {e}")

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
    global cap, is_capturing, camera_width, camera_height
    # Inicializa a webcam
    if cap is None or not cap.isOpened():
        if platform.system() == "Windows":
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        else:
            cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1080)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        camera_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        camera_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if not cap.isOpened():
            return JSONResponse(content={"message": "Erro ao acessar a câmera!"}, status_code=500)
    is_capturing = True
    return JSONResponse(content={"message": "A API já está em execução!"})

@app.get("/stop")
def stop_api():
    global cap, is_capturing
    is_capturing = False
    if cap is not None and cap.isOpened():
        cap.release()        
    return JSONResponse(content={"message": "Captura encerrada com sucesso!"})

# @app.get("/shutdown")
# def shutdown_api(background_tasks: BackgroundTasks):
#     def shutdown():
#         time.sleep(1)
#         os.kill(os.getpid(), signal.SIGINT)
    
#     background_tasks.add_task(shutdown)
#     return JSONResponse(content={"message": "API encerrada com sucesso!"})

def open_browser():
    webbrowser.open("http://127.0.1:8000")

def signal_handler(sig, frame):
    print("Encerrando o servidor...")

    if cap is not None and cap.isOpened():
        cap.release()
    
    sys.exit(0)




if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    if os.environ.get("TEST_ENV") != "True":
        threading.Thread(target=open_browser, daemon=True).start()
        asyncio.run(uvicorn.run(app, host="127.0.0.1", port=8000))
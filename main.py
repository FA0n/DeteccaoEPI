from utils import NOTIFICATIONS_FILE, STATIC_DIR, VIOLATIONS_DIR, IMG_DIR, active_connections
from manager_cameras import start_cameras, stop_cameras, generate_frames, cameras
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi import FastAPI, WebSocket

import webbrowser, uvicorn, json
import os, sys, signal, asyncio, threading

app = FastAPI()
cap = None

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

@app.post("/start")
def start_api():
    start_cameras()
    return JSONResponse(content={"message": "Captura das cameras iniciada com sucesso!"})

@app.get("/stop")
def stop_api():
    stop_cameras()  
    return JSONResponse(content={"message": "Captura das cameras encerrada com sucesso!"})

# Endpoint para vídeo em tempo real
@app.get("/video_feed/{camera_name}")
def video_feed(camera_name: str = "webcam"):
    if camera_name not in cameras:
        return JSONResponse(content={"error": "Câmera não encontrada!"}, status_code=404)
    return StreamingResponse(generate_frames(camera_name), media_type="multipart/x-mixed-replace; boundary=frame")

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

# @app.get("/shutdown")
# def shutdown_api(background_tasks: BackgroundTasks):
#     def shutdown():
#         time.sleep(1)
#         os.kill(os.getpid(), signal.SIGINT)
    
#     background_tasks.add_task(shutdown)
#     return JSONResponse(content={"message": "API encerrada com sucesso!"})
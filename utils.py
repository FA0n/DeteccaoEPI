import os, time, json, base64

active_connections = [] # Lista de conexões WebSocket ativas

# Diretórios
STATIC_DIR = "static"
IMG_DIR = os.path.join(STATIC_DIR, "img")
VIOLATIONS_DIR = "violations"
NOTIFICATIONS_FILE = "notifications.json"

# Função para enviar notificações via WebSocket
async def send_alert(class_name: str, filename: str):
    # Lê a imagem salva e converte para base64
    with open(filename, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
    # Cria a mensagem com a imagem em base64
    message = {
        "class_name": class_name,
        "filename": f'{os.path.basename(filename)}',
        "image": encoded_string
    }
    salvar_notificacao(class_name, filename)
    # Envia a mensagem para todas as conexões WebSocket ativas
    for connection in active_connections:
        await connection.send_json(message)

def salvar_notificacao(class_name: str, filename: str):
    notificacao = {
        "class_name": class_name,
        "filename": f'{os.path.basename(filename)}',
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
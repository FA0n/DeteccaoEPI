import cv2, platform

# Abre a webcam usando
if platform.system() == "Windows":
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
else:
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

# Tenta definir a resolução para 1920x1080
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

# Verifica se conseguiu abrir
if not cap.isOpened():
    raise RuntimeError("Erro ao acessar a webcam")

# Lê a resolução real após tentar configurar
camera_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
camera_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

print(f"Resolução da câmera: {camera_width}x{camera_height}")

# Loop para mostrar a imagem
while True:
    ret, frame = cap.read()
    if not ret:
        break

    cv2.imshow('Webcam', frame)

    if cv2.waitKey(1) == 27:  # Tecla ESC para sair
        break

cap.release()
cv2.destroyAllWindows()

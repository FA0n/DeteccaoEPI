import cv2

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # Tente mudar para 1 ou outro índice, se necessário

if not cap.isOpened():
    print("Erro: Não foi possível acessar a webcam.")
else:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Erro: Não foi possível capturar o frame.")
            break
        cv2.imshow("Webcam", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
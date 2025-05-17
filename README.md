# API de Detecção de EPIs via Webcam (FastAPI + YOLOv8)

Este projeto usa FastAPI + YOLOv8 para detectar EPIs (capacete, colete, etc) em tempo real usando a webcam.

## Como Rodar

Instale as dependências:

   - Com o ambiente virtual ativo:
      ```
      pip install fastapi uvicorn uvicorn[standard] torch torchvision ultralytics opencv-python pillow
      ```
      ```
      pip install -r requirements.txt
      ```

Baixe o modelo YOLO:

   - Você pode baixar usando:
     ```
     from ultralytics import YOLO
     model = YOLO('yolov8n.pt')
     ```
   - Ou manualmente pelo site da Ultralytics ou [https://universe.roboflow.com/] entre outros.

Inicie o servidor:

   ```
   uvicorn main:app --reload
   ```
   - Ou inicie o main.py

Como Acessar e utilizar:

   - Ao iniciar o sistema localmente o site será aberto automaticamente [http://localhost:8000]
   - Para iniciar a captura, no caso do site criado, tera que realizar o login e no dashboard iniciar o monitoramente, assim a camera
   configurada é ligada e o video_feed aberto. 

## Observações

   - O arquivo requirements.txt possui todas as dependecias necessarias mas, para evitar problemas de compatibilidade, eu aconselho
   que use o primeiro pip install apresentado acima, pois é garantida a intalação de todas as bibliotecas requeridas.

   - Para melhorar a detecção de EPIs reais, troque o modelo `.pt` por um modelo treinado específico.

   - O sistema esta em desenvolvimento, pode e vão ter muitos erros.
   
# 🛡️ Melhorias a implementar:
## Rodar como serviço (Linux):
   - Para iniciar o sistema automaticamente com o servidor
## Permitir múltiplas câmeras ou IP cameras:
   - Passar a fonte da câmera como parâmetro,
## Painel de controle para admin:
   - Interface web para iniciar/parar, ver logs, configurar alertas etc.
## Dockerização:
   - Facilitar a instalação e o deploy em qualquer máquina
## Banco de dados real (SQLite, PostgreSQL):
   - Substituir o notifications.json por algo mais robusto
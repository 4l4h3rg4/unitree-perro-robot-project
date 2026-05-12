# 05 — Conexión WebRTC con el robot

Todo lo que necesitas saber para conectarte al Unitree Go2 desde Python por WiFi.

---

## Cómo funciona la comunicación

El robot Go2 tiene internamente un módulo llamado `webrtc_bridge` que actúa como intermediario:

```
Tu app Python
     │
     │  WebRTC (WiFi)
     ▼
webrtc_bridge (dentro del robot)
     │
     │  DDS (CycloneDDS interno)
     ▼
sport_service / lidar_service / camera_service / ...
```

La librería `unitree_webrtc_connect` habla directamente con el `webrtc_bridge`, sin necesidad de tocar el DDS interno ni instalar nada en el robot.

---

## Modos de conexión disponibles

### Modo LocalSTA (el que usamos en DUOC UC)

El robot y la laptop están en la **misma red WiFi**.

```python
from unitree_webrtc_connect import UnitreeWebRTCConnection, WebRTCConnectionMethod

conn = UnitreeWebRTCConnection(
    WebRTCConnectionMethod.LocalSTA,
    ip="192.168.X.X"  # IP del robot en la red de DUOC
)
await conn.connect()
```

Para encontrar la IP del robot: abriendo la app Unitree Go en el celular → configuración del robot → información de red.

### Modo LocalAP (robot como hotspot)

El robot emite su propia red WiFi y la laptop se conecta a ella directamente.

```python
conn = UnitreeWebRTCConnection(WebRTCConnectionMethod.LocalAP)
await conn.connect()
```

IP del robot en modo AP: siempre `192.168.123.18`.

Este modo es útil si no hay red WiFi disponible, pero limita la laptop a no tener internet al mismo tiempo.

### Modo Remote (desde otra red, via TURN server de Unitree)

Requiere cuenta Unitree y número de serie del robot. No aplica para el proyecto en DUOC.

---

## Instalación de la librería

```bash
pip install go2-webrtc-connect
```

Si se va a usar audio (mic/speaker):
```bash
sudo apt install portaudio19-dev   # Linux
brew install portaudio             # macOS
pip install go2-webrtc-connect[audio]
```

---

## Restricción crítica: una sola conexión a la vez

El robot acepta **exactamente una conexión WebRTC activa**. Si la app Unitree Go en el celular está conectada, el script Python no podrá conectarse.

Antes de correr el agente:
1. Abrir la app Unitree Go en el celular
2. Desconectar o cerrar la app completamente
3. Recién entonces correr el script

---

## Verificar la conexión antes de programar

Antes de integrar con el agente, verificar que la conexión básica funciona:

```bash
# Clonar el repo de la librería para ver los ejemplos
git clone https://github.com/legion1581/unitree_webrtc_connect.git
cd unitree_webrtc_connect

# Correr el ejemplo básico de conexión
python examples/basic/connect_and_standup.py
```

Si el robot se para, la conexión funciona correctamente.

---

## Identificar la IP del robot en la red de DUOC

Opciones para encontrar la IP:

**Opción 1 — Desde la app:**
App Unitree Go → dispositivo → información → dirección IP

**Opción 2 — Escaneo de red:**
```bash
# Instalar nmap si no está
sudo apt install nmap

# Escanear la red (ajustar el rango según la red de DUOC)
nmap -sn 192.168.1.0/24
```

Buscar un dispositivo con nombre "Unitree" o con el fabricante "Rockchip".

**Opción 3 — Usando el serial number (detección automática por multicast):**
```python
conn = UnitreeWebRTCConnection(
    WebRTCConnectionMethod.LocalSTA,
    serialNumber="B42D2000XXXXXXXX"  # número de serie del robot
)
```

El número de serie está en la parte inferior del robot.

---

## Variables de entorno del proyecto

Crear un archivo `.env` basado en `.env.example`:

```
ROBOT_IP=192.168.X.X
ROBOT_SERIAL=B42D2000XXXXXXXX
GEMINI_API_KEY=tu_api_key_aqui
```

El `.env` nunca se sube al repositorio (está en `.gitignore`).

---

## Checklist antes de conectar

- [ ] El robot está encendido y estabilizado (luz de estado: azul fijo)
- [ ] La app Unitree Go está cerrada en el celular
- [ ] La laptop está en la misma red WiFi que el robot
- [ ] Las variables de entorno están configuradas en `.env`
- [ ] La librería está instalada: `pip install go2-webrtc-connect`
- [ ] Se tiene la IP o serial number del robot

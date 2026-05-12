# 02 — Arquitectura del sistema

Descripción completa de cómo se conectan todas las piezas del proyecto.

---

## Visión general

```
Usuario (lenguaje natural)
         │
         ▼
  Google ADK Agent
  ┌──────────────────────────────────────┐
  │  Gemini LLM                          │
  │  → razona la instrucción             │
  │  → decide qué tools llamar           │
  │  → en qué orden                      │
  │                                      │
  │  Tool Registry                       │
  │  → movement_tools.py                 │
  │  → sensor_tools.py                   │
  │  → state_tools.py                    │
  └──────────────────────────────────────┘
         │                        │
         ▼                        ▼ (EventBus pub/sub)
  robot/connection.py      web_dashboard/
  (wrapper WebRTC)         ├── event_bus.py
         │                 ├── server.py (FastAPI + WebSocket + relay WebRTC)
         │                 └── static/ (HTML + Chart.js + Canvas)
         │                        │
         │                        ▼
         │                 Navegador web
         │                 (monitoreo en tiempo real)
         │
         ▼  WiFi — red DUOC UC
  ┌──────────────────────────────┐
  │  Unitree Go2                 │
  │  webrtc_bridge interno       │
  │  → DDS Topics internos       │
  │  → sport_service             │
  │  → lidar_service             │
  │  → camera_service            │
  └──────────────────────────────┘
```

---

## Capas del sistema

### Capa 1 — Interfaz de usuario

El usuario interactúa con el agente mediante texto en lenguaje natural. No necesita saber nada sobre el robot ni sobre los comandos.

Ejemplos de instrucciones válidas:
- "Camina hacia adelante 3 segundos"
- "¿Cuánta batería te queda?"
- "Haz una voltereta y luego siéntate"
- "Gira 90 grados a la derecha y dime qué ves con la cámara"

---

### Capa 2 — Agente (Google ADK + Gemini)

El agente es el cerebro. Recibe la instrucción del usuario y decide cómo ejecutarla.

**Google ADK** provee el framework para:
- Definir tools como funciones Python con descripciones
- Manejar el loop de razonamiento del agente
- Orquestar múltiples llamadas a tools en secuencia

**Gemini** es el modelo de lenguaje que:
- Interpreta la instrucción en lenguaje natural
- Decide qué tool(s) llamar y con qué parámetros
- Puede encadenar múltiples tools para instrucciones complejas
- Responde al usuario con confirmación de lo ejecutado

Cada tool en el agente tiene:
- Un nombre descriptivo (ej. `move_forward`)
- Una descripción en lenguaje natural para que Gemini entienda cuándo usarla
- Parámetros tipados con descripciones
- La función Python que ejecuta el comando real

---

### Capa 3 — Wrapper de conexión WebRTC

`robot/connection.py` abstrae toda la lógica de conexión con el robot.

El robot Go2 usa WebRTC internamente — el mismo protocolo de la app Unitree Go — como puente hacia su sistema DDS interno. La librería `unitree_webrtc_connect` maneja esa comunicación.

El wrapper expone una interfaz simple para las tools:
```python
robot = Go2Connection(ip="192.168.123.18")
await robot.connect()
await robot.move(vx=0.5, vy=0.0, vyaw=0.0)
await robot.disconnect()
```

---

### Capa 4 — Unitree Go2 (hardware)

El robot recibe los comandos, los procesa en su `sport_service` interno y los ejecuta físicamente. También publica datos de sensores de vuelta por el canal WebRTC.

El flujo interno del robot es:
```
WebRTC → webrtc_bridge → DDS Topics → sport_service / lidar_service / camera_service
```

---

### Capa 5 — Dashboard web en tiempo real

Un servidor web (FastAPI + WebSocket) que permite monitorear todo el sistema desde un navegador en tiempo real. Se compone de:

**`event_bus.py` — Bus de eventos pub/sub**
- `Go2Connection` y las tools del agente publican eventos en tópicos (`sensor.battery`, `agent.action`, `connection.state`, etc.)
- El WebSocket se suscribe a los tópicos relevantes y transmite los datos a los clientes conectados
- Desacopla completamente el robot del dashboard: el robot no sabe que existe un dashboard

**`server.py` — Servidor FastAPI**
- Sirve los archivos estáticos del frontend (HTML, JS, CSS)
- Endpoint WebSocket `/ws` para streaming de eventos en tiempo real
- Relay WebRTC (`aiortc`) para transmitir la cámara del robot al navegador
- El WebSocket es bidireccional: el dashboard puede enviar comandos (ej. STOP de emergencia)

**Frontend (`static/`)**
- HTML + JavaScript vanilla con Chart.js para gráficas de tiempo real
- Canvas 2D para visualización de nube de puntos LiDAR (vista cenital)
- Widgets: batería, velocímetro, IMU, cámara, log de acciones, panel de razonamiento, alertas

```
Dashboard web (navegador)
         ▲
         │  WebSocket (eventos en tiempo real)
         │  + WebRTC (video de cámara relay)
         ▼
  web_dashboard/server.py
         ▲
         │  EventBus (pub/sub asíncrono en Python)
         ▼
  Go2Connection + Agent Tools
```

---

## Flujo de una instrucción completa

```
1. Usuario escribe: "camina hacia adelante 5 segundos y siéntate"

2. Gemini recibe la instrucción y razona:
   - necesito llamar move(vx=0.5, vy=0, vyaw=0)
   - esperar 5 segundos
   - luego llamar sit()

3. ADK ejecuta la tool move_forward(speed=0.5, duration=5)
   → llama robot.move(vx=0.5, vy=0, vyaw=0)
   → publica evento agent.action en EventBus
   → espera 5s
   → llama robot.stop_move()

4. ADK ejecuta la tool sit()
   → llama robot.sit()
   → publica evento agent.action en EventBus

5. Gemini responde al usuario: "Listo, caminé 5 segundos hacia adelante y ahora estoy sentado."

6. En paralelo, el dashboard recibe vía WebSocket:
   → agent.action: move_forward(speed=0.5, duration=5)
   → sensor.speed: {vx: 0.5, vy: 0, vyaw: 0}
   → robot.posture: standing → sitting
   → agent.action: sit()
   Todo visible en tiempo real en el navegador.
```

---

## Decisiones de diseño importantes

**¿Por qué WebRTC y no DDS directo?**
Porque el robot en DUOC UC se conecta por WiFi y no tenemos acceso por Ethernet. WebRTC funciona en todos los modelos (Air, Pro, EDU) sin modificar el firmware.

**¿Por qué Google ADK y no LangChain u otro framework?**
Porque ya tienes experiencia con ADK del proyecto Smart Robot Car v4.0. Se aprovecha el conocimiento existente.

**¿Por qué Gemini y no GPT-4?**
Misma razón — el proyecto anterior usó Gemini y funcionó muy bien. Además ADK está optimizado para Gemini.

**¿Una conexión global o por tool?**
La conexión WebRTC se abre una vez al iniciar el agente y se mantiene durante toda la sesión. No se abre y cierra en cada tool — eso sería muy lento.

**¿Cómo se comunica el dashboard con el robot?**
A través de un `EventBus` pub/sub asíncrono. `Go2Connection` y las tools publican eventos; el servidor WebSocket los transmite a los navegadores. El dashboard nunca se conecta directamente al robot — usa la misma conexión WebRTC que el agente.

**¿Por qué FastAPI + WebSocket para el dashboard?**
FastAPI es async nativo (compatible con `asyncio` de `go2-webrtc-connect`), WebSocket permite streaming bidireccional de eventos en tiempo real con mínima latencia, y los archivos estáticos (HTML/JS/CSS) se sirven sin necesidad de un servidor web separado.

---

## Limitación conocida: una sola conexión WebRTC a la vez

El robot acepta **una sola conexión WebRTC activa**. Si la app del celular está conectada al robot, el agente no puede conectarse (y viceversa). Antes de correr el agente, cerrar la app Unitree Go en el teléfono.

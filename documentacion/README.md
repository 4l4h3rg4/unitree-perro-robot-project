# 🐾 Unitree Go2 — Agente IA con Google ADK + Gemini

Proyecto de integración de un agente de lenguaje natural que controla de forma autónoma el perro robot **Unitree Go2** usando **Google ADK** y la **API de Gemini**, comunicándose vía **WebRTC por WiFi** (el mismo protocolo que usa la app oficial Unitree Go).

> Desarrollado en DUOC UC como proyecto de investigación y desarrollo en robótica con IA.

---

## ¿Qué hace este proyecto?

El usuario le habla al agente en lenguaje natural — por ejemplo, _"camina hacia adelante, gira a la derecha y siéntate"_ — y el agente razona, descompone la instrucción y ejecuta los comandos correspondientes en el robot en tiempo real.

El mismo enfoque que funcionó con el Smart Robot Car v4.0, replicado para el Go2.

---

## Estructura del repositorio

```
go2-agent/
│
├── README.md                  ← este archivo
│
├── docs/
│   ├── 01_fuentes_documentacion.md   ← dónde encontrar todo
│   ├── 02_arquitectura.md            ← cómo se conectan las piezas
│   ├── 03_movimientos_y_tools.md     ← todos los comandos disponibles
│   ├── 04_sensores.md                ← cámara, lidar, imu, batería
│   ├── 05_conexion_webrtc.md         ← cómo conectarse al robot
│   ├── 06_plan_de_desarrollo.md      ← fases y checklist del proyecto
│   └── 07_docker_y_despliegue.md     ← Docker, despliegue y troubleshooting
│
├── agent/
│   ├── __init__.py
│   ├── agent.py               ← definición del agente ADK
│   └── tools/
│       ├── __init__.py
│       ├── movement_tools.py  ← tools de movimiento
│       ├── sensor_tools.py    ← tools de sensores
│       └── state_tools.py     ← tools de estado del robot
│
├── robot/
│   ├── __init__.py
│   └── connection.py          ← wrapper de conexión WebRTC
│
├── web_dashboard/             ← dashboard web en tiempo real
│   ├── __init__.py
│   ├── event_bus.py           ← bus de eventos pub/sub asíncrono
│   ├── server.py              ← FastAPI + WebSocket + relay WebRTC
│   └── static/
│       ├── index.html         ← interfaz del dashboard
│       ├── dashboard.js       ← lógica WebSocket + Chart.js + Canvas
│       └── style.css          ← estilos (tema oscuro, responsive)
│
├── tests/
│   └── test_connection.py     ← verificar que el robot responde
│
├── .env.example               ← variables de entorno necesarias
├── .dockerignore              ← exclusiones para Docker
├── Dockerfile                 ← imagen Docker del proyecto
├── docker-compose.yml         ← servicios Docker (agente, dashboard)
├── requirements.txt           ← dependencias Python
└── main.py                    ← punto de entrada (agente + dashboard)
```

---

## Inicio rapido con Docker

```bash
cp .env.example .env
# Editar .env con ROBOT_IP y GEMINI_API_KEY (solo si tienes robot)
docker compose up go2-agent
# Abrir http://localhost:8001
```

Ver [`docs/07_docker_y_despliegue.md`](docs/07_docker_y_despliegue.md) para guia completa de despliegue.

## Requisitos rapidos (instalacion local)

- Python 3.10+
- Unitree Go2 (Air / Pro / EDU) en la misma red WiFi
- API Key de Google Gemini
- Google ADK + FastAPI + aiortc

Ver [`docs/05_conexion_webrtc.md`](docs/05_conexion_webrtc.md) para la configuracion de red.

---

## Documentación del proyecto

| Documento | Contenido |
|---|---|
| [`01_fuentes_documentacion.md`](docs/01_fuentes_documentacion.md) | Todos los repos y links oficiales/no oficiales |
| [`02_arquitectura.md`](docs/02_arquitectura.md) | Flujo completo del sistema |
| [`03_movimientos_y_tools.md`](docs/03_movimientos_y_tools.md) | Todos los comandos del robot + cómo mapearlos como tools |
| [`04_sensores.md`](docs/04_sensores.md) | Cámara, LiDAR, IMU, batería, fuerza |
| [`05_conexion_webrtc.md`](docs/05_conexion_webrtc.md) | Cómo conectarse al robot desde Python |
| [`06_plan_de_desarrollo.md`](docs/06_plan_de_desarrollo.md) | Fases del proyecto con checklist |
| [`07_docker_y_despliegue.md`](docs/07_docker_y_despliegue.md) | Docker, instalacion, despliegue y troubleshooting |

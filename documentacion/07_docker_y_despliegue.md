# 07 — Docker y guia de despliegue

Como levantar el proyecto completo (agente IA + dashboard web) usando Docker o instalacion local. Incluye checklist de requisitos, modos de conexion al robot, y troubleshooting.

---

## Requisitos previos

Antes de levantar el proyecto, verifica cada punto:

### Hardware
- [ ] **Unitree Go2** (Air, Pro o EDU) encendido y estabilizado
  - Luz de estado del robot: **azul fijo** (no intermitente)
  - Si esta roja o parpadeando, esperar a que termine el arranque
- [ ] **Computadora** (laptop/PC) en la **misma red WiFi** que el robot
  - O conectada directamente al hotspot del robot (modo LocalAP)

### Software
- [ ] **Docker** instalado (si usas Docker) o **Python 3.10+** (si instalacion local)
- [ ] **App Unitree Go del celular CERRADA** completamente
  - El robot acepta una sola conexion WebRTC a la vez
  - Si la app esta abierta, el agente no podra conectarse
- [ ] **IP del robot** anotada (ver abajo como obtenerla)
- [ ] **API Key de Gemini** desde https://aistudio.google.com

---

## Como obtener la IP del robot

### Opcion 1 — Desde la app movil
Abrir la app Unitree Go → seleccionar el robot → icono de configuracion → Informacion de red. Anotar la IP y **cerrar la app inmediatamente**.

### Opcion 2 — Escaneo de red
```bash
nmap -sn 192.168.1.0/24
# Buscar dispositivo con fabricante "Rockchip" o hostname "unitree"
```

### Opcion 3 — Modo LocalAP (robot como hotspot)
El robot crea su propia red WiFi. Conecta tu laptop a la red WiFi del robot. La IP siempre es `192.168.12.1`. Configura `ROBOT_CONNECTION_MODE=LocalAP` en `.env`.

---

## Modos de conexion al robot

| Modo | `ROBOT_CONNECTION_MODE` | IP robot | WiFi laptop | Internet laptop |
|---|---|---|---|---|
| **LocalSTA** (recomendado) | `LocalSTA` | Variable (obtener de app o nmap) | Misma red que robot | Si |
| **LocalAP** | `LocalAP` | `192.168.12.1` (fija) | Conectada al hotspot del robot | No |
| **Remote** | `Remote` | No aplica | Cualquiera | Si |

> **En DUOC UC se usa LocalSTA**: robot y laptop en la misma red WiFi del laboratorio.

---

## Docker (recomendado)

### 1. Clonar el repositorio

```bash
git clone <url-del-repo>
cd unitree-perro-robot-project
```

### 2. Configurar variables de entorno (solo si tienes robot)

Si tienes el robot fisico, crea el `.env` con tus datos reales:

```bash
cp .env.example .env
```

Editar `.env`:

```env
ROBOT_IP=192.168.1.100          # IP del robot en la red
ROBOT_SERIAL=                    # Opcional, numero de serie
ROBOT_CONNECTION_MODE=LocalSTA   # LocalSTA, LocalAP o Remote
GEMINI_API_KEY=AIza...           # Tu API key de Gemini
```

Si no tienes robot o quieres probar solo el dashboard, **no necesitas crear `.env`**. El contenedor usa valores default del `.env.example` y el dashboard funciona sin robot.

### 3. Construir y levantar

```bash
# Construir la imagen
docker compose build

# Dashboard web (sin necesidad de robot)
docker compose up go2-agent
# Abrir http://localhost:8001

# Agente CLI (requiere robot configurado en .env)
docker compose --profile cli up go2-agent-cli
```

### 4. Detener

```bash
# Ctrl+C si esta en primer plano, o:
docker compose down
```

### Pasar .env personalizado al contenedor

Si ya tienes tu `.env` configurado, pasalo como volumen:

```bash
docker compose run --rm -v ./conf/.env:/app/.env go2-agent
```

O copialo dentro del Dockerfile antes de hacer build para produccion.

### Nota sobre network_mode: host

El contenedor usa `network_mode: host` para acceder directamente a la red WiFi y comunicarse con el robot via WebRTC. Esto es necesario porque:

- WebRTC requiere visibilidad directa de la IP del host para ICE/STUN
- El robot y la laptop deben estar en la misma red (LocalSTA)
- Sin `host`, el contenedor estaria en una red NAT de Docker y la negociacion WebRTC fallaria

**Limitacion**: `network_mode: host` solo funciona en Linux. En macOS/Windows con Docker Desktop, usar instalacion local (ver abajo).

---

## Instalacion local (sin Docker)

### 1. Requisitos de sistema

```bash
# Linux (Ubuntu/Debian)
sudo apt install python3.10 python3.10-venv python3-pip
sudo apt install portaudio19-dev   # solo si usas audio del robot (Pro/EDU)

# macOS
brew install python@3.10 portaudio
```

### 2. Entorno virtual

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar .env

Igual que en la seccion Docker (paso 2 arriba).

### 5. Ejecutar

```bash
# Dashboard + Agente interactivo
python main.py

# Solo dashboard web
python main.py --dashboard-only
# Abrir http://localhost:8000

# Solo agente en terminal
python main.py --agent-only

# Test de conexion (sin agente ni dashboard)
python tests/test_connection.py
```

---

## Verificar que el robot es accesible

Antes de ejecutar el agente, confirma que el robot responde:

```bash
# Ping al robot
ping 192.168.1.100

# Debe responder. Si no, verificar:
# - Robot encendido
# - Misma red WiFi
# - IP correcta
```

---

## Dashboard web: que esperar

Al abrir `http://localhost:8000` veras:

| Widget | Que muestra | Cuando aparece |
|---|---|---|
| 🔋 Bateria | Gauge circular con %, voltaje, temperatura | Al conectar el robot |
| 📊 Velocidad | Grafica time-series vx/vyaw + brujula de direccion | Al mover el robot |
| 📐 IMU | Roll, pitch, yaw + indicador de estabilidad | Al conectar el robot |
| 📡 LiDAR | Vista cenital de puntos + distancia minima + semaforo obstaculo | Al conectar el robot |
| 📷 Camara | Stream de video via relay WebRTC | Al activar video |
| 🦿 Postura | Icono y texto (de pie/sentado/damp) | Al cambiar postura |
| 🧠 Razonamiento | Lo que el agente esta "pensando" | Al dar instrucciones |
| 🛡️ Alertas | Bateria baja, obstaculo, caida | Automatico |
| 📋 Log | Historial de eventos en tiempo real | Siempre |
| 🛑 STOP | Boton rojo de emergencia | Siempre activo |

---

## Flujo de trabajo tipico (sesion en DUOC UC)

```
1. Encender el robot → esperar luz azul fija
2. Conectar laptop a WiFi del laboratorio (misma red que robot)
3. Abrir app Unitree Go → anotar IP del robot → CERRAR APP
4. Configurar ROBOT_IP en .env
5. docker compose run --rm -v ./conf/.env:/app/.env go2-agent
6. Abrir http://localhost:8001 en el navegador
7. En la terminal, escribir instrucciones en espanol:
   "parate y camina 3 segundos adelante"
   "cuanta bateria tienes?"
   "gira 90 grados y dime que ves"
8. El dashboard muestra todo en tiempo real
9. Al terminar: "sientate y damp" → Ctrl+C
```

---

## Comandos utiles durante el desarrollo

```bash
# Reconstruir imagen tras cambios en el codigo
docker compose build --no-cache

# Ver logs del contenedor
docker compose logs -f go2-agent

# Entrar al contenedor para debug
docker compose run --rm go2-agent bash

# Ejecutar tests dentro del contenedor
docker compose run --rm go2-agent python tests/test_connection.py

# Dashboard sin robot (pruebas de frontend)
docker compose up go2-agent
# Abrir http://localhost:8001
```

---

## Troubleshooting

### El robot no se conecta

| Sintoma | Causa probable | Solucion |
|---|---|---|
| `ConnectionError` / timeout | App del celular abierta | Cerrar la app Unitree Go completamente |
| `ConnectionError` / timeout | IP incorrecta | Verificar IP con nmap o app |
| `SystemExit` en connect | Robot ya conectado a otro cliente | Cerrar app, reiniciar robot si es necesario |
| `Data channel did not open` | Robot en modo damp/sleep | Tocar el robot para despertarlo, esperar luz azul |
| Luz del robot roja | Robot arrancando | Esperar 1-2 min hasta luz azul fija |
| `Timeout conectando al robot (10s)` | IP no accesible o robot apagado | Verificar ping a la IP del robot |

### El dashboard no carga

| Sintoma | Solucion |
|---|---|
| `ERR_CONNECTION_REFUSED` en navegador | Verificar que el contenedor esta corriendo: `docker compose ps`. El puerto default es 8001. |
| Puerto 8001 ocupado | Cambiar `DASHBOARD_PORT` en `.env` o con `-e DASHBOARD_PORT=8002` en docker compose |
| WebSocket no conecta | Verificar que no hay firewall bloqueando. En localhost no deberia. |
| Dashboard muestra "Desconectado" | Normal si el robot no esta conectado. El dashboard funciona igual. |

### WebRTC / Video / LiDAR no funciona

| Sintoma | Solucion |
|---|---|
| Video no aparece | El video se activa automaticamente al conectar. Si no, llamar `switchVideoChannel(True)` |
| LiDAR sin datos | Robot debe estar en modo activo (no damp). Ejecutar `stand_up()` primero. |
| LiDAR datos vacios | El decoder LiDAR requiere `disableTrafficSaving(True)` — se maneja internamente. |
| Latencia alta (~200ms) | Normal via WebRTC. Usar `speed_level=0` para movimientos mas seguros. |

### Docker en macOS / Windows

`network_mode: host` no funciona en Docker Desktop. Opciones:

1. **Instalacion local** (recomendado para macOS/Windows): seguir la guia de instalacion local arriba.
2. **Docker con bridge**: editar `docker-compose.yml` y cambiar `network_mode: host` por:
   ```yaml
   ports:
     - "8000:8000"
   ```
   Pero WebRTC puede fallar porque el contenedor no expone la IP real del host.

---

## Variables de entorno (referencia completa)

| Variable | Obligatoria | Default | Descripcion |
|---|---|---|---|
| `ROBOT_IP` | Si (LocalSTA) | — | IP del robot en la red |
| `ROBOT_SERIAL` | No | — | Numero de serie (alternativa a IP) |
| `ROBOT_CONNECTION_MODE` | No | `LocalSTA` | `LocalSTA`, `LocalAP` o `Remote` |
| `GEMINI_API_KEY` | Si (para agente IA) | — | API key de Google Gemini |
| `GEMINI_MODEL` | No | `gemini-2.5-flash` | Modelo de Gemini a usar |
| `DASHBOARD_HOST` | No | `0.0.0.0` | Host donde sirve el dashboard |
| `DASHBOARD_PORT` | No | `8000` | Puerto del dashboard web |

---

## Arquitectura con Docker

```
┌─────────────────────────────────────────────────┐
│  Docker (network_mode: host)                    │
│                                                 │
│  ┌───────────────────────────────────────────┐  │
│  │  main.py                                  │  │
│  │  ├── Go2Agent (Google ADK + Gemini)       │  │
│  │  │   ├── MovementTools (18 tools)         │  │
│  │  │   ├── SensorTools (8 tools)            │  │
│  │  │   └── StateTools (2 tools)             │  │
│  │  │                                        │  │
│  │  ├── Go2Connection (wrapper WebRTC)       │  │
│  │  │   └── EventBus (pub/sub)               │  │
│  │  │                                        │  │
│  │  └── FastAPI server (:8000)               │  │
│  │      ├── WebSocket /ws                    │  │
│  │      └── Static files (HTML/JS/CSS)       │  │
│  └───────────────────────────────────────────┘  │
│                      │                          │
└──────────────────────┼──────────────────────────┘
                       │ WiFi (misma red)
                       ▼
              ┌─────────────────┐
              │  Unitree Go2    │
              │  webrtc_bridge  │
              └─────────────────┘
```

---

## Seguridad

- El archivo `.env` con la API key de Gemini **nunca** se sube al repositorio (esta en `.gitignore` y `.dockerignore`)
- `.env.example` es el template publico, sin keys reales
- El dashboard escucha en `0.0.0.0` por conveniencia. En redes publicas, usar `127.0.0.1` o un firewall
- El boton STOP de emergencia en el dashboard detiene el robot inmediatamente

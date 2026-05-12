# 06 — Plan de desarrollo

Fases del proyecto ordenadas de menor a mayor complejidad. Cada fase tiene un objetivo claro y un checklist de verificación antes de pasar a la siguiente.

A partir de la Fase 1, cada fase incluye tareas del **dashboard web en tiempo real** integradas incrementalmente. El dashboard usa **FastAPI + WebSocket + aiortc** en el backend y **HTML/JS vanilla + Chart.js + Canvas** en el frontend.

---

## Componente transversal: EventBus

Se agrega un bus de eventos asíncrono (`web_dashboard/event_bus.py`) que desacopla `Go2Connection` del dashboard. El robot publica eventos; el WebSocket los transmite a los navegadores conectados.

**Eventos del sistema:**

| Tópico | Payload | Origen |
|---|---|---|
| `connection.state` | `connected` / `disconnected` / `reconnecting` / `error` | `Go2Connection` |
| `sensor.battery` | `{percentage, voltage, temperature}` | `Go2Connection` |
| `sensor.imu` | `{accel_x/y/z, gyro_x/y/z, roll, pitch, yaw}` | `Go2Connection` |
| `sensor.lidar` | `{points, min_distance}` | `Go2Connection` |
| `sensor.speed` | `{vx, vy, vyaw}` | `Go2Connection` |
| `sensor.foot_force` | `{fl, fr, rl, rr}` | `Go2Connection` |
| `sensor.camera` | frame para relay WebRTC | `Go2Connection` |
| `robot.posture` | `standing` / `sitting` / `damping` / `recovery` / `unknown` | `Go2Connection` |
| `agent.action` | `{tool, params, result, timestamp}` | Tools del agente |
| `agent.reasoning` | `{thought, plan}` | Agente ADK |
| `agent.alert` | `{level, message, timestamp}` | Tools / Agente |

---

## Fase 0 — Configuración del entorno

**Objetivo:** tener todo instalado y el repositorio listo antes de escribir una sola línea del agente.

- [ ] Repositorio creado en GitHub con la estructura de carpetas definida en `README.md`
- [ ] Python 3.10+ instalado
- [ ] Entorno virtual creado (`python -m venv .venv`)
- [ ] `go2-webrtc-connect` instalado (`pip install go2-webrtc-connect`)
- [ ] Google ADK instalado (`pip install google-adk`)
- [ ] API Key de Gemini obtenida desde https://aistudio.google.com
- [ ] Archivo `.env` creado con `ROBOT_IP`, `ROBOT_SERIAL`, `GEMINI_API_KEY`
- [ ] `.env` en el `.gitignore`
- [ ] `requirements.txt` generado (`pip freeze > requirements.txt`)

### Dashboard — Fase 0
- [ ] Agregar al `requirements.txt`: `fastapi`, `uvicorn[standard]`, `aiortc`, `python-multipart`
- [ ] Crear estructura `web_dashboard/`:
  ```
  web_dashboard/
  ├── __init__.py
  ├── event_bus.py          # Pub/sub asíncrono (asyncio.Queue)
  ├── server.py              # FastAPI + WebSocket + relay WebRTC
  └── static/
      ├── index.html         # Dashboard principal
      ├── dashboard.js       # Lógica WebSocket + Chart.js + Canvas
      └── style.css          # Tema oscuro, responsive
  ```

---

## Fase 1 — Conexión básica con el robot

**Objetivo:** conectarse al Go2 y ejecutar un comando simple sin ningún agente. Solo Python puro + la librería WebRTC.

- [ ] Encontrar la IP del robot en la red de DUOC (ver `docs/05_conexion_webrtc.md`)
- [ ] Cerrar la app Unitree Go en el celular
- [ ] Correr el ejemplo básico del repo `unitree_webrtc_connect`
- [ ] El robot ejecuta `stand_up()` desde un script propio en `tests/test_connection.py`
- [ ] El robot ejecuta `sit()` desde el mismo script
- [ ] El robot ejecuta `move(vx=0.3, vy=0, vyaw=0)` durante 2 segundos y se detiene

✅ **Criterio de éxito:** el robot obedece comandos desde un script Python sin la app.

### Dashboard — Fase 1
- [ ] `event_bus.py`: implementar clase `EventBus` con métodos `publish(topic, data)` y `subscribe(topic) → AsyncIterator`
- [ ] `Go2Connection` recibe `EventBus` en constructor y publica `connection.state`
- [ ] `server.py`: endpoint WebSocket `/ws` que transmite eventos del bus a clientes conectados
- [ ] `index.html` inicial: widget de **estado de conexión** (🟢 conectado / 🔴 desconectado) + indicador de postura del robot
- [ ] `main.py`: levanta el dashboard con `uvicorn` en background al iniciar

✅ **Criterio de éxito dashboard:** abrir `http://localhost:8000` y ver el estado de conexión cambiar en tiempo real al conectar/desconectar el robot.

---

## Fase 2 — Lectura de sensores

**Objetivo:** poder leer datos del robot (no solo enviar comandos).

- [ ] Leer y mostrar en consola el estado de batería
- [ ] Capturar y guardar un frame de la cámara como imagen
- [ ] Leer y mostrar datos básicos del LiDAR (distancia mínima al objeto más cercano)
- [ ] Leer estado del IMU (acelerómetro + giroscopio)

✅ **Criterio de éxito:** script que imprime en consola: batería, distancia LiDAR, orientación IMU, y guarda una foto del punto de vista del robot.

### Dashboard — Fase 2
- [ ] `Go2Connection` publica eventos `sensor.*` en cada lectura de sensores
- [ ] Widgets en el dashboard:
  - 🔋 **Batería**: barra de progreso circular con %, voltaje, temperatura
  - 📐 **IMU**: valores numéricos de roll/pitch/yaw + indicador de estabilidad
  - 📡 **LiDAR**: canvas con vista cenital de puntos (top-down scatter plot, actualización en tiempo real) + badge con distancia mínima
  - 📷 **Cámara**: stream de video vía relay WebRTC (`aiortc` recibe frames del robot → browser como peer WebRTC)
  - 📊 **Gráfica de velocidad**: Chart.js time-series (últimos 30s) para vx, vy, vyaw

✅ **Criterio de éxito dashboard:** todos los widgets muestran datos reales del robot actualizándose en tiempo real.

---

## Fase 3 — Wrapper de conexión

**Objetivo:** abstraer la conexión y los comandos en `robot/connection.py` para que las tools del agente sean simples.

- [ ] Crear clase `Go2Connection` con métodos:
  - `connect()` / `disconnect()`
  - Todos los movimientos de `docs/03_movimientos_y_tools.md`
  - Todos los sensores de `docs/04_sensores.md`
- [ ] Manejar el caso de conexión perdida (reconexión automática)
- [ ] Manejar el timeout si el robot no responde
- [ ] Probar la clase desde `tests/test_connection.py`

✅ **Criterio de éxito:** se puede importar `Go2Connection` y usarla sin pensar en WebRTC.

### Dashboard — Fase 3
- [ ] Todos los métodos de `Go2Connection` publican su evento correspondiente vía `EventBus`
- [ ] Evento `robot.posture` al cambiar postura (stand/sit/damp/etc.)
- [ ] Evento `connection.state` con todos los estados: `connected`, `disconnected`, `reconnecting`, `error`
- [ ] Dashboard muestra:
  - **Log de eventos**: últimas 50 líneas scrollables con timestamp y tipo de evento
  - **Widget de alertas**: toast/popup cuando `connection.state = error` o `reconnecting`

✅ **Criterio de éxito dashboard:** el log de eventos refleja cada acción del wrapper; las alertas aparecen si se pierde la conexión.

---

## Fase 4 — Tools del agente (movimientos básicos)

**Objetivo:** mapear los movimientos más importantes como tools de Google ADK.

Tools a implementar primero (las más útiles para demostrar):
- [ ] `stand_up` / `stand_down`
- [ ] `sit` / `rise_sit`
- [ ] `move_forward(speed, duration)`
- [ ] `move_backward(speed, duration)`
- [ ] `turn_right(degrees)` / `turn_left(degrees)`
- [ ] `stop_move`
- [ ] `hello` / `stretch`
- [ ] `get_battery_state`

Cada tool debe tener:
- [ ] Descripción clara en lenguaje natural (para que Gemini la entienda)
- [ ] Parámetros con tipos y valores por defecto sensatos
- [ ] Manejo de errores básico
- [ ] Return con mensaje descriptivo de lo que hizo

✅ **Criterio de éxito:** el agente puede recibir "párate, camina adelante 3 segundos y siéntate" y ejecutarlo correctamente.

### Dashboard — Fase 4
- [ ] Las tools publican evento `agent.action` al ejecutarse: `{tool, params, result, timestamp}`
- [ ] Dashboard muestra:
  - **Log de acciones**: lista cronológica de tools ejecutadas por el agente (nombre + parámetros + resultado)
  - **Instrucción actual**: qué dijo el usuario y qué se está ejecutando ahora
  - **Panel de movimiento**: flecha visual indicando dirección y velocidad del movimiento en curso
- [ ] Chart.js: timeline de acciones ejecutadas vs tiempo

✅ **Criterio de éxito dashboard:** dar una instrucción al agente y ver cada paso ejecutado aparecer en el log de acciones en tiempo real.

---

## Fase 5 — Tools de sensores

**Objetivo:** que el agente pueda percibir el entorno, no solo actuar.

- [ ] `get_battery_state()` — porcentaje y voltaje
- [ ] `get_camera_frame()` — captura imagen actual
- [ ] `describe_surroundings()` — frame → Gemini Vision → descripción en lenguaje natural
- [ ] `check_obstacle_ahead(threshold_meters)` — LiDAR → booleano
- [ ] `get_min_distance()` — distancia al objeto más cercano
- [ ] `is_robot_stable()` — IMU → booleano

✅ **Criterio de éxito:** el agente puede responder "¿qué ves adelante?" y "¿cuánta batería tienes?" con datos reales del robot.

### Dashboard — Fase 5
- [ ] El agente publica `agent.reasoning` con su pensamiento actual (qué tool va a llamar y por qué)
- [ ] Dashboard muestra:
  - **Panel de razonamiento**: burbuja de texto actualizable con lo que Gemini está "pensando" en ese momento
  - **Visor de cámara con overlay**: cuando `describe_surroundings` se ejecuta, mostrar la descripción textual sobre el video
  - **Indicador de obstáculo**: semáforo (🟢 libre / 🟡 cerca / 🔴 obstáculo) basado en `check_obstacle_ahead`
  - **Gráfica de batería histórica**: Chart.js mostrando % de batería en el tiempo (toda la sesión)
  - **Indicador de estabilidad**: robot estable/inclinado/caído basado en `is_robot_stable()`

✅ **Criterio de éxito dashboard:** preguntar "¿qué ves?" y ver la descripción aparecer sobre el video; el semáforo de obstáculo cambia según el LiDAR.

---

## Fase 6 — Agente completo con comportamientos autónomos

**Objetivo:** el agente puede ejecutar instrucciones complejas que requieren razonamiento y uso de sensores en un loop.

Ejemplos de comportamientos a probar:
- [ ] "Camina hasta encontrar un obstáculo" → loop LiDAR + movimiento
- [ ] "Explora la sala y dime qué hay" → movimiento + cámara + descripción
- [ ] "Haz una demostración" → secuencia de movimientos predefinida
- [ ] "Guarda energía" → verifica batería y ajusta comportamiento

- [ ] Definir el system prompt del agente con instrucciones de seguridad
- [ ] Agregar herramienta de emergencia `stop_move` con prioridad alta
- [ ] Probar instrucciones ambiguas y ver cómo responde el agente
- [ ] Probar instrucciones imposibles y ver que el agente las maneje bien

✅ **Criterio de éxito:** el agente puede operar 10 minutos seguidos con instrucciones variadas sin errores.

### Dashboard — Fase 6
- [ ] Evento `agent.alert`: alertas de seguridad (batería <20%, obstáculo detectado, robot caído)
- [ ] Dashboard muestra:
  - **Panel de misión**: objetivo actual de la misión autónoma ("explorar sala", "buscar obstáculo", etc.)
  - **Panel de seguridad**: indicador de nivel de seguridad + lista de alertas activas con código de colores (🟢/🟡/🔴)
  - **Timeline de misión**: gráfica de barras horizontal mostrando secuencia de acciones en el tiempo
  - **Estadísticas de sesión**: distancia total recorrida, comandos ejecutados, tiempo activo
  - **Botón STOP de emergencia**: botón rojo prominente que publica `emergency_stop` vía WebSocket, ejecutando `stop_move` con máxima prioridad
- [ ] WebSocket bidireccional: el dashboard puede enviar comandos al agente (no solo recibir)

✅ **Criterio de éxito dashboard:** durante una misión autónoma de 10 min, el dashboard muestra misión, alertas, estadísticas y el botón STOP funciona instantáneamente.

---

## Fase 7 — Pulido y documentación final

**Objetivo:** dejar el proyecto en un estado presentable y reproducible.

- [ ] Documentar todos los métodos del wrapper con docstrings
- [ ] Crear un video demo corto del agente funcionando
- [ ] Actualizar el `README.md` con instrucciones de instalación paso a paso
- [ ] Agregar sección de troubleshooting con los problemas que surgieron
- [ ] Agregar `CHANGELOG.md` con lo que se fue construyendo
- [ ] Revisar que el repo funciona desde cero en otro equipo

### Dashboard — Fase 7
- [ ] Dashboard responsive (funciona en tablet/celular para monitoreo en terreno)
- [ ] Tema oscuro como default (mejor visibilidad en interiores y laboratorio)
- [ ] Exportar log de sesión como archivo CSV/JSON descargable desde el dashboard
- [ ] Incluir screenshots del dashboard en el `README.md`
- [ ] Agregar sección "Dashboard web" en troubleshooting (puerto ocupado, CORS, firewall, etc.)
- [ ] Probar el dashboard con múltiples clientes conectados simultáneamente

---

## Orden sugerido de trabajo por sesión

| Sesión | Fases | Estimación |
|---|---|---|
| 1 | Fase 0 + Fase 1 | 3-4 horas |
| 2 | Fase 2 + Fase 3 | 4-5 horas |
| 3 | Fase 4 (tools de movimiento) | 3-4 horas |
| 4 | Fase 5 (tools de sensores) | 4-5 horas |
| 5 | Fase 6 (agente autónomo completo) | 5-6 horas |
| 6 | Fase 7 (pulido y documentación) | 3-4 horas |

---

## Problemas conocidos a tener en cuenta

| Problema | Solución |
|---|---|
| App del celular conectada al robot | Cerrar la app antes de correr el agente |
| Robot en posición incorrecta | Llamar `recovery_stand()` primero |
| LiDAR no entrega datos | Verificar que el robot está en modo activo (no damp) |
| Latencia alta en los comandos | Normal vía WebRTC, esperar ~100-200ms por comando |
| Robot se cae durante movimientos rápidos | Bajar velocidad, usar `set_speed_level(0)` |
| Batería baja (<20%) | No ejecutar flips ni saltos, solo movimientos suaves |
| Puerto 8000 ocupado al iniciar dashboard | Cambiar `DASHBOARD_PORT` en `.env` o detener el proceso existente |
| CORS bloqueado en el navegador | FastAPI configurado con `CORSMiddleware`, verificar origen |
| Firewall bloquea WebSocket | Usar `localhost` en desarrollo; en red local, abrir puerto en firewall |
| Robot solo acepta una conexión WebRTC | El dashboard usa la misma conexión que el agente vía EventBus, no abre una segunda |

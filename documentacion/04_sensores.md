# 04 — Sensores disponibles

Todos los datos que el robot puede enviar de vuelta al agente, lo que le permite percibir su entorno y tomar decisiones informadas.

---

## Sensores del Unitree Go2

### 1. Cámara frontal

| Propiedad | Detalle |
|---|---|
| Tipo | Cámara RGB de color |
| Posición | Cabeza del robot, orientada al frente |
| Acceso | Canal de video WebRTC (solo lectura) |
| Formato | Stream de video en tiempo real |
| Disponibilidad | Air, Pro y EDU |

**Cómo leerla:** El canal WebRTC de video se suscribe como stream. Para el agente, la tool `get_camera_frame()` captura un frame y puede pasárselo a Gemini Vision para que describa lo que ve el robot.

**Tool del agente:**
```
get_camera_frame() → imagen actual desde la perspectiva del robot
describe_surroundings() → obtiene frame + pide a Gemini que describa la escena
```

**Caso de uso:** "¿Qué ves adelante?" → el agente captura un frame y Gemini lo analiza.

---

### 2. LiDAR 4D (L1)

| Propiedad | Detalle |
|---|---|
| Tipo | 4D LiDAR L1 |
| Posición | Cabeza del robot |
| Cobertura | 360° horizontal × 90° vertical (hemiesférico) |
| Salida | Nube de puntos 3D (PointCloud) |
| Uso principal | Detección de obstáculos, mapeo |
| Disponibilidad | Air, Pro y EDU |

**Cómo leerlo:** La librería `unitree_webrtc_connect` incluye un decoder de LiDAR integrado que entrega `PointCloud` decodificado directamente.

**Tool del agente:**
```
get_lidar_data() → nube de puntos actual
check_obstacle_ahead() → ¿hay algo a menos de X metros adelante?
get_min_distance() → distancia al objeto más cercano
```

**Caso de uso:** "¿Hay espacio para caminar?" → el agente lee el LiDAR y decide si es seguro moverse.

---

### 3. IMU (Unidad de Medición Inercial)

| Propiedad | Detalle |
|---|---|
| Datos disponibles | Acelerómetro (x, y, z) + Giroscopio (x, y, z) |
| Frecuencia | ~500 Hz |
| Acceso | Vía `LowState` DDS topic (con WebRTC) |

**Tool del agente:**
```
get_imu_state() → aceleración y velocidad angular actuales
is_robot_stable() → ¿está el robot en equilibrio?
get_orientation() → ángulos de inclinación actuales (roll, pitch, yaw)
```

**Caso de uso:** Verificar si el robot está en posición estable antes de ejecutar un movimiento brusco.

---

### 4. Sensores de fuerza en pies

| Propiedad | Detalle |
|---|---|
| Cantidad | 4 sensores (uno por pata) |
| Datos | Fuerza de contacto en Newtons |
| Disponibilidad | Principalmente EDU; en Air/Pro disponible vía LowState |

**Tool del agente:**
```
get_foot_force() → fuerza en cada uno de los 4 pies
is_foot_in_contact(foot_id) → ¿tiene contacto esa pata con el suelo?
```

**Caso de uso:** Detectar si el robot está parado correctamente o si alguna pata está en el aire.

---

### 5. Estado de la batería

| Propiedad | Detalle |
|---|---|
| Datos | Porcentaje de carga, voltaje, temperatura |
| Acceso | Vía `RobotState` / `BasicClient` |

**Tool del agente:**
```
get_battery_state() → porcentaje de batería, voltaje, temperatura
```

**Caso de uso:** "¿Cuánta batería tienes?" o para que el agente advierta si la batería baja de un umbral.

---

### 6. Velocidad y odometría

| Propiedad | Detalle |
|---|---|
| Datos | Velocidad lineal (vx, vy) y angular (vyaw) actuales |
| Acceso | Vía `SportState` / estado del robot |

**Tool del agente:**
```
get_speed_state() → velocidad lineal y angular actuales del robot
get_position_estimate() → estimación de posición relativa desde el inicio
```

---

### 7. Audio (Pro y EDU solamente)

| Propiedad | Detalle |
|---|---|
| Hardware | Micrófono integrado + altavoz de 3W |
| Acceso | Canal de audio WebRTC (send/recv) |
| Disponibilidad | Pro y EDU únicamente (Air no tiene) |

**Tool del agente:**
```
play_audio(file_path) → reproduce un audio por el altavoz del robot
record_audio(duration) → graba audio desde el micrófono del robot
```

**Nota:** La librería `unitree_webrtc_connect` incluye soporte de audio. Requiere instalar `portaudio19-dev` en el sistema.

---

## Resumen de disponibilidad por modelo

| Sensor | Air | Pro | EDU |
|---|---|---|---|
| Cámara frontal | ✅ | ✅ | ✅ |
| LiDAR 4D | ✅ | ✅ | ✅ |
| IMU | ✅ | ✅ | ✅ |
| Batería | ✅ | ✅ | ✅ |
| Velocidad/odometría | ✅ | ✅ | ✅ |
| Sensores de fuerza en pies | ⚠️ parcial | ⚠️ parcial | ✅ |
| Audio (mic + speaker) | ❌ | ✅ | ✅ |

---

## Cómo el agente usa los sensores

Los sensores permiten que el agente tome decisiones con contexto real del entorno, no solo ejecute comandos a ciegas.

**Ejemplo de razonamiento con sensores:**
```
Usuario: "Camina hacia adelante hasta que encuentres un obstáculo"

Agente:
1. Llama get_lidar_data() → no hay obstáculo cercano
2. Llama move_forward(speed=0.3)
3. Loop: cada 0.5s llama check_obstacle_ahead()
4. Cuando detecta obstáculo a < 0.5m → llama stop_move()
5. Responde: "Caminé X metros y encontré un obstáculo a 0.3m adelante."
```

Esto transforma el agente de un ejecutor de comandos en un robot verdaderamente autónomo que percibe y reacciona a su entorno.

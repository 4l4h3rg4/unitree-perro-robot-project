# 03 — Movimientos disponibles y mapeo como tools

Todos los comandos de movimiento del Unitree Go2, extraídos del `sport_client` oficial, con su descripción, parámetros y cómo se convierten en tools para el agente.

Fuente directa: https://github.com/unitreerobotics/unitree_sdk2/blob/main/include/unitree/robot/go2/sport/sport_client.hpp

---

## Categorías de movimiento

### 1. Control de postura básica

| Método SDK | Tool del agente | Descripción |
|---|---|---|
| `StandUp()` | `stand_up` | El robot se pone de pie desde el suelo |
| `StandDown()` | `stand_down` | El robot baja al suelo de manera controlada |
| `Sit()` | `sit` | El robot se sienta |
| `RiseSit()` | `rise_sit` | Alterna entre sentado y parado |
| `BalanceStand()` | `balance_stand` | Se para en postura de equilibrio estable |
| `RecoveryStand()` | `recovery_stand` | Se recupera si cayó o está en posición incorrecta |
| `Damp()` | `damp` | Relaja todos los motores (estado de reposo) |

---

### 2. Movimiento y desplazamiento

| Método SDK | Tool del agente | Parámetros | Descripción |
|---|---|---|---|
| `Move(vx, vy, vyaw)` | `move` | `vx`: velocidad adelante/atrás (-1 a 1 m/s), `vy`: velocidad lateral (-1 a 1 m/s), `vyaw`: velocidad de giro (-1 a 1 rad/s) | Movimiento continuo en cualquier dirección |
| `StopMove()` | `stop_move` | — | Detiene cualquier movimiento en curso |
| `SpeedLevel(level)` | `set_speed_level` | `level`: 0 (lento), 1 (normal), 2 (rápido) | Ajusta la velocidad máxima global |

**Valores de referencia para `Move`:**
- Caminar adelante: `move(vx=0.5, vy=0, vyaw=0)`
- Caminar atrás: `move(vx=-0.5, vy=0, vyaw=0)`
- Desplazarse a la derecha: `move(vx=0, vy=-0.3, vyaw=0)`
- Desplazarse a la izquierda: `move(vx=0, vy=0.3, vyaw=0)`
- Girar en el lugar (derecha): `move(vx=0, vy=0, vyaw=-0.5)`
- Girar en el lugar (izquierda): `move(vx=0, vy=0, vyaw=0.5)`
- Velocidad máxima recomendada en interiores: `vx=0.6`, evitar > 1.0

---

### 3. Control de orientación y postura del cuerpo

| Método SDK | Tool del agente | Parámetros | Descripción |
|---|---|---|---|
| `Euler(roll, pitch, yaw)` | `set_body_orientation` | Ángulos en radianes | Inclina el cuerpo del robot en 3 ejes |
| `Pose(flag)` | `pose` | `flag`: True/False | Activa/desactiva modo de pose manual |

---

### 4. Acciones y movimientos predefinidos (alto interés para el agente)

| Método SDK | Tool del agente | Descripción |
|---|---|---|
| `Hello()` | `hello` | El robot saluda moviendo una pata |
| `Stretch()` | `stretch` | El robot se estira como si despertara |
| `Scrape()` | `scrape` | El robot rasca el suelo con una pata |
| `FrontFlip()` | `front_flip` | Voltereta hacia adelante (⚠️ solo en superficie libre) |
| `FrontJump()` | `front_jump` | Salto hacia adelante |
| `FrontPounce()` | `front_pounce` | Abalanzarse hacia adelante |
| `Content()` | `content` | Expresión de satisfacción/contento |
| `Heart()` | `heart` | Expresión de afecto |

> ⚠️ `FrontFlip`, `FrontJump` y `FrontPounce` requieren espacio libre alrededor del robot. No ejecutar en espacios reducidos o con personas cerca.

---

### 5. Modos especiales

| Método SDK | Tool del agente | Descripción |
|---|---|---|
| `SwitchJoystick(flag)` | `toggle_joystick` | Activa/desactiva el control por joystick físico |

---

## Cómo se mapean como tools en Google ADK

Cada movimiento se convierte en una función Python con una descripción clara para que Gemini sepa cuándo invocarla.

Estructura de una tool de movimiento:

```python
# Ejemplo de estructura (sin código funcional completo)
def move_forward(speed: float = 0.5, duration: float = 2.0) -> str:
    """
    Mueve el robot hacia adelante.
    
    Args:
        speed: velocidad de avance entre 0.1 (muy lento) y 1.0 (máximo).
               Valor recomendado en interiores: 0.5
        duration: tiempo en segundos que debe caminar
    
    Returns:
        Confirmación del movimiento ejecutado
    """
    ...
```

La descripción de la tool es lo más importante — Gemini la lee para decidir cuándo y cómo usarla.

---

## Tools compuestas (combinaciones útiles)

Además de las tools básicas 1:1 con el SDK, conviene crear tools compuestas para instrucciones frecuentes:

| Tool compuesta | Descripción | Equivale a |
|---|---|---|
| `move_forward(speed, duration)` | Camina hacia adelante X segundos | `move(vx=speed)` + espera + `stop_move()` |
| `move_backward(speed, duration)` | Camina hacia atrás X segundos | `move(vx=-speed)` + espera + `stop_move()` |
| `turn_right(degrees)` | Gira a la derecha N grados | `move(vyaw=-X)` calibrado |
| `turn_left(degrees)` | Gira a la izquierda N grados | `move(vyaw=X)` calibrado |
| `move_sideways(direction, duration)` | Se mueve lateralmente | `move(vy=±X)` + espera + `stop_move()` |

---

## Consideraciones de seguridad

- Siempre tener `stop_move()` como tool disponible para el agente
- Definir velocidades máximas en el wrapper, no dejar que Gemini las elija libremente
- Para `FrontFlip` y similares, agregar en la descripción de la tool: "solo ejecutar si el usuario confirma que hay espacio libre"
- El robot tiene sensores de fuerza en los pies — si cae, usar `recovery_stand()`

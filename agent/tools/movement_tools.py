import asyncio
import time
from typing import Optional


class MovementTools:
    """
    Tools de movimiento para Google ADK.
    Cada metodo es una tool que Gemini puede invocar con lenguaje natural.
    """

    def __init__(self, robot):
        self._robot = robot
        self._event_bus = getattr(robot, "_event_bus", None)

    def _emit(self, tool: str, params: dict, result: str):
        if self._event_bus:
            self._event_bus.publish("agent.action", {
                "tool": tool,
                "params": params,
                "result": result,
                "timestamp": time.time(),
            })

    async def stand_up(self) -> str:
        """Pone al robot de pie desde cualquier posicion. Usar cuando el robot esta en el suelo, damp, o sentado y se necesita que camine."""
        await self._robot.stand_up()
        if self._event_bus:
            self._event_bus.publish("robot.posture", "standing")
        self._emit("stand_up", {}, "Robot de pie")
        return "Me puse de pie."

    async def stand_down(self) -> str:
        """Baja al robot al suelo de manera controlada. Usar cuando se quiere que el robot descanse completamente."""
        await self._robot.stand_down()
        if self._event_bus:
            self._event_bus.publish("robot.posture", "lying")
        self._emit("stand_down", {}, "Robot en el suelo")
        return "Baje al suelo."

    async def sit(self) -> str:
        """Sienta al robot. Postura de descanso intermedia entre parado y suelo."""
        await self._robot.sit()
        if self._event_bus:
            self._event_bus.publish("robot.posture", "sitting")
        self._emit("sit", {}, "Robot sentado")
        return "Me sente."

    async def rise_sit(self) -> str:
        """Alterna entre sentado y parado. Si esta sentado se para, si esta parado se sienta."""
        await self._robot.rise_sit()
        self._emit("rise_sit", {}, "Alternado sentado/parado")
        return "Alterne entre sentado y parado."

    async def recovery_stand(self) -> str:
        """Recupera al robot si se cayo o esta en posicion incorrecta. Usar despues de una caida."""
        await self._robot.recovery_stand()
        if self._event_bus:
            self._event_bus.publish("robot.posture", "standing")
        self._emit("recovery_stand", {}, "Robot recuperado")
        return "Me recupere y estoy de pie."

    async def damp(self) -> str:
        """Relaja todos los motores. El robot queda inerte. Usar para guardar energia o al finalizar."""
        await self._robot.damp()
        if self._event_bus:
            self._event_bus.publish("robot.posture", "damping")
        self._emit("damp", {}, "Motores relajados")
        return "Motores relajados en modo damp."

    async def stop_move(self) -> str:
        """Detiene inmediatamente cualquier movimiento en curso. COMANDO DE EMERGENCIA con maxima prioridad."""
        await self._robot.stop_move()
        self._emit("stop_move", {}, "Movimiento detenido (EMERGENCIA)")
        return "Movimiento detenido de emergencia."

    async def move_forward(self, speed: float = 0.5, duration: float = 2.0) -> str:
        """Mueve el robot hacia adelante por un tiempo determinado.

        Args:
            speed: Velocidad entre 0.1 (muy lento) y 1.0 (rapido). Recomendado en interiores: 0.3-0.5
            duration: Tiempo en segundos que debe caminar. Maximo 10s por seguridad.
        """
        speed = max(0.1, min(1.0, speed))
        duration = max(0.5, min(10.0, duration))
        await self._robot.move(vx=speed, vy=0, vyaw=0)
        await asyncio.sleep(duration)
        await self._robot.stop_move()
        self._emit("move_forward", {"speed": speed, "duration": duration},
                   f"Camine {duration}s adelante a velocidad {speed}")
        return f"Camine hacia adelante {duration} segundos a velocidad {speed}."

    async def move_backward(self, speed: float = 0.3, duration: float = 2.0) -> str:
        """Mueve el robot hacia atras por un tiempo determinado.

        Args:
            speed: Velocidad entre 0.1 y 1.0. Recomendado 0.3 en interiores.
            duration: Tiempo en segundos.
        """
        speed = max(0.1, min(1.0, speed))
        duration = max(0.5, min(10.0, duration))
        await self._robot.move(vx=-speed, vy=0, vyaw=0)
        await asyncio.sleep(duration)
        await self._robot.stop_move()
        self._emit("move_backward", {"speed": speed, "duration": duration},
                   f"Camine {duration}s atras")
        return f"Camine hacia atras {duration} segundos."

    async def turn_left(self, degrees: float = 90.0) -> str:
        """Gira el robot hacia la izquierda N grados.

        Args:
            degrees: Angulo en grados (positivo = izquierda). Ej: 90 para cuarto de vuelta.
        """
        degrees = max(10.0, min(360.0, degrees))
        vyaw = 0.5
        duration = (degrees / 360.0) * (2 * 3.1416) / vyaw
        duration = max(0.5, min(10.0, duration))
        await self._robot.move(vx=0, vy=0, vyaw=vyaw)
        await asyncio.sleep(duration)
        await self._robot.stop_move()
        self._emit("turn_left", {"degrees": degrees, "duration": duration},
                   f"Gire {degrees}° izquierda")
        return f"Gire {degrees} grados a la izquierda."

    async def turn_right(self, degrees: float = 90.0) -> str:
        """Gira el robot hacia la derecha N grados.

        Args:
            degrees: Angulo en grados (positivo = derecha). Ej: 90 para cuarto de vuelta.
        """
        degrees = max(10.0, min(360.0, degrees))
        vyaw = -0.5
        duration = (degrees / 360.0) * (2 * 3.1416) / 0.5
        duration = max(0.5, min(10.0, duration))
        await self._robot.move(vx=0, vy=0, vyaw=vyaw)
        await asyncio.sleep(duration)
        await self._robot.stop_move()
        self._emit("turn_right", {"degrees": degrees, "duration": duration},
                   f"Gire {degrees}° derecha")
        return f"Gire {degrees} grados a la derecha."

    async def hello(self) -> str:
        """El robot saluda moviendo una pata. Expresion amistosa."""
        await self._robot.hello()
        self._emit("hello", {}, "Saludo ejecutado")
        return "Hice el saludo."

    async def stretch(self) -> str:
        """El robot se estira como si despertara. Expresion de estiramiento."""
        await self._robot.stretch()
        self._emit("stretch", {}, "Estiramiento ejecutado")
        return "Me estire."

    async def front_flip(self) -> str:
        """Voltereta hacia adelante. SOLO si hay espacio libre alrededor (>2m) y bateria > 20%."""
        await self._robot.front_flip()
        self._emit("front_flip", {}, "Voltereta ejecutada")
        return "Hice una voltereta hacia adelante."

    async def front_jump(self) -> str:
        """Salto hacia adelante. SOLO si hay espacio libre y bateria > 20%."""
        await self._robot.front_jump()
        self._emit("front_jump", {}, "Salto ejecutado")
        return "Salte hacia adelante."

    async def content(self) -> str:
        """Expresion de satisfaccion. El robot muestra que esta contento."""
        await self._robot.content()
        self._emit("content", {}, "Expresion de contento")
        return "Estoy contento."

    async def dance(self) -> str:
        """El robot baila una secuencia de movimientos predefinida."""
        await self._robot.dance1()
        self._emit("dance", {}, "Baile ejecutado")
        return "Baile completo."

    async def set_speed_level(self, level: int = 1) -> str:
        """Ajusta la velocidad maxima global del robot.

        Args:
            level: 0 (lento/seguro), 1 (normal), 2 (rapido). Recomendado 0 en interiores.
        """
        level = max(0, min(2, level))
        await self._robot.set_speed_level(level)
        nombres = {0: "lento", 1: "normal", 2: "rapido"}
        self._emit("set_speed_level", {"level": level}, f"Nivel velocidad: {nombres.get(level, level)}")
        return f"Nivel de velocidad ajustado a {nombres.get(level, level)}."

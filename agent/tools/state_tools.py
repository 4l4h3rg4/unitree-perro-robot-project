import time
from typing import Optional


class StateTools:
    """
    Tools de estado del robot para Google ADK.
    Informacion general del robot: velocidad, posicion, postura.
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

    async def get_speed_state(self) -> str:
        """Lee la velocidad actual del robot: lineal (vx, vy) y angular (vyaw)."""
        speed = await self._robot.get_speed_state()
        self._emit("get_speed_state", {},
                   f"Velocidad: vx={speed['vx']:.2f}, vy={speed['vy']:.2f}, vyaw={speed['vyaw']:.2f}")
        return (f"Velocidad actual: adelante/atras={speed['vx']:.2f} m/s, "
                f"lateral={speed['vy']:.2f} m/s, giro={speed['vyaw']:.2f} rad/s")

    async def get_robot_status(self) -> str:
        """Obtiene un resumen completo del estado del robot: bateria, orientacion, velocidad y obstaculos."""
        try:
            battery = await self._robot.get_battery_state()
        except Exception:
            battery = {"percentage": 0, "voltage": 0, "temperature": 0}

        try:
            imu = await self._robot.get_imu_state()
        except Exception:
            imu = {}

        try:
            speed = await self._robot.get_speed_state()
        except Exception:
            speed = {"vx": 0, "vy": 0, "vyaw": 0}

        try:
            lidar = await self._robot.get_lidar_data()
        except Exception:
            lidar = {"min_distance": float("inf")}

        msg = (
            f"Estado del robot:\n"
            f"  Bateria: {battery.get('percentage', '?')}% ({battery.get('voltage', '?')}V)\n"
            f"  Orientacion: roll={imu.get('roll', 0):.1f}°, pitch={imu.get('pitch', 0):.1f}°\n"
            f"  Velocidad: vx={speed.get('vx', 0):.2f}, vyaw={speed.get('vyaw', 0):.2f}\n"
            f"  Obstaculo mas cercano: {lidar.get('min_distance', float('inf')):.2f}m"
        )

        if lidar.get("min_distance", float("inf")) < 0.5:
            msg += "\n  ATENCION: Obstaculo cercano detectado."

        if battery.get("percentage", 0) < 20:
            msg += "\n  ADVERTENCIA: Bateria baja."
            if self._event_bus:
                self._event_bus.publish("agent.alert", {
                    "level": "warning",
                    "message": f"Bateria baja: {battery.get('percentage', 0)}%",
                    "timestamp": time.time(),
                })

        self._emit("get_robot_status", {}, "Estado completo obtenido")
        return msg

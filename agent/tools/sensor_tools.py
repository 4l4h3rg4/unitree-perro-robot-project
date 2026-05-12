import base64
import time
from io import BytesIO
from typing import Optional


class SensorTools:
    """
    Tools de sensores para Google ADK.
    Permiten al agente percibir su entorno y tomar decisiones informadas.
    """

    def __init__(self, robot, gemini_model=None):
        self._robot = robot
        self._gemini_model = gemini_model
        self._event_bus = getattr(robot, "_event_bus", None)

    def _emit(self, tool: str, params: dict, result: str):
        if self._event_bus:
            self._event_bus.publish("agent.action", {
                "tool": tool,
                "params": params,
                "result": result,
                "timestamp": time.time(),
            })

    async def get_battery_state(self) -> str:
        """Lee el estado de la bateria del robot: porcentaje, voltaje y temperatura."""
        battery = await self._robot.get_battery_state()
        pct = battery.get("percentage", 0)
        voltage = battery.get("voltage", 0)
        temp = battery.get("temperature", 0)
        self._emit("get_battery_state", {},
                   f"Bateria: {pct}%, {voltage}V, {temp}°C")
        return f"Bateria al {pct}% ({voltage}V, {temp}°C)."

    async def check_battery_safe(self) -> str:
        """Verifica si la bateria esta en nivel seguro para operar. Retorna advertencia si <20%."""
        battery = await self._robot.get_battery_state()
        pct = battery.get("percentage", 0)
        if pct < 10:
            if self._event_bus:
                self._event_bus.publish("agent.alert", {
                    "level": "critical",
                    "message": f"Bateria critica: {pct}%",
                    "timestamp": time.time(),
                })
            return f"BATERIA CRITICA al {pct}%. Solo movimientos esenciales. Busca cargador."
        elif pct < 20:
            if self._event_bus:
                self._event_bus.publish("agent.alert", {
                    "level": "warning",
                    "message": f"Bateria baja: {pct}%",
                    "timestamp": time.time(),
                })
            return f"Bateria baja al {pct}%. Evitar flips, saltos y movimientos bruscos."
        return f"Bateria en nivel seguro: {pct}%."

    async def get_imu_state(self) -> str:
        """Lee el estado del IMU: acelerometro, giroscopio y orientacion (roll, pitch, yaw)."""
        imu = await self._robot.get_imu_state()
        if not imu:
            return "No pude leer el IMU."
        roll = imu.get("roll", 0)
        pitch = imu.get("pitch", 0)
        yaw = imu.get("yaw", 0)
        self._emit("get_imu_state", {},
                   f"Orientacion: roll={roll:.1f}°, pitch={pitch:.1f}°, yaw={yaw:.1f}°")
        return f"Orientacion: roll={roll:.1f}°, pitch={pitch:.1f}°, yaw={yaw:.1f}°."

    async def is_robot_stable(self) -> str:
        """Verifica si el robot esta estable (no inclinado peligrosamente ni caido)."""
        imu = await self._robot.get_imu_state()
        if not imu:
            return "No pude verificar estabilidad."
        roll = abs(imu.get("roll", 0))
        pitch = abs(imu.get("pitch", 0))
        if roll > 45 or pitch > 45:
            if self._event_bus:
                self._event_bus.publish("agent.alert", {
                    "level": "warning",
                    "message": "Robot inestable o caido",
                    "timestamp": time.time(),
                })
            return "El robot NO esta estable (posible caida). Usar recovery_stand()."
        if roll > 20 or pitch > 20:
            return "El robot esta inclinado. Evitar movimientos bruscos hasta estabilizarse."
        return "El robot esta estable y en equilibrio."

    async def check_obstacle_ahead(self, threshold_meters: float = 0.5) -> str:
        """Verifica si hay un obstaculo adelante usando el LiDAR.

        Args:
            threshold_meters: Distancia minima en metros para considerar obstaculo. Default 0.5m.
        """
        lidar = await self._robot.get_lidar_data()
        min_dist = lidar.get("min_distance", float("inf"))
        point_count = lidar.get("point_count", 0)

        if min_dist < threshold_meters:
            if self._event_bus:
                self._event_bus.publish("agent.alert", {
                    "level": "warning",
                    "message": f"Obstaculo a {min_dist:.2f}m",
                    "timestamp": time.time(),
                })
            self._emit("check_obstacle_ahead", {"threshold": threshold_meters},
                       f"Obstaculo detectado a {min_dist:.2f}m")
            return f"OBSTACULO detectado a {min_dist:.2f} metros ({point_count} puntos LiDAR). No avanzar."
        self._emit("check_obstacle_ahead", {"threshold": threshold_meters},
                   f"Libre hasta {min_dist:.2f}m")
        return f"Camino libre. Distancia minima: {min_dist:.2f}m ({point_count} puntos LiDAR)."

    async def get_min_distance(self) -> str:
        """Obtiene la distancia al objeto mas cercano usando el LiDAR."""
        lidar = await self._robot.get_lidar_data()
        min_dist = lidar.get("min_distance", float("inf"))
        if min_dist == float("inf"):
            return "No se detectan objetos cercanos."
        self._emit("get_min_distance", {}, f"Objeto mas cercano a {min_dist:.2f}m")
        return f"El objeto mas cercano esta a {min_dist:.2f} metros."

    async def get_camera_frame(self) -> str:
        """Captura un frame de la camara del robot y lo convierte a base64 para analisis."""
        frame = self._robot.get_latest_frame()
        if frame is None:
            return "No hay frame de camara disponible. La camara podria estar apagada."

        try:
            img_bytes = frame.to_image().tobytes()
            img_format = "jpeg"
        except Exception:
            try:
                from PIL import Image
                import io
                buf = io.BytesIO()
                frame.to_image().save(buf, format="JPEG")
                img_bytes = buf.getvalue()
                img_format = "jpeg"
            except Exception:
                return "No pude procesar el frame de camara."

        b64 = base64.b64encode(img_bytes).decode("utf-8")
        self._emit("get_camera_frame", {}, "Frame capturado")
        return f"[FRAME:{img_format}:{b64}]"

    async def describe_surroundings(self) -> str:
        """Captura un frame de la camara y describe lo que ve el robot usando Vision.

        Requiere que el modelo Gemini tenga capacidad de vision (gemini-pro-vision o similar).
        """
        frame = self._robot.get_latest_frame()
        if frame is None:
            return "No puedo ver nada. La camara no tiene frames disponibles."

        if not self._gemini_model:
            return "No tengo capacidad de vision configurada."

        try:
            try:
                img_bytes = frame.to_image().tobytes()
            except Exception:
                from PIL import Image
                import io
                pil_img = frame.to_image()
                buf = io.BytesIO()
                pil_img.save(buf, format="JPEG")
                img_bytes = buf.getvalue()

            import base64 as b64
            image_b64 = b64.b64encode(img_bytes).decode("utf-8")

            try:
                from google import genai
                client = genai.Client()
                response = client.models.generate_content(
                    model=self._gemini_model,
                    contents=[
                        "Describe en espanol lo que ves en esta imagen desde la perspectiva de un perro robot. Se conciso (max 2 frases). Menciona personas, objetos, obstaculos y el tipo de entorno.",
                        {"inline_data": {"mime_type": "image/jpeg", "data": image_b64}},
                    ],
                )
                description = response.text
            except Exception:
                description = "No pude analizar la imagen con Vision."

            if self._event_bus:
                self._event_bus.publish("agent.reasoning", {
                    "thought": f"Analizando camara: {description}",
                    "plan": "describe_surroundings",
                })

            self._emit("describe_surroundings", {}, description)
            return f"Veo: {description}"
        except Exception as e:
            return f"No pude describir el entorno: {e}"

    async def get_foot_force(self) -> str:
        """Lee la fuerza en los 4 pies del robot en Newtons."""
        forces = await self._robot.get_foot_force()
        self._emit("get_foot_force", forces,
                   f"Fuerza pies: FL={forces['fl']:.1f}N, FR={forces['fr']:.1f}N, RL={forces['rl']:.1f}N, RR={forces['rr']:.1f}N")
        return (f"Fuerza en pies: Delantero izquierdo={forces['fl']:.1f}N, "
                f"Delantero derecho={forces['fr']:.1f}N, "
                f"Trasero izquierdo={forces['rl']:.1f}N, "
                f"Trasero derecho={forces['rr']:.1f}N")

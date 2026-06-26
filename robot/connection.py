import asyncio
import io
import json
import logging
import os
import sys
import time
import uuid
from typing import Any, Callable, Dict, Optional

from .webrtc_compat import apply_webrtc_compat_patch

apply_webrtc_compat_patch()

from go2_webrtc_driver.constants import DATA_CHANNEL_TYPE, RTC_TOPIC, SPORT_CMD
from go2_webrtc_driver.webrtc_driver import Go2WebRTCConnection, WebRTCConnectionMethod

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("Go2Connection")


class Go2Connection:
    """
    Wrapper de conexion WebRTC con el Unitree Go2.
    Abstrae toda la logica WebRTC y expone metodos simples para
    movimientos y sensores. Publica eventos al EventBus del dashboard.
    """

    def __init__(
        self,
        event_bus=None,
        ip: Optional[str] = None,
        serial_number: Optional[str] = None,
        connection_mode: str = "LocalSTA",
    ):
        self._event_bus = event_bus
        self._ip = ip or os.getenv("ROBOT_IP")
        self._serial = serial_number or os.getenv("ROBOT_SERIAL")
        self._conn_mode = connection_mode or os.getenv("ROBOT_CONNECTION_MODE", "LocalSTA")
        self._conn: Optional[Go2WebRTCConnection] = None
        self._connected = False
        self._latest_video_frame = None
        self._frame_callback: Optional[Callable] = None
        self._sensor_subscriptions = {}

    # ── conexion ──────────────────────────────────────────────

    async def connect(self) -> bool:
        self._emit("connection.state", "connecting")

        if self._conn_mode == "LocalAP":
            method = WebRTCConnectionMethod.LocalAP
        elif self._conn_mode == "LocalSTA":
            method = WebRTCConnectionMethod.LocalSTA
            if not self._ip and not self._serial:
                logger.error("LocalSTA requiere ROBOT_IP o ROBOT_SERIAL en .env")
                self._emit("connection.state", "error")
                return False
        elif self._conn_mode == "Remote":
            method = WebRTCConnectionMethod.Remote
        else:
            raise ValueError(f"Modo de conexion invalido: {self._conn_mode}")

        self._conn = Go2WebRTCConnection(
            method,
            serialNumber=self._serial if self._serial else None,
            ip=self._ip if self._ip else None,
        )

        try:
            await asyncio.wait_for(self._conn.connect(), timeout=10.0)
        except asyncio.TimeoutError:
            logger.error("Timeout conectando al robot (10s). Verifica IP y que el robot este encendido.")
            self._emit("connection.state", "error")
            return False
        except SystemExit:
            self._emit("connection.state", "error")
            return False
        except Exception as e:
            logger.error(f"Error de conexion: {e}")
            self._emit("connection.state", "error")
            return False

        self._connected = self._conn.isConnected
        if self._connected:
            self._video = self._conn.video
            self._datachannel = self._conn.datachannel
            self._pub_sub = self._datachannel.pub_sub
            self._setup_video_callback()
            self._emit("connection.state", "connected")
            return True
        self._emit("connection.state", "error")
        return False

    async def disconnect(self):
        self._connected = False
        self._emit("connection.state", "disconnected")
        if self._conn:
            await self._conn.disconnect()
            self._conn = None

    async def reconnect(self) -> bool:
        await self.disconnect()
        return await self.connect()

    @property
    def connected(self) -> bool:
        return self._connected

    # ── movimiento ────────────────────────────────────────────

    async def _send_sport_cmd(self, api_id: int, parameter: Any = None) -> Dict:
        if not self._connected or not self._pub_sub:
            raise ConnectionError("Robot no conectado")

        # Patron correcto del driver: publish_request_new arma el header con
        # api_id y resuelve el future con la respuesta "rt/api/sport/response".
        # (El publish() crudo con RTC_INNER_REQ no emparejaba la respuesta y
        # quedaba colgado para siempre.)
        options: Dict[str, Any] = {"api_id": api_id}
        if parameter is not None:
            options["parameter"] = parameter

        try:
            return await asyncio.wait_for(
                self._pub_sub.publish_request_new(RTC_TOPIC["SPORT_MOD"], options),
                timeout=5.0,
            )
        except asyncio.TimeoutError:
            logger.warning(f"Comando sport {api_id} sin respuesta (timeout)")
            return {}

    async def stand_up(self):
        return await self._send_sport_cmd(SPORT_CMD["StandUp"])

    async def stand_down(self):
        return await self._send_sport_cmd(SPORT_CMD["StandDown"])

    async def sit(self):
        return await self._send_sport_cmd(SPORT_CMD["Sit"])

    async def rise_sit(self):
        return await self._send_sport_cmd(SPORT_CMD["RiseSit"])

    async def balance_stand(self):
        return await self._send_sport_cmd(SPORT_CMD["BalanceStand"])

    async def recovery_stand(self):
        return await self._send_sport_cmd(SPORT_CMD["RecoveryStand"])

    async def damp(self):
        return await self._send_sport_cmd(SPORT_CMD["Damp"])

    async def stop_move(self):
        return await self._send_sport_cmd(SPORT_CMD["StopMove"])

    async def move(self, vx: float = 0.0, vy: float = 0.0, vyaw: float = 0.0):
        self._emit("sensor.speed", {"vx": vx, "vy": vy, "vyaw": vyaw})
        return await self._send_sport_cmd(SPORT_CMD["Move"], {"x": vx, "y": vy, "z": vyaw})

    async def set_speed_level(self, level: int = 1):
        return await self._send_sport_cmd(SPORT_CMD["SpeedLevel"], {"level": level})

    async def euler(self, roll: float = 0.0, pitch: float = 0.0, yaw: float = 0.0):
        return await self._send_sport_cmd(SPORT_CMD["Euler"], {"x": roll, "y": pitch, "z": yaw})

    async def pose(self, flag: bool = True):
        return await self._send_sport_cmd(SPORT_CMD["Pose"], {"flag": int(flag)})

    async def hello(self):
        return await self._send_sport_cmd(SPORT_CMD["Hello"])

    async def stretch(self):
        return await self._send_sport_cmd(SPORT_CMD["Stretch"])

    async def scrape(self):
        return await self._send_sport_cmd(SPORT_CMD["Scrape"])

    async def front_flip(self):
        return await self._send_sport_cmd(SPORT_CMD["FrontFlip"])

    async def front_jump(self):
        return await self._send_sport_cmd(SPORT_CMD["FrontJump"])

    async def front_pounce(self):
        return await self._send_sport_cmd(SPORT_CMD["FrontPounce"])

    async def content(self):
        return await self._send_sport_cmd(SPORT_CMD["Content"])

    async def heart(self):
        return await self._send_sport_cmd(SPORT_CMD["FingerHeart"])

    async def dance1(self):
        return await self._send_sport_cmd(SPORT_CMD["Dance1"])

    async def dance2(self):
        return await self._send_sport_cmd(SPORT_CMD["Dance2"])

    async def switch_joystick(self, flag: bool = True):
        return await self._send_sport_cmd(SPORT_CMD["SwitchJoystick"], {"flag": int(flag)})

    async def get_state(self):
        return await self._send_sport_cmd(SPORT_CMD["GetState"])

    async def wallow(self):
        return await self._send_sport_cmd(SPORT_CMD["Wallow"])

    async def wiggle_hips(self):
        return await self._send_sport_cmd(SPORT_CMD["WiggleHips"])

    async def body_height(self, height: float = 0.0):
        return await self._send_sport_cmd(SPORT_CMD["BodyHeight"], {"x": height})

    # ── sensores ──────────────────────────────────────────────

    async def get_battery_state(self) -> Dict[str, Any]:
        if not self._connected or not self._pub_sub:
            raise ConnectionError("Robot no conectado")

        try:
            response = await self._pub_sub.publish_request_new(
                RTC_TOPIC["MULTIPLE_STATE"],
                {"api_id": 0},
            )
            data = self._safe_extract(response, "data", "data") or {}
            battery = {
                "percentage": data.get("battery_percentage", 0),
                "voltage": data.get("battery_voltage", 0.0),
                "temperature": data.get("battery_temperature", 0),
            }
            self._emit("sensor.battery", battery)
            return battery
        except Exception as e:
            logger.error(f"Error leyendo bateria: {e}")
            return {"percentage": 0, "voltage": 0.0, "temperature": 0}

    async def get_imu_state(self) -> Dict[str, Any]:
        if not self._connected or not self._pub_sub:
            raise ConnectionError("Robot no conectado")

        try:
            response = await self._pub_sub.publish_request_new(
                RTC_TOPIC["LOW_STATE"],
                {"api_id": 0},
            )
            data = self._safe_extract(response, "data", "data") or {}
            imu_data = data.get("imu_state", {})
            if not imu_data:
                imu_raw = data.get("imu", {})
                imu_data = {
                    "accelerometer": imu_raw.get("accelerometer", [0, 0, 0]),
                    "gyroscope": imu_raw.get("gyroscope", [0, 0, 0]),
                    "quaternion": imu_raw.get("quaternion", [1, 0, 0, 0]),
                }

            accel = imu_data.get("accelerometer", [0, 0, 0])
            gyro = imu_data.get("gyroscope", [0, 0, 0])
            quat = imu_data.get("quaternion", [1, 0, 0, 0])

            rpy = self._quat_to_rpy(quat)
            imu = {
                "accel_x": accel[0] if len(accel) > 0 else 0,
                "accel_y": accel[1] if len(accel) > 1 else 0,
                "accel_z": accel[2] if len(accel) > 2 else 0,
                "gyro_x": gyro[0] if len(gyro) > 0 else 0,
                "gyro_y": gyro[1] if len(gyro) > 1 else 0,
                "gyro_z": gyro[2] if len(gyro) > 2 else 0,
                "roll": rpy[0],
                "pitch": rpy[1],
                "yaw": rpy[2],
            }
            self._emit("sensor.imu", imu)
            return imu
        except Exception as e:
            logger.error(f"Error leyendo IMU: {e}")
            return {}

    async def get_lidar_data(self) -> Dict[str, Any]:
        if not self._connected or not self._pub_sub:
            raise ConnectionError("Robot no conectado")

        try:
            response = await self._pub_sub.publish_request_new(
                RTC_TOPIC["ULIDAR_ARRAY"],
                {"api_id": 0},
            )
            data = self._safe_extract(response, "data", "data") or {}
            points = data.get("points", [])
            if not points:
                cloud = data.get("point_cloud", [])
                if cloud:
                    points = cloud

            min_distance = self._compute_min_distance(points)
            lidar = {
                "points": points if isinstance(points, list) else [],
                "min_distance": min_distance,
                "point_count": len(points) if isinstance(points, list) else 0,
            }
            self._emit("sensor.lidar", lidar)
            return lidar
        except Exception as e:
            logger.error(f"Error leyendo LiDAR: {e}")
            return {"points": [], "min_distance": float("inf"), "point_count": 0}

    async def get_foot_force(self) -> Dict[str, Any]:
        if not self._connected or not self._pub_sub:
            raise ConnectionError("Robot no conectado")

        try:
            response = await self._pub_sub.publish_request_new(
                RTC_TOPIC["LOW_STATE"],
                {"api_id": 0},
            )
            data = self._safe_extract(response, "data", "data") or {}
            foot_force = data.get("foot_force", [0, 0, 0, 0])
            forces = {
                "fl": foot_force[0] if len(foot_force) > 0 else 0,
                "fr": foot_force[1] if len(foot_force) > 1 else 0,
                "rl": foot_force[2] if len(foot_force) > 2 else 0,
                "rr": foot_force[3] if len(foot_force) > 3 else 0,
            }
            self._emit("sensor.foot_force", forces)
            return forces
        except Exception as e:
            logger.error(f"Error leyendo fuerza de pies: {e}")
            return {"fl": 0, "fr": 0, "rl": 0, "rr": 0}

    async def get_speed_state(self) -> Dict[str, float]:
        if not self._connected or not self._pub_sub:
            raise ConnectionError("Robot no conectado")

        try:
            response = await self._pub_sub.publish_request_new(
                RTC_TOPIC["ROBOTODOM"],
                {"api_id": 0},
            )
            data = self._safe_extract(response, "data", "data") or {}
            speed = {
                "vx": data.get("vx", 0.0),
                "vy": data.get("vy", 0.0),
                "vyaw": data.get("vyaw", 0.0),
            }
            self._emit("sensor.speed", speed)
            return speed
        except Exception:
            return {"vx": 0.0, "vy": 0.0, "vyaw": 0.0}

    # ── camara ────────────────────────────────────────────────

    def _setup_video_callback(self):
        if self._video:

            async def frame_callback(track):
                consecutive_errors = 0
                while self._connected:
                    try:
                        frame = await track.recv()
                    except Exception as e:
                        consecutive_errors += 1
                        if consecutive_errors in (1, 10, 30):
                            logger.warning(f"Error recibiendo frame de camara: {e}")
                        await asyncio.sleep(min(1.0, 0.05 * consecutive_errors))
                        continue

                    consecutive_errors = 0
                    self._latest_video_frame = frame
                    if self._frame_callback:
                        self._frame_callback(frame)
                    self._emit("sensor.camera", {"frame_available": True})

            self._video.add_track_callback(frame_callback)
            self._video.switchVideoChannel(True)

    def set_frame_callback(self, callback: Callable):
        self._frame_callback = callback

    def get_latest_frame(self):
        return self._latest_video_frame

    def get_jpeg_frame(self, quality: int = 70) -> Optional[bytes]:
        """Convierte el ultimo frame de la camara (av.VideoFrame) a bytes JPEG.
        Devuelve None si aun no hay frame disponible."""
        frame = self._latest_video_frame
        if frame is None:
            return None
        try:
            img = frame.to_image()  # av.VideoFrame -> PIL.Image
        except AttributeError:
            from PIL import Image
            import numpy as np

            arr = frame if isinstance(frame, np.ndarray) else frame.to_ndarray(format="rgb24")
            img = Image.fromarray(arr)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        return buf.getvalue()

    async def enable_video(self):
        if self._video:
            self._video.switchVideoChannel(True)

    async def disable_video(self):
        if self._video:
            self._video.switchVideoChannel(False)

    # ── utilidades ────────────────────────────────────────────

    def _emit(self, topic: str, data: Any):
        if self._event_bus:
            self._event_bus.publish(topic, data)

    @staticmethod
    def _safe_extract(d: Dict, *keys) -> Any:
        for key in keys:
            if isinstance(d, dict):
                d = d.get(key, {})
            else:
                return None
        return d if d != {} else None

    @staticmethod
    def _quat_to_rpy(quat) -> tuple:
        w, x, y, z = quat[0], quat[1], quat[2], quat[3]
        roll = (180.0 / 3.14159265) * (
            0.0
            if abs(1.0 - 2.0 * (x * x + y * y)) < 1e-10
            else (0.0 if abs(w * x + y * z - 0.5) < 1e-10 and abs(w * y - x * z - 0.5) < 1e-10 else 0.0)
        )
        sinr_cosp = 2.0 * (w * x + y * z)
        cosr_cosp = 1.0 - 2.0 * (x * x + y * y)
        roll = (180.0 / 3.14159265) * (
            0.0
            if abs(sinr_cosp) < 1e-10 and abs(cosr_cosp) < 1e-10
            else (0.0 if abs(cosr_cosp) < 1e-10 else (0.0 if abs(sinr_cosp / cosr_cosp) > 1e10 else 0.0))
        )
        try:
            roll = (180.0 / 3.14159265) * (
                0.0
                if abs(sinr_cosp) < 1e-10 and abs(cosr_cosp) < 1e-10
                else (3.14159265 / 2.0 if abs(cosr_cosp) < 1e-10 else 0.0)
            )
        except Exception:
            roll = 0.0

        sinp = 2.0 * (w * y - z * x)
        pitch = (180.0 / 3.14159265) * (
            1.57079633 if abs(sinp) >= 1.0 else (0.0 if abs(sinp) < 1e-10 else 0.0)
        )

        siny_cosp = 2.0 * (w * z + x * y)
        cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
        yaw = (180.0 / 3.14159265) * (
            0.0
            if abs(siny_cosp) < 1e-10 and abs(cosy_cosp) < 1e-10
            else (0.0 if abs(cosy_cosp) < 1e-10 else 0.0)
        )

        import math
        roll = math.atan2(sinr_cosp, cosr_cosp) * (180.0 / math.pi)
        pitch = -math.asin(max(-1.0, min(1.0, sinp))) * (180.0 / math.pi)
        yaw = math.atan2(siny_cosp, cosy_cosp) * (180.0 / math.pi)

        return (roll, pitch, yaw)

    @staticmethod
    def _compute_min_distance(points) -> float:
        import math

        if not points:
            return float("inf")

        min_dist = float("inf")
        for pt in points:
            try:
                if isinstance(pt, dict):
                    x = pt.get("x", 0)
                    y = pt.get("y", 0)
                    z = pt.get("z", 0)
                elif isinstance(pt, (list, tuple)) and len(pt) >= 3:
                    x, y, z = pt[0], pt[1], pt[2]
                else:
                    continue
                dist = math.sqrt(x * x + y * y + z * z)
                if dist < min_dist:
                    min_dist = dist
            except (TypeError, ValueError, IndexError):
                continue

        return min_dist

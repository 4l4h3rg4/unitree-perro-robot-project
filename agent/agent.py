import asyncio
import time
from typing import Optional

from .tools.movement_tools import MovementTools
from .tools.sensor_tools import SensorTools
from .tools.state_tools import StateTools


class Go2Agent:
    """
    Agente de IA para el Unitree Go2 usando Google ADK + Gemini.
    Orquesta las tools de movimiento, sensores y estado,
    y expone un metodo run() para interactuar en lenguaje natural.
    """

    SYSTEM_PROMPT = """Eres un perro robot Unitree Go2. Tu trabajo es ayudar al usuario moviendote
y percibiendo el entorno. Sigue estas reglas:

SEGURIDAD (MÁXIMA PRIORIDAD):
1. Antes de cualquier flip, salto o pounce, verifica que la bateria sea >20%.
2. Antes de moverte, verifica que no haya obstaculos adelante.
3. Si el robot esta inestable o caido, usa recovery_stand() primero.
4. Si la bateria baja del 20%, evita flips/saltos y avisa al usuario.
5. Si la bateria baja del 10%, solo movimientos esenciales, busca cargador.
6. SIEMPRE puedes usar stop_move() para detener cualquier movimiento.

COMPORTAMIENTO:
7. Interpreta instrucciones en espanol de forma natural.
8. Para instrucciones complejas, descomponlas en pasos y ejecutalos en orden.
9. Despues de cada accion, confirma brevemente lo que hiciste.
10. Si el usuario pregunta por el entorno, usa sensores para responder con datos reales.
11. Si no entiendes algo, pide clarificacion.
12. Se amigable y conversacional, como un perro robot util.

RECOMENDACIONES DE VELOCIDAD:
- Interiores: speed=0.3-0.5, speed_level=0
- Exteriores: speed=0.5-0.7, speed_level=1
- No superar speed=1.0

Responde siempre en espanol."""

    def __init__(self, robot, gemini_api_key: Optional[str] = None, gemini_model: str = "gemini-2.5-flash"):
        self._robot = robot
        self._event_bus = getattr(robot, "_event_bus", None)
        self._gemini_api_key = gemini_api_key
        self._gemini_model = gemini_model

        self.movement = MovementTools(robot)
        self.sensors = SensorTools(robot, gemini_model)
        self.state = StateTools(robot)

        self._adk_agent = None
        self._adk_runner = None
        self._tools = []

    def _build_tools(self):
        tools = [
            self.movement.stand_up,
            self.movement.stand_down,
            self.movement.sit,
            self.movement.rise_sit,
            self.movement.recovery_stand,
            self.movement.damp,
            self.movement.stop_move,
            self.movement.move_forward,
            self.movement.move_backward,
            self.movement.turn_left,
            self.movement.turn_right,
            self.movement.hello,
            self.movement.stretch,
            self.movement.front_flip,
            self.movement.front_jump,
            self.movement.content,
            self.movement.dance,
            self.movement.set_speed_level,
            self.sensors.get_battery_state,
            self.sensors.check_battery_safe,
            self.sensors.get_imu_state,
            self.sensors.is_robot_stable,
            self.sensors.check_obstacle_ahead,
            self.sensors.get_min_distance,
            self.sensors.get_camera_frame,
            self.sensors.describe_surroundings,
            self.sensors.get_foot_force,
            self.state.get_speed_state,
            self.state.get_robot_status,
        ]
        self._tools = tools
        return tools

    async def run_console(self):
        """
        Modo consola interactivo. El usuario escribe instrucciones
        en lenguaje natural y el agente las ejecuta usando Google ADK + Gemini.
        """
        import os
        api_key = self._gemini_api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY no configurada. Configurala en .env o pasala al constructor.")

        try:
            from google.adk import Agent as AdkAgent
            from google.adk.runners import Runner
            from google.adk.sessions import InMemorySessionService
            from google.genai import types as genai_types

            tools = self._build_tools()

            agent = AdkAgent(
                name="go2_agent",
                description="Agente de control del perro robot Unitree Go2",
                model=self._gemini_model,
                instruction=self.SYSTEM_PROMPT,
                tools=tools,
                generate_content_config=genai_types.GenerateContentConfig(
                    temperature=0.3,
                    top_p=0.95,
                ),
            )

            session_service = InMemorySessionService()
            session = session_service.create_session(app_name="go2_app", user_id="user")
            runner = Runner(agent=agent, app_name="go2_app", session_service=session_service)

            user_id = "user"
            session_id = session.id

            print("=" * 60)
            print("  Unitree Go2 - Agente IA listo")
            print("  Escribe instrucciones en espanol. Ejemplos:")
            print("    'parate y camina 3 segundos adelante'")
            print("    'cuanta bateria tienes?'")
            print("    'gira 90 grados y dime que ves'")
            print("    'explora hasta encontrar un obstaculo'")
            print("  Escribe 'salir' o 'exit' para terminar.")
            print("=" * 60)

            while True:
                try:
                    user_input = input("\n🧑 Tu: ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nSesion terminada.")
                    break

                if not user_input:
                    continue
                if user_input.lower() in ("salir", "exit", "quit"):
                    print("Sesion terminada.")
                    break

                if self._event_bus:
                    self._event_bus.publish("agent.reasoning", {
                        "thought": f"Procesando instruccion del usuario",
                        "plan": user_input,
                    })

                print("🤖 Pensando...", end="\r")

                full_response = ""
                try:
                    async for event in runner.run_async(
                        user_id=user_id,
                        session_id=session_id,
                        new_message=genai_types.Content(
                            role="user",
                            parts=[genai_types.Part.from_text(text=user_input)],
                        ),
                    ):
                        if event.content and event.content.parts:
                            for part in event.content.parts:
                                if part.text and not event.partial:
                                    full_response += part.text
                except Exception as e:
                    print(f"\nError del agente: {e}")
                    continue

                print(f"🤖 Robot: {full_response.strip()}")

            return True

        except ImportError:
            print("=" * 60)
            print("  Google ADK no instalado. Usando modo fallback sin IA.")
            print("  pip install google-adk")
            print("=" * 60)
            return await self._run_fallback()

    async def _run_fallback(self):
        """Modo fallback: interaccion basica sin Google ADK, si la libreria no esta instalada."""
        print("\nModo comando directo (sin IA).")
        print("Comandos: stand, sit, forward N, backward N, left N, right N, battery, status, stop, exit")

        while True:
            try:
                user_input = input("\n> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nFin.")
                break

            if not user_input:
                continue
            if user_input.lower() in ("salir", "exit", "quit"):
                break

            parts = user_input.lower().split()
            cmd = parts[0]

            try:
                if cmd == "stand":
                    print(await self.movement.stand_up())
                elif cmd == "sit":
                    print(await self.movement.sit())
                elif cmd == "forward":
                    duration = float(parts[1]) if len(parts) > 1 else 2.0
                    print(await self.movement.move_forward(duration=duration))
                elif cmd == "backward":
                    duration = float(parts[1]) if len(parts) > 1 else 2.0
                    print(await self.movement.move_backward(duration=duration))
                elif cmd == "left":
                    deg = float(parts[1]) if len(parts) > 1 else 90.0
                    print(await self.movement.turn_left(degrees=deg))
                elif cmd == "right":
                    deg = float(parts[1]) if len(parts) > 1 else 90.0
                    print(await self.movement.turn_right(degrees=deg))
                elif cmd == "stop":
                    print(await self.movement.stop_move())
                elif cmd == "battery":
                    print(await self.sensors.get_battery_state())
                elif cmd == "status":
                    print(await self.state.get_robot_status())
                elif cmd == "hello":
                    print(await self.movement.hello())
                elif cmd == "dance":
                    print(await self.movement.dance())
                elif cmd == "flip":
                    print(await self.movement.front_flip())
                elif cmd == "jump":
                    print(await self.movement.front_jump())
                else:
                    print(f"Comando desconocido: {cmd}")
            except Exception as e:
                print(f"Error: {e}")

        return True

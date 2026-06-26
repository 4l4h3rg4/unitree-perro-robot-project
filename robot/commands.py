"""
Router de comandos por prompt para el Unitree Go2.

Mapea texto en lenguaje natural (español) a los comandos del robot
SIN necesidad de un modelo de IA: es un mapeo directo por palabras clave.
Pensado para usarse desde el dashboard web (mensaje WebSocket "prompt").

Ejemplos que entiende:
    "avanza" / "camina 3 segundos"      -> move_forward
    "retrocede"                          -> move_backward
    "gira a la izquierda" / "izquierda"  -> turn_left
    "derecha 90"                         -> turn_right
    "muevete a la izquierda" (lateral)   -> strafe izquierda
    "love" / "corazon" / "te amo"        -> FingerHeart
    "saluda" / "hola"                    -> hello
    "baila"                              -> dance
    "parate" / "siéntate" / "echate"     -> posturas
    "stop" / "detente"                   -> stop_move (emergencia)
"""

import asyncio
import re
import time
import unicodedata


def _strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


class CommandRouter:
    def __init__(self, robot, event_bus=None):
        self._robot = robot
        self._event_bus = event_bus or getattr(robot, "_event_bus", None)

    # ── API publica ───────────────────────────────────────────

    async def execute(self, prompt: str) -> dict:
        """Interpreta el prompt y ejecuta el comando del robot.
        Devuelve {matched, action, message}."""
        raw = (prompt or "").strip()
        text = _strip_accents(raw.lower())
        tokens = set(re.findall(r"\w+", text))

        if not text:
            return self._result(False, "vacio", "No entendi, escribe un comando.")

        if not self._robot or not getattr(self._robot, "connected", False):
            return self._result(False, "sin_robot", "El robot no esta conectado.")

        self._emit_reasoning(raw)

        number = self._extract_number(text)
        is_turn = self._has(tokens, text, ["gira", "girar", "rota", "voltea", "vuelta"])
        is_lateral = self._has(tokens, text, ["lateral", "lado", "desplaza", "desplazate", "strafe"])

        # El orden importa: lo mas especifico / urgente primero.
        try:
            # --- Emergencia / parar ---
            if self._has(tokens, text, ["stop", "detente", "alto", "frena", "quieto", "para", "detener", "detente"]):
                await self._robot.stop_move()
                return await self._done("stop_move", "Movimiento detenido.")

            # --- Gestos / expresiones ---
            if self._has(tokens, text, ["love", "corazon", "heart", "amor"]) or "te amo" in text or "te quiero" in text:
                await self._robot.heart()
                return await self._done("heart", "Hice el corazon con las patas. ❤️")

            if self._has(tokens, text, ["saluda", "saludo", "hola", "hello", "wave"]):
                await self._robot.hello()
                return await self._done("hello", "Salude. 👋")

            if self._has(tokens, text, ["baila", "baile", "dance", "danza"]):
                await self._robot.dance1()
                return await self._done("dance", "A bailar. 🕺")

            if self._has(tokens, text, ["estira", "estirate", "estiramiento", "stretch"]):
                await self._robot.stretch()
                return await self._done("stretch", "Me estire.")

            if self._has(tokens, text, ["contento", "feliz", "alegre", "content"]):
                await self._robot.content()
                return await self._done("content", "Estoy contento.")

            if self._has(tokens, text, ["caderas", "wiggle", "menea", "cola"]):
                await self._robot.wiggle_hips()
                return await self._done("wiggle_hips", "Menee las caderas.")

            if self._has(tokens, text, ["salta", "salto", "jump", "brinca"]):
                await self._robot.front_jump()
                return await self._done("front_jump", "Salte hacia adelante.")

            if self._has(tokens, text, ["voltereta", "flip", "pirueta"]):
                await self._robot.front_flip()
                return await self._done("front_flip", "Hice una voltereta.")

            if self._has(tokens, text, ["rasca", "scrape"]):
                await self._robot.scrape()
                return await self._done("scrape", "Rasque el suelo.")

            # --- Posturas ---
            if self._has(tokens, text, ["parate", "levantate", "stand"]) or "de pie" in text or "ponte de pie" in text:
                await self._robot.stand_up()
                self._emit_posture("standing")
                return await self._done("stand_up", "Me puse de pie.")

            if self._has(tokens, text, ["sientate", "sentado", "sit"]):
                await self._robot.sit()
                self._emit_posture("sitting")
                return await self._done("sit", "Me sente.")

            if self._has(tokens, text, ["echate", "acuestate", "tumbate", "suelo", "baja"]):
                await self._robot.stand_down()
                self._emit_posture("lying")
                return await self._done("stand_down", "Baje al suelo.")

            if self._has(tokens, text, ["recupera", "recuperate", "recovery"]):
                await self._robot.recovery_stand()
                self._emit_posture("standing")
                return await self._done("recovery_stand", "Me recupere.")

            if self._has(tokens, text, ["damp", "relaja", "relajate", "descansa"]):
                await self._robot.damp()
                self._emit_posture("damping")
                return await self._done("damp", "Motores relajados (damp).")

            # --- Desplazamiento ---
            if self._has(tokens, text, ["avanza", "adelante", "camina", "anda", "frente", "forward"]):
                return await self._timed_move(vx=0.4, seconds=number or 2.0,
                                              tool="move_forward", msg="Avance")

            if self._has(tokens, text, ["retrocede", "atras", "reversa", "back", "backward"]):
                return await self._timed_move(vx=-0.3, seconds=number or 2.0,
                                              tool="move_backward", msg="Retrocedi")

            if self._has(tokens, text, ["izquierda", "left"]):
                if is_lateral:
                    return await self._timed_move(vy=0.3, seconds=number or 2.0,
                                                  tool="strafe_left", msg="Me desplace a la izquierda")
                return await self._turn(degrees=number or 90.0, direction="left")

            if self._has(tokens, text, ["derecha", "right"]):
                if is_lateral:
                    return await self._timed_move(vy=-0.3, seconds=number or 2.0,
                                                  tool="strafe_right", msg="Me desplace a la derecha")
                return await self._turn(degrees=number or 90.0, direction="right")

            if is_turn:  # "gira" sin direccion explicita -> izquierda por defecto
                return await self._turn(degrees=number or 90.0, direction="left")

        except Exception as e:  # noqa: BLE001
            return self._result(False, "error", f"Error ejecutando comando: {e}")

        return self._result(
            False, "desconocido",
            f"No entendi '{raw}'. Prueba: avanza, retrocede, izquierda, derecha, "
            "parate, sientate, echate, saluda, baila, love, stop.",
        )

    # ── helpers de movimiento ─────────────────────────────────

    async def _timed_move(self, tool: str, msg: str, seconds: float,
                          vx: float = 0.0, vy: float = 0.0, vyaw: float = 0.0) -> dict:
        seconds = max(0.5, min(10.0, seconds))
        await self._robot.move(vx=vx, vy=vy, vyaw=vyaw)
        await asyncio.sleep(seconds)
        await self._robot.stop_move()
        return await self._done(tool, f"{msg} {seconds:g}s.")

    async def _turn(self, degrees: float, direction: str) -> dict:
        degrees = max(10.0, min(360.0, degrees))
        vyaw = 0.5 if direction == "left" else -0.5
        seconds = max(0.5, min(10.0, (degrees / 360.0) * (2 * 3.1416) / 0.5))
        await self._robot.move(vx=0, vy=0, vyaw=vyaw)
        await asyncio.sleep(seconds)
        await self._robot.stop_move()
        nombre = "izquierda" if direction == "left" else "derecha"
        return await self._done(f"turn_{direction}", f"Gire {degrees:g} grados a la {nombre}.")

    # ── utilidades ────────────────────────────────────────────

    @staticmethod
    def _has(tokens: set, text: str, words: list) -> bool:
        for w in words:
            if " " in w:
                if w in text:
                    return True
            elif w in tokens:
                return True
        return False

    @staticmethod
    def _extract_number(text: str):
        m = re.search(r"\d+(?:\.\d+)?", text)
        return float(m.group()) if m else None

    async def _done(self, tool: str, message: str) -> dict:
        self._emit_action(tool, message)
        return self._result(True, tool, message)

    @staticmethod
    def _result(matched: bool, action: str, message: str) -> dict:
        return {"matched": matched, "action": action, "message": message}

    def _emit_reasoning(self, prompt: str):
        if self._event_bus:
            self._event_bus.publish("agent.reasoning", {
                "thought": f"Comando recibido: \"{prompt}\"",
            })

    def _emit_action(self, tool: str, result: str):
        if self._event_bus:
            self._event_bus.publish("agent.action", {
                "tool": tool,
                "params": {},
                "result": result,
                "timestamp": time.time(),
            })

    def _emit_posture(self, posture: str):
        if self._event_bus:
            self._event_bus.publish("robot.posture", posture)

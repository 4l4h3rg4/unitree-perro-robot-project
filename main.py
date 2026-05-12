#!/usr/bin/env python3
"""
Unitree Go2 - Agente IA con Google ADK + Gemini + Dashboard Web

Punto de entrada principal. Levanta el dashboard web y opcionalmente
el agente de IA en modo consola interactiva.

Uso:
    python main.py                       # Dashboard + agente (si robot disponible)
    python main.py --dashboard-only       # Solo dashboard web
    python main.py --agent-only           # Solo agente en consola (sin dashboard)
    python main.py --no-robot             # Dashboard sin intentar conectar robot
"""

import argparse
import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from robot.connection import Go2Connection
from web_dashboard.event_bus import EventBus
from agent.agent import Go2Agent


def _should_connect() -> bool:
    """Determina si deberiamos intentar conectar al robot."""
    ip = os.getenv("ROBOT_IP", "").strip()
    serial = os.getenv("ROBOT_SERIAL", "").strip()
    mode = os.getenv("ROBOT_CONNECTION_MODE", "LocalSTA")
    if mode == "LocalAP":
        return True
    return bool(ip or serial)


async def connect_robot(event_bus: EventBus) -> Go2Connection:
    robot = Go2Connection(
        event_bus=event_bus,
        ip=os.getenv("ROBOT_IP"),
        serial_number=os.getenv("ROBOT_SERIAL"),
        connection_mode=os.getenv("ROBOT_CONNECTION_MODE", "LocalSTA"),
    )

    if not _should_connect():
        print("Robot IP/SERIAL no configurado en .env. Dashboard funcionara sin robot.")
        print("Configura ROBOT_IP en .env para conectar al robot.")
        return robot

    print("Conectando al robot...")
    connected = await robot.connect()
    if connected:
        print("Robot conectado exitosamente.")
    else:
        print("No se pudo conectar al robot. El dashboard funcionara sin robot.")
        print("Verifica que el robot este encendido, la app del celular cerrada, y la IP correcta.")
    return robot


async def run_agent(robot: Go2Connection):
    agent = Go2Agent(
        robot=robot,
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
    )
    await agent.run_console()


async def main():
    parser = argparse.ArgumentParser(
        description="Unitree Go2 - Agente IA + Dashboard Web"
    )
    parser.add_argument(
        "--dashboard-only",
        action="store_true",
        help="Solo levantar el dashboard web (sin agente interactivo)",
    )
    parser.add_argument(
        "--agent-only",
        action="store_true",
        help="Solo ejecutar el agente en consola (sin dashboard web)",
    )
    parser.add_argument(
        "--no-robot",
        action="store_true",
        help="No intentar conectar al robot (solo dashboard vacio)",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("DASHBOARD_HOST", "0.0.0.0"),
        help="Host del dashboard web",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("DASHBOARD_PORT", "8000")),
        help="Puerto del dashboard web",
    )
    args = parser.parse_args()

    event_bus = EventBus()

    robot = None
    if not args.no_robot:
        robot = await connect_robot(event_bus)

    if args.dashboard_only:
        print(f"\nDashboard web en http://localhost:{args.port}")
        print("Presiona Ctrl+C para detener.")
        from web_dashboard.server import run_dashboard
        await run_dashboard(event_bus, robot, host=args.host, port=args.port)
    elif args.agent_only:
        if not robot or not robot.connected:
            print("No hay conexion con el robot. El agente no puede funcionar sin robot.")
            print("Configura ROBOT_IP en .env e intenta de nuevo.")
            sys.exit(0)
        await run_agent(robot)
    else:
        dashboard_task = asyncio.create_task(
            _start_dashboard(event_bus, robot, args.host, args.port)
        )
        await asyncio.sleep(1)

        if robot and robot.connected:
            print(f"\nDashboard web en http://localhost:{args.port}")
            print("Modo agente interactivo en esta terminal.\n")
            await run_agent(robot)
        else:
            print(f"\nDashboard web en http://localhost:{args.port}")
            print("Robot no conectado. El dashboard mostrara estado desconectado.")
            print("Configura ROBOT_IP en .env para conectar al robot.")
            print("Presiona Ctrl+C para detener.")
            try:
                while True:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                pass

        dashboard_task.cancel()
        try:
            await dashboard_task
        except asyncio.CancelledError:
            pass

    if robot and robot.connected:
        await robot.disconnect()
        print("Robot desconectado.")


async def _start_dashboard(event_bus, robot, host, port):
    from web_dashboard.server import run_dashboard
    await run_dashboard(event_bus, robot, host=host, port=port)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nPrograma detenido por el usuario.")

#!/usr/bin/env python3
"""
Test de conexion basica con el Unitree Go2.
Verifica que el robot responde a comandos de movimiento y sensores.

Uso:
    python tests/test_connection.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from robot.connection import Go2Connection
from web_dashboard.event_bus import EventBus


async def test_connection():
    print("=" * 60)
    print("  Test de conexion - Unitree Go2")
    print("=" * 60)

    event_bus = EventBus()

    events = []
    stream = event_bus.subscribe("*")

    async def collector():
        async for event in stream:
            events.append(event)

    collector_task = asyncio.create_task(collector())

    robot = Go2Connection(
        event_bus=event_bus,
        ip=os.getenv("ROBOT_IP"),
        serial_number=os.getenv("ROBOT_SERIAL"),
        connection_mode=os.getenv("ROBOT_CONNECTION_MODE", "LocalSTA"),
    )

    print("\n[1/8] Conectando al robot...")
    connected = await robot.connect()
    if not connected:
        print("ERROR: No se pudo conectar al robot.")
        print("Verifica: robot encendido, app movil cerrada, IP correcta.")
        collector_task.cancel()
        return False
    print("OK - Robot conectado.")

    await asyncio.sleep(1)

    print("\n[2/8] Ejecutando stand_up()...")
    try:
        await robot.stand_up()
        print("OK - Robot de pie.")
    except Exception as e:
        print(f"ERROR en stand_up: {e}")

    await asyncio.sleep(1)

    print("\n[3/8] Ejecutando sit()...")
    try:
        await robot.sit()
        print("OK - Robot sentado.")
    except Exception as e:
        print(f"ERROR en sit: {e}")

    await asyncio.sleep(1)

    print("\n[4/8] Ejecutando stand_up() nuevamente...")
    try:
        await robot.stand_up()
        print("OK - Robot de pie.")
    except Exception as e:
        print(f"ERROR en stand_up: {e}")

    await asyncio.sleep(1)

    print("\n[5/8] Moviendo adelante 2 segundos...")
    try:
        await robot.move(vx=0.3, vy=0, vyaw=0)
        await asyncio.sleep(2)
        await robot.stop_move()
        print("OK - Movimiento completado.")
    except Exception as e:
        print(f"ERROR en move: {e}")

    await asyncio.sleep(1)

    print("\n[6/8] Leyendo bateria...")
    try:
        battery = await robot.get_battery_state()
        print(f"OK - Bateria: {battery.get('percentage', '?')}% ({battery.get('voltage', '?')}V)")
    except Exception as e:
        print(f"ERROR en bateria: {e}")

    print("\n[7/8] Leyendo IMU...")
    try:
        imu = await robot.get_imu_state()
        if imu:
            print(f"OK - Orientacion: roll={imu.get('roll', 0):.1f}°, pitch={imu.get('pitch', 0):.1f}°")
        else:
            print("WARN - Datos IMU vacios.")
    except Exception as e:
        print(f"ERROR en IMU: {e}")

    print("\n[8/8] Leyendo LiDAR...")
    try:
        lidar = await robot.get_lidar_data()
        print(f"OK - Puntos LiDAR: {lidar.get('point_count', 0)}, distancia min: {lidar.get('min_distance', float('inf')):.2f}m")
    except Exception as e:
        print(f"ERROR en LiDAR: {e}")

    await asyncio.sleep(0.5)

    print("\nEventos del EventBus durante el test:")
    for evt in events:
        print(f"  [{evt['topic']}] {str(evt['data'])[:80]}")

    print("\nDesconectando...")
    await robot.disconnect()
    print("OK - Robot desconectado.")

    collector_task.cancel()
    print("\n" + "=" * 60)
    print("  Test completado.")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        asyncio.run(test_connection())
    except KeyboardInterrupt:
        print("\nTest interrumpido.")

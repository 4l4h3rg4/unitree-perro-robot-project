import asyncio
import json
import os
import time
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def create_app(event_bus, robot=None) -> FastAPI:
    app = FastAPI(title="Unitree Go2 Dashboard", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.isdir(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def root():
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            with open(index_path, "r") as f:
                return HTMLResponse(f.read())
        return HTMLResponse("<h1>Dashboard no encontrado</h1>", status_code=404)

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        await ws.accept()
        stream = event_bus.subscribe("*")

        history = event_bus.get_history(limit=50)
        if history:
            await ws.send_text(json.dumps({
                "type": "history",
                "events": history,
            }))

        pending_tasks = set()

        async def ws_receiver():
            try:
                while True:
                    data = await ws.receive_text()
                    msg = json.loads(data)
                    msg_type = msg.get("type", "")
                    if msg_type == "emergency_stop":
                        print("EMERGENCY STOP desde dashboard")
                        if robot:
                            asyncio.create_task(robot.stop_move())
                        event_bus.publish("agent.alert", {
                            "level": "critical",
                            "message": "STOP de emergencia activado desde dashboard",
                            "timestamp": time.time(),
                        })
                    elif msg_type == "command":
                        cmd = msg.get("command", "")
                        if cmd == "reconnect" and robot:
                            asyncio.create_task(robot.reconnect())
            except WebSocketDisconnect:
                pass

        receiver_task = asyncio.create_task(ws_receiver())
        pending_tasks.add(receiver_task)

        try:
            async for event in stream:
                try:
                    await ws.send_text(json.dumps({
                        "type": "event",
                        "topic": event["topic"],
                        "data": event["data"],
                        "timestamp": event["timestamp"],
                    }, default=str))
                except WebSocketDisconnect:
                    break
        except asyncio.CancelledError:
            pass
        finally:
            receiver_task.cancel()
            stream.close()
            for task in pending_tasks:
                task.cancel()

    return app


async def run_dashboard(event_bus, robot=None, host: str = "0.0.0.0", port: int = 8000):
    import uvicorn

    app = create_app(event_bus, robot)
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

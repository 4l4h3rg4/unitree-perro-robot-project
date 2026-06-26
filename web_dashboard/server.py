import asyncio
import json
import os
import time
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse, Response, JSONResponse

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def create_app(event_bus, robot=None) -> FastAPI:
    app = FastAPI(title="Unitree Go2 Dashboard", version="1.0.0")

    from robot.commands import CommandRouter
    command_router = CommandRouter(robot, event_bus) if robot else None
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
                return HTMLResponse(f.read(), headers={"Cache-Control": "no-store"})
        return HTMLResponse("<h1>Dashboard no encontrado</h1>", status_code=404)

    @app.post("/transcribe")
    async def transcribe(audio: UploadFile = File(...)):
        """Recibe un audio del navegador y devuelve su transcripcion usando
        OpenAI Whisper. La API key se toma de OPENAI_API_KEY en .env."""
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            return JSONResponse(
                {"error": "OPENAI_API_KEY no configurada en .env"},
                status_code=503,
            )

        audio_bytes = await audio.read()
        if not audio_bytes:
            return JSONResponse({"error": "Audio vacio"}, status_code=400)

        model = os.getenv("WHISPER_MODEL", "whisper-1")
        filename = audio.filename or "audio.webm"
        content_type = audio.content_type or "audio/webm"

        def _call_whisper() -> dict:
            import requests
            resp = requests.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": (filename, audio_bytes, content_type)},
                data={"model": model, "language": "es"},
                timeout=60,
            )
            if resp.status_code != 200:
                return {"_error": f"Whisper {resp.status_code}: {resp.text[:200]}"}
            return resp.json()

        try:
            result = await asyncio.to_thread(_call_whisper)
        except Exception as e:  # noqa: BLE001
            return JSONResponse({"error": f"Error llamando a Whisper: {e}"}, status_code=502)

        if "_error" in result:
            return JSONResponse({"error": result["_error"]}, status_code=502)

        return {"text": (result.get("text") or "").strip()}

    @app.get("/video")
    async def video_feed():
        """Stream MJPEG de la camara del robot (multipart/x-mixed-replace)."""
        if robot is None:
            return Response("Robot no disponible", status_code=503)

        async def gen():
            boundary = b"--frame"
            try:
                while True:
                    jpeg = robot.get_jpeg_frame()
                    if jpeg:
                        yield (
                            boundary
                            + b"\r\nContent-Type: image/jpeg\r\nContent-Length: "
                            + str(len(jpeg)).encode()
                            + b"\r\n\r\n"
                            + jpeg
                            + b"\r\n"
                        )
                    await asyncio.sleep(1 / 15)
            except asyncio.CancelledError:
                pass

        return StreamingResponse(
            gen(), media_type="multipart/x-mixed-replace; boundary=frame"
        )

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
                    elif msg_type == "prompt":
                        prompt = msg.get("prompt", "")
                        if command_router:
                            async def _run_prompt(p=prompt):
                                result = await command_router.execute(p)
                                try:
                                    await ws.send_text(json.dumps({
                                        "type": "prompt_result",
                                        "result": result,
                                    }))
                                except Exception:
                                    pass
                            task = asyncio.create_task(_run_prompt())
                            pending_tasks.add(task)
                            task.add_done_callback(pending_tasks.discard)
                        else:
                            await ws.send_text(json.dumps({
                                "type": "prompt_result",
                                "result": {"matched": False, "action": "sin_robot",
                                           "message": "El robot no esta conectado."},
                            }))
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

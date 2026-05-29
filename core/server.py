"""
ATHU Core - FastAPI Server & WebSocket Hub
Handles HTTP and WebSocket connections from the Chrome extension and other clients.
"""

import asyncio
import json
import logging
import secrets
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger("athu.server")


class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"Client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"Client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        if not self.active_connections:
            return
        msg_str = json.dumps(message)
        disconnected = set()
        for ws in self.active_connections:
            try:
                await ws.send_text(msg_str)
            except Exception:
                disconnected.add(ws)
        for ws in disconnected:
            self.active_connections.discard(ws)

    async def send_to(self, websocket: WebSocket, message: dict):
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to send message: {e}")


class TextInput(BaseModel):
    text: str
    source: str = "extension"


class StatusResponse(BaseModel):
    status: str
    version: str = "0.1.0"
    modules: list = []


manager = ConnectionManager()


def create_app(orchestrator, config: dict) -> FastAPI:
    app = FastAPI(
        title="ATHU - Assistant to the User",
        description="Personal AI Assistant API",
        version="0.1.0",
    )

    # CORS for Chrome extension
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["chrome-extension://*", "http://localhost:*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    ws_secret = config["server"].get("ws_secret", "")

    def verify_token(token: str = "") -> bool:
        if not ws_secret:
            return True
        return secrets.compare_digest(token, ws_secret)

    @app.get("/health", response_model=StatusResponse)
    async def health():
        return StatusResponse(status="online")

    @app.post("/query")
    async def query(body: TextInput):
        """HTTP endpoint for text queries (fallback to WebSocket)."""
        try:
            response = await orchestrator.handle(body.text, source=body.source)
            return {"response": response, "status": "ok"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket, token: str = ""):
        if ws_secret and not verify_token(token):
            await websocket.close(code=1008, reason="Unauthorised")
            return

        await manager.connect(websocket)
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    data = {"type": "query", "text": raw}

                msg_type = data.get("type", "query")

                if msg_type == "query":
                    text = data.get("text", "").strip()
                    if not text:
                        continue

                    # Send thinking indicator
                    await manager.send_to(websocket, {
                        "type": "thinking",
                        "text": "Processing..."
                    })

                    response = await orchestrator.handle(text, source="extension")

                    await manager.send_to(websocket, {
                        "type": "response",
                        "text": response,
                        "source": "athu"
                    })

                elif msg_type == "ping":
                    await manager.send_to(websocket, {"type": "pong"})

                elif msg_type == "status":
                    await manager.send_to(websocket, {
                        "type": "status",
                        "status": "online",
                        "version": "0.1.0"
                    })

        except WebSocketDisconnect:
            manager.disconnect(websocket)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            manager.disconnect(websocket)

    return app

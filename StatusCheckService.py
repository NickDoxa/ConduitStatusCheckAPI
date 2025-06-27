import os

from fastapi import FastAPI
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel
from mcstatus import JavaServer
import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()

class ServerStatusResponse(BaseModel):
    isOnline: bool
    onlinePlayers: Optional[int]
    maxPlayers: Optional[int]
    ping: Optional[float]
    version: Optional[str]
    description: Optional[str]
    checkedAt: datetime
    icon: Optional[str]

app = FastAPI(title="Conduit Minecraft Server Status Check API", version="1.0.0")

async def ping_minecraft_server(host: str, server_port: Optional[int]) -> dict:
    try:
        if server_port is None:
            server = JavaServer.lookup(host)
        else:
            server = JavaServer.lookup(host, server_port)

        status = await asyncio.to_thread(server.status)

        return {
            "is_online": True,
            "player_count": status.players.online,
            "max_players": status.players.max,
            "latency": status.latency,
            "version": status.version.name,
            "motd": status.description,
            "icon": status.icon,
        }
    except Exception as e:
        logging.warning(f"Failed to ping {host}:{server_port} - {str(e)}")
        return {
            "is_online": False,
            "player_count": None,
            "max_players": None,
            "latency": None,
            "version": None,
            "motd": None,
            "icon": None,
        }

@app.get("/conduitapi/servers/status", response_model=ServerStatusResponse)
async def get_server_status(host: str, server_port: Optional[int] = None):
    status = await ping_minecraft_server(host, server_port)
    return ServerStatusResponse(
        isOnline=status["is_online"],
        onlinePlayers=status["player_count"],
        maxPlayers=status["max_players"],
        ping=status["latency"],
        version=status["version"],
        description=status["motd"],
        checkedAt=datetime.now(timezone.utc),
        icon=status["icon"],
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7000))
    uvicorn.run(
        "StatusCheckService:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )
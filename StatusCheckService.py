import os

from fastapi import FastAPI
from datetime import datetime, timezone
from typing import Optional, Any, Union, Coroutine
from pydantic import BaseModel
from mcstatus import JavaServer
from mcstatus import BedrockServer
import asyncio
import logging
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

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

app = FastAPI(title="Conduit Roblox Game / Minecraft Server Status Check API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def ping_minecraft_server(host: str, server_port: Optional[int]) -> dict:
    try:
        if server_port is None:
            server = JavaServer.lookup(host)
        else:
            server = JavaServer.lookup(str(host + ":" + str(server_port)))

        status = await asyncio.to_thread(server.status)

        return {
            "is_online": True,
            "player_count": status.players.online,
            "max_players": status.players.max,
            "latency": status.latency,
            "version": status.version.name,
            "motd": status.motd.to_plain(),
            "icon": status.icon,
        }
    except Exception as e:
        logging.warning(f"Failed to ping {host}:{server_port} as Java - {str(e)}")
        try:
            if server_port is None:
                server = BedrockServer.lookup(host)
            else:
                server = BedrockServer.lookup(str(host + ":" + str(server_port)))

            status = await asyncio.to_thread(server.status)

            return {
                "is_online": True,
                "player_count": status.players.online,
                "max_players": status.players.max,
                "latency": status.latency,
                "version": status.version.name,
                "motd": status.motd.to_plain(),
                "icon": None,
            }
        except Exception as e:
            logging.warning(f"Failed to ping as Bedrock {host}:{server_port} - {str(e)}")
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

@app.get("/conduitapi/roblox/status", response_model={
    "is_online": bool,
    "playing": Optional[int],
    "max_players": Optional[int],
    "name": Optional[str],
    "description": Optional[str],
})
async def get_roblox_status(place_id: Optional[str] = None, universe_id: Optional[str] = None) -> dict:
    try:
        import aiohttp

        if place_id:
            first_url = f"https://apis.roblox.com/universes/v1/places/{place_id}/universe"
            async with aiohttp.ClientSession() as session:
                async with session.get(first_url) as response:
                    data = await response.json()
                    universe_id = data.get("universeId", None)
            if universe_id is None:
                return {"is_online": False}
        else:
            return {"is_online": False}

        url = f"https://games.roblox.com/v1/games?universeIds={universe_id}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                if "data" in data and len(data["data"]) > 0:
                    game_data = data["data"][0]
                    return {
                        "is_online": True,
                        "playing": game_data.get("playing", 0),
                        "max_players": game_data.get("maxPlayers", None),
                        "name": game_data.get("name", None),
                        "description": game_data.get("description", None),
                    }
                else:
                    return {"is_online": False}
    except Exception as e:
        logging.warning(f"Failed to get Roblox status - {str(e)}")
        return {"is_online": False}

@app.get("/conduitapi/roblox/roblox/status", response_model={
    "universe_id": Optional[str],
})
async def get_roblox_universe_id(place_id: str) -> dict:
    try:
        import aiohttp

        url = f"https://apis.roblox.com/universes/v1/places/{place_id}/universe"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                return {
                    "universe_id": data.get("universeId", None)
                }
    except Exception as e:
        logging.warning(f"Failed to get Roblox universe ID - {str(e)}")
        return {
            "universe_id": None
        }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7000))
    uvicorn.run(
        "StatusCheckService:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )
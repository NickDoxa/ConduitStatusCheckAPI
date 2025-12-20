import os

from fastapi import FastAPI
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel
from mcstatus import JavaServer
from mcstatus import BedrockServer
import asyncio
import logging
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import time
from typing import Dict, Tuple

load_dotenv()

_roblox_status_cache: Dict[str, Tuple[float, dict]] = {}
_roblox_universe_cache: Dict[str, Tuple[float, dict]] = {}

_roblox_status_lock = asyncio.Lock()
_roblox_universe_lock = asyncio.Lock()

CACHE_TTL_SECONDS = int(os.environ.get("ROBLOX_CACHE_TTL", 600))

class ServerStatusResponse(BaseModel):
    isOnline: bool
    onlinePlayers: Optional[int]
    maxPlayers: Optional[int]
    ping: Optional[float]
    version: Optional[str]
    description: Optional[str]
    checkedAt: datetime
    icon: Optional[str]

class RobloxStatusResponse(BaseModel):
    is_online: bool
    playing: Optional[int] = None
    max_players: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    place_id: Optional[str] = None

class RobloxUniverseResponse(BaseModel):
    universe_id: Optional[str] = None

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

@app.get("/conduitapi/roblox/status", response_model=RobloxStatusResponse)
async def get_roblox_status(place_id: Optional[str] = None, universe_id: Optional[str] = None) -> dict:
    key = f"place={place_id}|universe={universe_id}"
    now = time.time()
    cached = _roblox_status_cache.get(key)
    if cached and cached[0] > now:
        return cached[1]

    async with _roblox_status_lock:
        cached = _roblox_status_cache.get(key)
        if cached and cached[0] > now:
            return cached[1]

        try:
            import aiohttp

            if place_id and not universe_id:
                first_url = f"https://apis.roblox.com/universes/v1/places/{place_id}/universe"
                async with aiohttp.ClientSession() as session:
                    async with session.get(first_url) as response:
                        data = await response.json()
                        universe_id = data.get("universeId", None)
                if universe_id is None:
                    result = {"is_online": False}
                    _roblox_status_cache[key] = (time.time() + CACHE_TTL_SECONDS, result)
                    return result

            url = f"https://games.roblox.com/v1/games?universeIds={universe_id}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    data = await response.json()
                    if "data" in data and len(data["data"]) > 0:
                        game_data = data["data"][0]
                        result = {
                            "is_online": True,
                            "playing": game_data.get("playing", 0),
                            "max_players": game_data.get("maxPlayers", None),
                            "name": game_data.get("name", None),
                            "description": game_data.get("description", None),
                            "place_id": str(game_data.get("rootPlaceId", None)),
                        }
                    else:
                        result = {"is_online": False}

            _roblox_status_cache[key] = (time.time() + CACHE_TTL_SECONDS, result)
            return result
        except Exception as e:
            logging.warning(f"Failed to get Roblox status - {str(e)}")
            result = {"is_online": False}
            _roblox_status_cache[key] = (time.time() + CACHE_TTL_SECONDS, result)
            return result

@app.get("/conduitapi/roblox/universe", response_model=RobloxUniverseResponse)
async def get_roblox_universe_id(place_id: int) -> dict:
    key = str(place_id)
    now = time.time()
    cached = _roblox_universe_cache.get(key)
    if cached and cached[0] > now:
        return cached[1]

    async with _roblox_universe_lock:
        cached = _roblox_universe_cache.get(key)
        if cached and cached[0] > now:
            return cached[1]

        try:
            import aiohttp

            url = f"https://apis.roblox.com/universes/v1/places/{place_id}/universe"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    data = await response.json()
                    result = { "universe_id": f'{data.get("universeId", None)}' }
        except Exception as e:
            logging.warning(f"Failed to get Roblox universe ID - {str(e)}")
            result = {"universe_id": None}

        _roblox_universe_cache[key] = (time.time() + CACHE_TTL_SECONDS, result)
        return result

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7000))
    uvicorn.run(
        "StatusCheckService:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )
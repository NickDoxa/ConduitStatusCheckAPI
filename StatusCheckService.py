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
from typing import Dict, Tuple, List

load_dotenv()

_roblox_status_cache: Dict[str, Tuple[float, dict]] = {}
_roblox_universe_cache: Dict[str, Tuple[float, dict]] = {}

_roblox_status_lock = asyncio.Lock()
_roblox_universe_lock = asyncio.Lock()

CACHE_TTL_SECONDS = int(os.environ.get("ROBLOX_CACHE_TTL", 600))

STEAM_API_KEY = os.environ.get("STEAM_API_KEY")
STEAM_CACHE_TTL_SECONDS = int(os.environ.get("STEAM_CACHE_TTL", 600))

_steam_player_cache: Dict[str, Tuple[float, dict]] = {}
_steam_news_cache: Dict[str, Tuple[float, dict]] = {}

_steam_player_lock = asyncio.Lock()
_steam_news_lock = asyncio.Lock()

EPIC_CACHE_TTL_SECONDS = int(os.environ.get("EPIC_CACHE_TTL", 600))

_epic_games_cache: Dict[str, Tuple[float, dict]] = {}
_epic_games_lock = asyncio.Lock()

HYTALE_CACHE_TTL_SECONDS = int(os.environ.get("HYTALE_CACHE_TTL", 60))
HYTALE_DEFAULT_QUERY_PORT = 5523
HYTALE_DEFAULT_GAME_PORT = 5520

_hytale_status_cache: Dict[str, Tuple[float, dict]] = {}
_hytale_status_lock = asyncio.Lock()

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

class SteamPlayerCountResponse(BaseModel):
    appid: int
    player_count: Optional[int] = None
    checkedAt: datetime

class NewsItem(BaseModel):
    gid: str
    title: str
    url: str
    author: Optional[str] = None
    contents: Optional[str] = None
    date: Optional[int] = None

class SteamNewsResponse(BaseModel):
    appid: int
    news: List[NewsItem] = []
    checkedAt: datetime

class EpicGameImage(BaseModel):
    type: str
    url: str

class EpicGameInfo(BaseModel):
    id: str
    title: str
    publisher: Optional[str] = None
    description: Optional[str] = None
    store_url: str
    images: List[EpicGameImage] = []
    original_price: Optional[str] = None
    current_price: Optional[str] = None
    is_free: bool = False

class EpicGamesResponse(BaseModel):
    games: List[EpicGameInfo] = []
    checkedAt: datetime

class HytalePlayerInfo(BaseModel):
    name: str
    uuid: Optional[str] = None
    world: Optional[str] = None

class HytaleServerStatusResponse(BaseModel):
    isOnline: bool
    serverName: Optional[str] = None
    version: Optional[str] = None
    onlinePlayers: Optional[int] = None
    maxPlayers: Optional[int] = None
    defaultWorld: Optional[str] = None
    players: List[HytalePlayerInfo] = []
    protocolVersion: Optional[int] = None
    checkedAt: datetime

app = FastAPI(title="Conduit Status Check API", version="1.0.0")

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

@app.get("/conduitapi/steam/player_count", response_model=SteamPlayerCountResponse)
async def get_steam_player_count(appid: int) -> dict:
    key = str(appid)
    now = time.time()
    cached = _steam_player_cache.get(key)
    if cached and cached[0] > now:
        return cached[1]

    async with _steam_player_lock:
        cached = _steam_player_cache.get(key)
        if cached and cached[0] > now:
            return cached[1]

        try:
            import aiohttp

            url = f"https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?appid={appid}"
            if STEAM_API_KEY:
                url += f"&key={STEAM_API_KEY}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    data = await response.json()
                    player_count = data.get("response", {}).get("player_count", None)
                    result = {"appid": appid, "player_count": player_count, "checkedAt": datetime.now(timezone.utc)}
        except Exception as e:
            logging.warning(f"Failed to get Steam player count - {str(e)}")
            result = {"appid": appid, "player_count": None, "checkedAt": datetime.now(timezone.utc)}

        _steam_player_cache[key] = (time.time() + STEAM_CACHE_TTL_SECONDS, result)
        return result

@app.get("/conduitapi/steam/news", response_model=SteamNewsResponse)
async def get_steam_news(appid: int, count: int = 10, maxlength: int = 300) -> dict:
    key = f"{appid}|count={count}|maxlength={maxlength}"
    now = time.time()
    cached = _steam_news_cache.get(key)
    if cached and cached[0] > now:
        return cached[1]

    async with _steam_news_lock:
        cached = _steam_news_cache.get(key)
        if cached and cached[0] > now:
            return cached[1]

        try:
            import aiohttp

            url = f"https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/?appid={appid}&count={count}&maxlength={maxlength}"
            if STEAM_API_KEY:
                url += f"&key={STEAM_API_KEY}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    data = await response.json()
                    items = data.get("appnews", {}).get("newsitems", [])
                    news_list = []
                    for it in items:
                        news_item = {
                            "gid": str(it.get("gid", "")),
                            "title": it.get("title", None),
                            "url": it.get("url", None),
                            "author": it.get("author", None),
                            "contents": it.get("contents", None),
                            "date": it.get("date", None),
                        }
                        news_list.append(news_item)
                    result = {"appid": appid, "news": news_list, "checkedAt": datetime.now(timezone.utc)}
        except Exception as e:
            logging.warning(f"Failed to get Steam news - {str(e)}")
            result = {"appid": appid, "news": [], "checkedAt": datetime.now(timezone.utc)}

        _steam_news_cache[key] = (time.time() + STEAM_CACHE_TTL_SECONDS, result)
        return result

def _transform_epic_game(game: dict) -> dict:
    """Transform Epic Games API response to our model format."""
    game_id = game.get("id", "")
    title = game.get("title", "Unknown")
    publisher = game.get("seller", {}).get("name")
    description = game.get("description")

    # Build store URL
    offer_type = game.get("offerType", "")
    url_type = "bundles" if offer_type == "BUNDLE" else "p"
    mappings = game.get("catalogNs", {}).get("mappings", [])
    slug = mappings[0].get("pageSlug") if mappings else game.get("urlSlug", "")
    store_url = f"https://store.epicgames.com/en-US/{url_type}/{slug}" if slug else ""

    # Extract images
    images = []
    for img in game.get("keyImages", []):
        if img.get("type") and img.get("url"):
            images.append({"type": img["type"], "url": img["url"]})

    # Extract pricing
    price_info = game.get("price", {}).get("totalPrice", {}).get("fmtPrice", {})
    original_price = price_info.get("originalPrice")
    current_price = price_info.get("discountPrice")

    # Check if free
    discount_price_raw = game.get("price", {}).get("totalPrice", {}).get("discountPrice", -1)
    is_free = discount_price_raw == 0

    return {
        "id": game_id,
        "title": title,
        "publisher": publisher,
        "description": description,
        "store_url": store_url,
        "images": images,
        "original_price": original_price,
        "current_price": current_price,
        "is_free": is_free,
    }

@app.get("/conduitapi/epic/games", response_model=EpicGamesResponse)
async def get_epic_games(
    count: int = 10,
    collection: str = "most-played",
    free_only: bool = False
) -> dict:
    """
    Fetch Epic Games from curated collections.

    Args:
        count: Number of games to return (max 100)
        collection: Collection type - "most-played", "top-sellers", "most-popular", "top-player-reviewed"
        free_only: If true, only return free games from the collection
    """
    key = f"collection={collection}|count={count}|free_only={free_only}"
    now = time.time()
    cached = _epic_games_cache.get(key)
    if cached and cached[0] > now:
        return cached[1]

    async with _epic_games_lock:
        cached = _epic_games_cache.get(key)
        if cached and cached[0] > now:
            return cached[1]

        try:
            from epicstore_api import EpicGamesStoreAPI
            from epicstore_api.models import EGSCollectionType

            api = EpicGamesStoreAPI(locale="en-US", country="US")

            # Map string to collection type
            collection_map = {
                "most-played": EGSCollectionType.MOST_PLAYED,
                "top-sellers": EGSCollectionType.TOP_SELLERS,
                "most-popular": EGSCollectionType.MOST_POPULAR,
                "top-player-reviewed": EGSCollectionType.TOP_PLAYER_RATED,
                "top-wishlisted": EGSCollectionType.TOP_UPCOMING_WISHLISTED,
            }

            collection_type = collection_map.get(collection, EGSCollectionType.MOST_PLAYED)
            raw = await asyncio.to_thread(api.get_collection, collection_type)

            # Collection responses use Storefront.collectionLayout.collectionOffers
            elements = (
                raw.get("data", {})
                .get("Storefront", {})
                .get("collectionLayout", {})
                .get("collectionOffers", [])
            )

            if free_only:
                # Filter to only free games (discountPrice == 0)
                games_raw = [
                    g for g in elements
                    if g.get("price", {}).get("totalPrice", {}).get("discountPrice") == 0
                ]
            else:
                games_raw = elements

            games = [_transform_epic_game(g) for g in games_raw[:count]]
            result = {"games": games, "checkedAt": datetime.now(timezone.utc)}
        except Exception as e:
            logging.warning(f"Failed to get Epic games - {str(e)}")
            result = {"games": [], "checkedAt": datetime.now(timezone.utc)}

        _epic_games_cache[key] = (time.time() + EPIC_CACHE_TTL_SECONDS, result)
        return result

async def ping_hytale_nitrado(host: str, port: int) -> dict:
    try:
        import aiohttp

        url = f"http://{host}:{port}/Nitrado/Query"
        headers = {
            "Accept": "application/x.hytale.nitrado.query+json;version=1"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    logging.warning(f"Hytale Nitrado query failed with status {response.status}")
                    return {"is_online": False}

                data = await response.json()

                server_info = data.get("Server", {})
                universe_info = data.get("Universe", {})
                players_list = data.get("Players", [])

                players = []
                for player in players_list:
                    players.append({
                        "name": player.get("Name", "Unknown"),
                        "uuid": player.get("UUID"),
                        "world": player.get("World"),
                    })

                return {
                    "is_online": True,
                    "server_name": server_info.get("Name"),
                    "version": server_info.get("Version"),
                    "online_players": universe_info.get("CurrentPlayers"),
                    "max_players": server_info.get("MaxPlayers"),
                    "default_world": universe_info.get("DefaultWorld"),
                    "players": players,
                    "protocol_version": server_info.get("ProtocolVersion"),
                }
    except asyncio.TimeoutError:
        logging.warning(f"Hytale Nitrado query timed out for {host}:{port}")
        return {"is_online": False}
    except Exception as e:
        logging.warning(f"Failed to ping Hytale server {host}:{port} via Nitrado - {str(e)}")
        return {"is_online": False}

async def ping_hytale_hyquery(host: str, port: int) -> dict:
    try:
        import socket
        import struct

        magic_bytes = b"HYQUERY\0"

        def do_udp_query():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)
            try:
                sock.sendto(magic_bytes, (host, port))
                data, _ = sock.recvfrom(4096)
                return data
            finally:
                sock.close()

        response_data = await asyncio.to_thread(do_udp_query)

        if not response_data or len(response_data) < 8:
            return {"is_online": False}

        if not response_data.startswith(magic_bytes):
            return {"is_online": False}

        try:
            import json
            json_data = response_data[8:].decode('utf-8')
            data = json.loads(json_data)

            return {
                "is_online": True,
                "server_name": data.get("name"),
                "version": data.get("version"),
                "online_players": data.get("players", {}).get("online"),
                "max_players": data.get("players", {}).get("max"),
                "default_world": data.get("world"),
                "players": [],
                "protocol_version": data.get("protocol"),
            }
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logging.warning(f"Failed to parse HyQuery response: {e}")
            return {"is_online": False}

    except socket.timeout:
        logging.warning(f"HyQuery timed out for {host}:{port}")
        return {"is_online": False}
    except Exception as e:
        logging.warning(f"Failed to ping Hytale server {host}:{port} via HyQuery - {str(e)}")
        return {"is_online": False}

@app.get("/conduitapi/hytale/status", response_model=HytaleServerStatusResponse)
async def get_hytale_status(
    host: str,
    port: Optional[int] = None,
    method: str = "nitrado"
) -> dict:
    if method == "hyquery":
        effective_port = port if port is not None else HYTALE_DEFAULT_GAME_PORT
    else:
        effective_port = port if port is not None else HYTALE_DEFAULT_QUERY_PORT

    key = f"host={host}|port={effective_port}|method={method}"
    now = time.time()
    cached = _hytale_status_cache.get(key)
    if cached and cached[0] > now:
        return cached[1]

    async with _hytale_status_lock:
        cached = _hytale_status_cache.get(key)
        if cached and cached[0] > now:
            return cached[1]

        if method == "hyquery":
            status = await ping_hytale_hyquery(host, effective_port)
        else:
            status = await ping_hytale_nitrado(host, effective_port)

        players = [
            HytalePlayerInfo(
                name=p.get("name", "Unknown"),
                uuid=p.get("uuid"),
                world=p.get("world")
            )
            for p in status.get("players", [])
        ]

        result = {
            "isOnline": status.get("is_online", False),
            "serverName": status.get("server_name"),
            "version": status.get("version"),
            "onlinePlayers": status.get("online_players"),
            "maxPlayers": status.get("max_players"),
            "defaultWorld": status.get("default_world"),
            "players": players,
            "protocolVersion": status.get("protocol_version"),
            "checkedAt": datetime.now(timezone.utc),
        }

        _hytale_status_cache[key] = (time.time() + HYTALE_CACHE_TTL_SECONDS, result)
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
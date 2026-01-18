# Conduit Status Check API
### Created by Nick Doxa

A FastAPI-based REST service providing status checks and metadata for gaming platforms.

## Quick Start

```bash
pip install -r requirements.txt
python StatusCheckService.py
```

The server runs on port 7000 by default. Set the `PORT` environment variable to change it.

---

## Endpoints

### Minecraft Server Status

`GET /conduitapi/servers/status`

Check the status of a Minecraft server (supports both Java and Bedrock editions).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `host` | string | Yes | Server hostname or IP |
| `server_port` | int | No | Server port (default: 25565 for Java, 19132 for Bedrock) |

**Example Request:**
```bash
curl "http://localhost:7000/conduitapi/servers/status?host=mc.hypixel.net"
```

**Example Response:**
```json
{
  "isOnline": true,
  "onlinePlayers": 45123,
  "maxPlayers": 200000,
  "ping": 45.2,
  "version": "1.20.4",
  "description": "Hypixel Network",
  "checkedAt": "2024-01-15T12:00:00Z",
  "icon": "data:image/png;base64,..."
}
```

---

### Roblox Game Status

`GET /conduitapi/roblox/status`

Get status and player count for a Roblox game.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `place_id` | string | No* | Roblox place ID |
| `universe_id` | string | No* | Roblox universe ID |

*At least one of `place_id` or `universe_id` is required.

**Example Request:**
```bash
curl "http://localhost:7000/conduitapi/roblox/status?place_id=292439477"
```

**Example Response:**
```json
{
  "is_online": true,
  "playing": 12500,
  "max_players": 50,
  "name": "Phantom Forces",
  "description": "Call of Robloxia 5 sequel...",
  "place_id": "292439477"
}
```

---

### Roblox Universe ID Lookup

`GET /conduitapi/roblox/universe`

Convert a Roblox place ID to its universe ID.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `place_id` | int | Yes | Roblox place ID |

**Example Request:**
```bash
curl "http://localhost:7000/conduitapi/roblox/universe?place_id=292439477"
```

**Example Response:**
```json
{
  "universe_id": "103279455"
}
```

---

### Steam Player Count

`GET /conduitapi/steam/player_count`

Get the current player count for a Steam game.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `appid` | int | Yes | Steam application ID |

**Example Request:**
```bash
curl "http://localhost:7000/conduitapi/steam/player_count?appid=730"
```

**Example Response:**
```json
{
  "appid": 730,
  "player_count": 892451,
  "checkedAt": "2024-01-15T12:00:00Z"
}
```

---

### Steam Game News

`GET /conduitapi/steam/news`

Get the latest news for a Steam game.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `appid` | int | Yes | - | Steam application ID |
| `count` | int | No | 10 | Number of news items |
| `maxlength` | int | No | 300 | Max content length per item |

**Example Request:**
```bash
curl "http://localhost:7000/conduitapi/steam/news?appid=730&count=2"
```

**Example Response:**
```json
{
  "appid": 730,
  "news": [
    {
      "gid": "5234567890",
      "title": "Counter-Strike 2 Update",
      "url": "https://store.steampowered.com/news/...",
      "author": "Valve",
      "contents": "Release Notes for today...",
      "date": 1705320000
    }
  ],
  "checkedAt": "2024-01-15T12:00:00Z"
}
```

---

### Epic Games Store

`GET /conduitapi/epic/games`

Get games from Epic Games Store curated collections. Returns popular titles including free-to-play games like Fortnite and Rocket League.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `count` | int | No | 10 | Number of games to return (max 100) |
| `collection` | string | No | "most-played" | Collection type (see below) |
| `free_only` | bool | No | false | Only return free games from the collection |

**Available Collections:**

| Collection | Description |
|------------|-------------|
| `most-played` | Most played games (includes F2P titles like Fortnite, Rocket League) |
| `top-sellers` | Best selling games |
| `most-popular` | Most popular games |
| `top-player-reviewed` | Highest rated by players |
| `top-wishlisted` | Most wishlisted upcoming games |

**Example Request - Most Played Games:**
```bash
curl "http://localhost:7000/conduitapi/epic/games?collection=most-played&count=10"
```

**Example Request - Top Sellers:**
```bash
curl "http://localhost:7000/conduitapi/epic/games?collection=top-sellers&count=5"
```

**Example Request - Free Games Only:**
```bash
curl "http://localhost:7000/conduitapi/epic/games?collection=most-played&free_only=true"
```

**Example Response:**
```json
{
  "games": [
    {
      "id": "09176f4ff7564bbbb499bbe20bd6348f",
      "title": "Fortnite",
      "publisher": "Epic Games",
      "description": "Fortnite",
      "store_url": "https://store.epicgames.com/en-US/p/fortnite",
      "images": [
        {
          "type": "Thumbnail",
          "url": "https://cdn1.epicgames.com/offer/fn/..."
        },
        {
          "type": "OfferImageWide",
          "url": "https://cdn1.epicgames.com/offer/fn/..."
        }
      ],
      "original_price": "0",
      "current_price": "0",
      "is_free": true
    },
    {
      "id": "9773aa1aa54f4f7b80e44bef04986cea",
      "title": "Rocket League",
      "publisher": "Psyonix LLC",
      "description": "Rocket League",
      "store_url": "https://store.epicgames.com/en-US/p/rocket-league",
      "images": [
        {
          "type": "OfferImageWide",
          "url": "https://cdn1.epicgames.com/offer/..."
        }
      ],
      "original_price": "0",
      "current_price": "0",
      "is_free": true
    }
  ],
  "checkedAt": "2024-01-15T12:00:00Z"
}
```

---

### Hytale Server Status

`GET /conduitapi/hytale/status`

Query a Hytale server's status. Supports two query methods depending on which plugin the server has installed.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `host` | string | Yes | - | Server hostname or IP address |
| `port` | int | No | 5523 (nitrado) / 5520 (hyquery) | Server query port |
| `method` | string | No | "nitrado" | Query method (see below) |

**Query Methods:**

| Method | Protocol | Default Port | Required Plugin |
|--------|----------|--------------|-----------------|
| `nitrado` | HTTP | 5523 | [Nitrado Query Plugin](https://github.com/nitrado/hytale-plugin-query) |
| `hyquery` | UDP | 5520 | [HyQuery Plugin](https://www.curseforge.com/hytale/mods/hyquery) |

> **Note:** Servers must have the appropriate query plugin installed to be queryable. Servers without a query plugin will return `isOnline: false`.

**Example Request - Nitrado Query (HTTP):**
```bash
curl "http://localhost:7000/conduitapi/hytale/status?host=my-hytale-server.com"
```

**Example Request - HyQuery (UDP):**
```bash
curl "http://localhost:7000/conduitapi/hytale/status?host=my-hytale-server.com&method=hyquery"
```

**Example Request - Custom Port:**
```bash
curl "http://localhost:7000/conduitapi/hytale/status?host=my-hytale-server.com&port=5530"
```

**Example Response:**
```json
{
  "isOnline": true,
  "serverName": "My Hytale Server",
  "version": "1.0.0",
  "onlinePlayers": 12,
  "maxPlayers": 50,
  "defaultWorld": "world",
  "players": [
    {
      "name": "Player1",
      "uuid": "550e8400-e29b-41d4-a716-446655440000",
      "world": "world"
    }
  ],
  "protocolVersion": 1,
  "checkedAt": "2026-01-18T12:00:00Z"
}
```

**Response when server is offline or unreachable:**
```json
{
  "isOnline": false,
  "serverName": null,
  "version": null,
  "onlinePlayers": null,
  "maxPlayers": null,
  "defaultWorld": null,
  "players": [],
  "protocolVersion": null,
  "checkedAt": "2026-01-18T12:00:00Z"
}
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | 7000 | Server port |
| `ROBLOX_CACHE_TTL` | 600 | Roblox endpoint cache TTL (seconds) |
| `STEAM_API_KEY` | - | Optional Steam API key |
| `STEAM_CACHE_TTL` | 600 | Steam endpoint cache TTL (seconds) |
| `EPIC_CACHE_TTL` | 600 | Epic Games endpoint cache TTL (seconds) |
| `HYTALE_CACHE_TTL` | 60 | Hytale endpoint cache TTL (seconds) |

---

## Caching

All endpoints except Minecraft server status use in-memory TTL caching to reduce external API calls and improve response times. Default cache TTL is 10 minutes (600 seconds), except for Hytale which uses 1 minute (60 seconds) for more real-time server status.

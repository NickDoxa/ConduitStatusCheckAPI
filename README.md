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

Get games from the Epic Games Store with optional filtering.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `count` | int | No | 10 | Number of games to return |
| `sort_by` | string | No | "releaseDate" | Sort field |
| `sort_dir` | string | No | "DESC" | Sort direction (ASC/DESC) |
| `free_only` | bool | No | false | Only return currently free games |

**Example Request - Recent Games:**
```bash
curl "http://localhost:7000/conduitapi/epic/games?count=5"
```

**Example Request - Free Games:**
```bash
curl "http://localhost:7000/conduitapi/epic/games?free_only=true"
```

**Example Response:**
```json
{
  "games": [
    {
      "title": "Bloons TD 6",
      "publisher": "Ninja Kiwi",
      "description": "The Bloons are back and better than ever!",
      "store_url": "https://store.epicgames.com/en-US/p/bloons-td-6-bf95a0",
      "images": [
        {
          "type": "Thumbnail",
          "url": "https://cdn1.epicgames.com/..."
        },
        {
          "type": "OfferImageWide",
          "url": "https://cdn1.epicgames.com/..."
        }
      ],
      "original_price": "$13.99",
      "current_price": "0",
      "is_free": true
    }
  ],
  "checkedAt": "2024-01-15T12:00:00Z"
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

---

## Caching

All endpoints except Minecraft server status use in-memory TTL caching (default: 10 minutes) to reduce external API calls and improve response times.

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Conduit Status Check API is a FastAPI-based REST service providing status checks and metadata for gaming platforms (Minecraft, Roblox, Steam, Epic Games). Single-file application deployed on Heroku.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server (default port 7000)
python StatusCheckService.py

# Run with custom port
PORT=8000 python StatusCheckService.py
```

No test suite is configured.

## Environment Variables

- `PORT` - Server port (default: 7000)
- `ROBLOX_CACHE_TTL` - Roblox cache TTL in seconds (default: 600)
- `STEAM_API_KEY` - Steam API key for authenticated requests
- `STEAM_CACHE_TTL` - Steam cache TTL in seconds (default: 600)
- `EPIC_CACHE_TTL` - Epic Games cache TTL in seconds (default: 600)

Use `.env` file for local development (python-dotenv enabled).

## Architecture

**Single-file architecture** (`StatusCheckService.py`):
1. Pydantic models for request/response validation
2. FastAPI endpoints under `/conduitapi/` prefix
3. In-memory TTL caching with asyncio.Lock for thread safety
4. Async HTTP calls via aiohttp to external APIs

**Caching Pattern:**
```python
# Each endpoint group has its own cache dict: Dict[str, Tuple[float, dict]]
# Cache key -> (expiration_timestamp, cached_response)
```

**External API Integration:**
- Minecraft: `mcstatus` library (supports both Java and Bedrock protocols)
- Roblox: REST API calls for universe lookup and game status
- Steam: REST API calls for player counts and news
- Epic Games: `epicstore_api` library (synchronous, wrapped with `asyncio.to_thread()`)

## API Endpoints

| Endpoint | Parameters | Notes |
|----------|------------|-------|
| `GET /conduitapi/servers/status` | `host` (required), `server_port` (optional) | Minecraft Java/Bedrock |
| `GET /conduitapi/roblox/status` | `place_id` or `universe_id` | Cached |
| `GET /conduitapi/roblox/universe` | `place_id` (int) | Cached |
| `GET /conduitapi/steam/player_count` | `appid` | Cached |
| `GET /conduitapi/steam/news` | `appid`, `count`, `maxlength` | Cached |
| `GET /conduitapi/epic/games` | `count`, `sort_by`, `sort_dir`, `free_only` | Cached |

## Code Conventions

- Pydantic models use camelCase field aliases for JSON responses (e.g., `playerCount`, `isOnline`)
- Internal Python uses snake_case
- Inline aiohttp imports within endpoint functions
- CORS enabled for all origins

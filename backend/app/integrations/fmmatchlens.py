import httpx
from typing import List
from app.telemetry.models import MatchFrame

async def fetch_match_frames(from_tick: int = 1, limit: int = 5) -> List[MatchFrame]:
    url = "http://127.0.0.1:16726/api/match/frames"
    params = {
        "fromTick": from_tick,
        "stride": 1,
        "limit": limit
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=5.0)
            response.raise_for_status()

            data = response.json()

            raw_frames = data.get("frames", [])

            parsed_frames = [MatchFrame.model_validate(frame) for frame in raw_frames]

            return parsed_frames
        except httpx.RequestError as e:
            print(f"Failed to communicate with FMMatchLens API: {e}")
    return []

async def fetch_player_names() -> dict[int, str]:
    url = "http://127.0.0.1:16726/api/match/meta"
    names: dict[int, str] = {}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=5.0)
            response.raise_for_status()
            data = response.json()

            if not data:
                return names
            
            players = data.get("players", [])
            if not isinstance(players, list):
                return names

            for player in players:
                if not isinstance(player, dict):
                    continue
                raw_id = player.get("playerId")
                name = player.get("displayName")

                if raw_id is None or not name:
                    continue
                try:
                    player_id = int(raw_id)
                except (TypeError, ValueError):
                    continue    

                names[player_id] = str(name)
        except httpx.RequestError as e:
            print(f"Failed to communicate with FMMatchLens API: {e}")
    return names


        


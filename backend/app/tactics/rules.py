from typing import List, Dict, Any, Optional
from app.telemetry.models import MatchFrame

def evaluate_player_fatigue(frame: MatchFrame, user_team: str = "home", condition_threshold: float = 75.0, player_names: Optional[Dict[int, str]] = None) -> List[Dict[str, Any]]:
    """Scans the match frame for players on pitch whose overall physical condition has dropped below the threshold, recommending potential substitutions."""
    fatigue_warnings = []
    if not frame.players:
        return fatigue_warnings

    for player in frame.players:
        """Important to only evaluate active player currently on the pitch who belong to the user's team."""
        if player.is_on_pitch and not player.is_substitute and player.team == user_team:
            condition = player.overall_physical_condition
            if condition is not None and condition < condition_threshold:
                if isinstance(player_names, dict):
                    name = player_names.get(player.player_id, f"Player #{player.player_id}")
                else:
                    name = f"Player #{player.player_id}"
                fatigue_warnings.append({
                    "player_id": player.player_id,
                    "player_name": name,
                    "team": player.team,
                    "current_condition": condition,
                    "advice": f"Player {name} is fatigued at {condition:.1f}% condtion. Consider a substitution."
                })
    return fatigue_warnings

def count_home_flanks(frame) -> tuple[int, int]:
    ball_y_m = frame.ball_y_centimeters / 100
    below = 0
    above = 0
    for player in frame.players or []:
        if player.team != "home" or player.y is None:
            continue
        if player.y < ball_y_m:
            below += 1
        elif player.y > ball_y_m:
            above += 1
    return below, above

def short_flank(frame, minimum: int = 6) -> str | None:
    below, above = count_home_flanks(frame)
    if below < minimum:
        return f"Short flank: {below} home players on the ball's side"
    return None

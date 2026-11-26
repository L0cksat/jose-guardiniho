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

def short_flank(frame, minimum: int = 4) -> str | None:
    below, above = count_home_flanks(frame)
    if below < minimum:
        return f"Short flank: {below} home players on the ball's side"
    return None

def count_press(frame: MatchFrame, user_team: str = "home", radius_m: float = 4) -> int:
    opponents = "away" if user_team == "home" else "home"
    
    ball_x_m = frame.ball_x_centimeters / 100
    ball_y_m = frame.ball_y_centimeters / 100
    near = 0

    for player in frame.players or []:
        if player.team != opponents or player.x is None or player.y is None:
            continue
             
        dx = player.x - ball_x_m
        dy = player.y - ball_y_m

        if (dx * dx + dy * dy) ** 0.5 < radius_m: near += 1

    return near

def press_warning(frame, user_team, minimum: int = 3) -> str | None:
    near = count_press(frame, user_team)
    if near >= minimum:
        return f"Press: {near} away players inside the 4 m."
    return None
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from typing import Optional, List

class PlayerFrame(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="allow")
    player_id: int
    team: Optional[str] = None
    is_ball_holder: Optional[bool] = None
    is_substitute: Optional[bool] = None
    is_on_pitch: Optional[bool] = None
    subbed_on_minute: Optional[int] = None
    subbed_off_minute: Optional[int] = None
    x: Optional[float] = None
    y: Optional[float] = None
    speed_centimeters_per_second: Optional[float] = None
    angle_degrees: Optional[float] = None
    rating: Optional[float] = None
    raw_internal_rating: Optional[float] = None
    overall_physical_condition: Optional[float] = None
    match_sharpness: Optional[float] = None
    distance_m: Optional[float] = None

class MatchFrame(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="allow")
    match_id: str
    sequence: int
    tick: int
    display_tick: int
    period: int
    captured_unix_milliseconds: int
    possession_team: Optional[str] = None
    ball_holder_player_id: Optional[int] = None
    ball_x_centimeters: Optional[float] = None
    ball_y_centimeters: Optional[float] = None
    ball_z_centimeters: Optional[float] = None
    players: Optional[List[PlayerFrame]] = None

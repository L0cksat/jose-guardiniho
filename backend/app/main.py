from fastapi import FastAPI, HTTPException, Query
from typing import List, Optional
from app.integrations.fmmatchlens import fetch_match_frames
from app.telemetry.models import MatchFrame, PlayerFrame
from app.telemetry.state import MatchStateManager
from app.telemetry.parser import parse_fmlens_player_metadata
from app.tactics.rules import evaluate_player_fatigue, count_home_flanks, short_flank, count_press, press_warning
from app.tactics.llm_advisor import generate_jose_advice
from app.integrations.fmmatchlens import fetch_player_names

app = FastAPI(
    title="José Guardiniho Backend",
    version="0.1.0",
    description="AI Assistant Manager for Football Manager 27 - Telemetry Ingestion API.",
)

state_manager = MatchStateManager(max_history_size=300)

LIVE_PLAYER_NAMES_MAP = {}

@app.get("/api/health")
async def health():
    return {
        "status": "ok, healthy",
        "service": "jose-guardiniho-backend",
        "mode": "read-only",
    }

@app.get("/api/match/frames", response_model=List[MatchFrame])
async def get_match_frames(
    from_tick: int = Query(1, description="Starting tick to fetch frames from"),
    limit: int = Query(5, description="Maximum number of frames to return")
):
    """Fetch raw and validated match telemetry frames from the local FMMatchLens provider."""
    
    frames = await fetch_match_frames(from_tick=from_tick, limit=limit)
    if not frames:
        raise HTTPException(
            status_code=503, 
            detail="Unable to fetch frames from FMMatchLens telemetry provider. Ensure FM27 and the plugin are running."
        )
    LIVE_PLAYER_NAMES_MAP.update(await fetch_player_names())

    for frame in frames:
        state_manager.update_state(frame)

        if frame.players:
            for player in frame.players:
                if player.player_id not in LIVE_PLAYER_NAMES_MAP:
                    LIVE_PLAYER_NAMES_MAP[player.player_id] = f"Player #{player.player_id}"

    return frames

@app.get("/api/match/state/recent", response_model=List[MatchFrame])
async def get_recent_state():
    """Retrieve the current rolling window of buffered match frames from memory."""
    return state_manager.get_recent_frames()

@app.get("/api/match/state/latest", response_model=Optional[MatchFrame])
async def get_latest_state():
    """Retrieve the absolute latest match frame observation stored in memory."""
    return state_manager.get_latest_frame()

@app.get("/api/tactics/analysis/fatigue")
async def analyze_fatigue(
    user_team: str = Query("home", description="The team identifier representing your squad ('home' or 'away')"),
    threshold: float = Query(75.0, description="Physical condition percentage threshold below which to flag fatigue"),
    model: str = Query("llama3.1:latest", description="Local Ollama model name to use")
):
    """
    Runs deterministic fatigue analysis against the latest match frame, 
    filtering strictly for your team using real-time state data.
    """
    latest_frame = state_manager.get_latest_frame()
    if not latest_frame:
        return {
            "status": "no_data",
            "message": "No match frames currently stored in memory. Fetch frames first via /api/match/frames."
        }
        
    warnings = evaluate_player_fatigue(
        latest_frame, 
        user_team=user_team, 
        condition_threshold=threshold,
        player_names=LIVE_PLAYER_NAMES_MAP
    )

    manager_advice = await generate_jose_advice(warnings, model_name=model)
    
    return {
        "match_id": latest_frame.match_id,
        "tick": latest_frame.tick,
        "user_team": user_team,
        "threshold_checked": threshold,
        "fatigue_warnings_count": len(warnings),
        "raw_warnings": warnings,
        "jose_advice": manager_advice
    }

@app.get("/api/tactics/analysis/shape")
async def analyze_shape(user_team: str = "home", from_tick: int =1):
    frames = await fetch_match_frames(from_tick=from_tick, limit=1)
    if not frames:
        return {"user_team": user_team, "detail": "No frame captured."}
    frame = frames[-1]
    below, above = count_home_flanks(frame)
    return {
        "user_team": user_team,
        "tick": frame.tick,
        "flank_below": below,
        "flank_above": above,
        "short_flank": short_flank(frame),
        "press_count": count_press(frame, user_team),
        "press_warning": press_warning(frame, user_team),
    }

from app.telemetry.models import PlayerFrame

@app.post("/api/match/frames/seed-mock")
async def seed_mock_frame():
    """
    Injects a mock match frame with fatiguing players into the state manager 
    so you can test tactical rules and Ollama advice without FM27 running.
    """
    mock_frame = MatchFrame(
        match_id="mock-match-99",
        sequence=1,
        tick=1250,
        display_tick=67,
        period=1,
        captured_unix_milliseconds=1700000000000,
        possession_team="home",
        ball_holder_player_id=10,
        ball_x_centimeters=1200,
        ball_y_centimeters=3400,
        ball_z_centimeters=0,
        players=[
            PlayerFrame(
                player_id=10,
                team="home",
                is_ball_holder=True,
                is_substitute=False,
                is_on_pitch=True,
                x=1100,
                y=3300,
                overall_physical_condition=68.5  # Fatigued! Should trigger warnings
            ),
            PlayerFrame(
                player_id=7,
                team="home",
                is_ball_holder=False,
                is_substitute=False,
                is_on_pitch=True,
                x=1500,
                y=2000,
                overall_physical_condition=92.0  # Fresh
            )
        ]
    )
    
    # Push straight into the state manager
    state_manager.update_state(mock_frame)
    
    return {
        "status": "success",
        "message": "Mock frame seeded successfully into memory!",
        "frame": mock_frame
    }


import pytest
from app.telemetry.state import MatchStateManager
from app.telemetry.models import MatchFrame


def test_match_state_manager_maxlen():
    """""Initialize with a small max size for testing evicition behavior"""
    manager = MatchStateManager(max_history_size=3)

    """Create dummy MatchFrames with sequential ticks"""
    frame1 = MatchFrame(match_id="match-1", sequence=1, tick=10, display_tick=10, period=1, captured_unix_milliseconds=1000)
    frame2 = MatchFrame(match_id="match-1", sequence=2, tick=11, display_tick=11, period=1, captured_unix_milliseconds=1001)
    frame3 = MatchFrame(match_id="match-1", sequence=3, tick=12, display_tick=12, period=1, captured_unix_milliseconds=1002)
    frame4 = MatchFrame(match_id="match-1", sequence=4, tick=13, display_tick=13, period=1, captured_unix_milliseconds=1003)

    """Add frames up to limit (3 frames)"""
    manager.update_state(frame1)
    manager.update_state(frame2)
    manager.update_state(frame3)

    """Verify lenght and order"""
    recent_frames = manager.get_recent_frames()
    assert len(recent_frames) == 3
    assert recent_frames[0]. tick == 10
    assert recent_frames[-1]. tick == 12

    """Add a 4th frame, which should automatically drop frame1 (tick10)"""
    manager.update_state(frame4)

    updated_frames = manager.get_recent_frames()
    assert len(updated_frames) == 3
    assert updated_frames[0].tick == 11
    assert updated_frames[1].tick == 12
    assert updated_frames[2].tick == 13
    assert manager.get_latest_frame().tick == 13

def test_match_state_manager_match_switch():
    manager = MatchStateManager(max_history_size=3)

    frame1 = MatchFrame(match_id="match-1", sequence=1, tick=10, display_tick=10, period=1, captured_unix_milliseconds=1000)
    manager.update_state(frame1)
    assert len(manager.get_recent_frames()) == 1

    frame_new_match = MatchFrame(match_id="match-2", sequence=1, tick=1, display_tick=1, period=1, captured_unix_milliseconds=2000)
    manager.update_state(frame_new_match)

    recent_frames = manager.get_recent_frames()
    assert len(recent_frames) == 1
    assert recent_frames[0].match_id == "match-2"
    assert recent_frames[0].tick == 1

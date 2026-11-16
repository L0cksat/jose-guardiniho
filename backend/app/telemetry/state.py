from collections import deque
from typing import List, Optional
from app.telemetry.models import MatchFrame

class MatchStateManager:
    def __init__(self, max_history_size: int = 300):
        self._frames: deque[MatchFrame] = deque(maxlen=max_history_size)
        self._current_match_id: Optional[str] = None

    def update_state(self, frame: MatchFrame) -> None:
        """Adds a new frame, resetting history if a new match ID is detected."""
        if self._current_match_id != frame.match_id:
            self._current_match_id = frame.match_id
            self._frames.clear()
        self._frames.append(frame)

    def get_recent_frames(self) -> List[MatchFrame]:
        """Returns all currently buffered frames as a standard list."""
        return list(self._frames)

    def get_latest_frame(self) -> Optional[MatchFrame]:
        """Returns the most recent frame observation."""
        if self._frames:
            return self._frames[-1]
        return None

    def clear(self) -> None:
        """Resets the state manager"""
        self._frames.clear()
        self._current_match_id = None
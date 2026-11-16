import asyncio
from app.integrations.fmmatchlens import fetch_match_frames
from app.telemetry.models import MatchFrame


def test_fetch_match_frames_live():
    async def run_test():
        frames = await fetch_match_frames(from_tick=1, limit=5)

        assert isinstance(frames, list)

        if len(frames) > 0:
            first_frame = frames[0]
            assert isinstance(first_frame, MatchFrame)
            assert first_frame.match_id is not None
            assert first_frame.tick >= 1

            print(f"Successfully fetched frame {first_frame.tick} for match {first_frame.match_id} with {len(first_frame.players or [])} players.")
    asyncio.run(run_test())
# Milestone 1 — telemetry proof of concept

## Goal

Prove that FM27 Steam + FMMatchLens can provide reliable match data to a local Python
process, and preserve a replayable test sample.

## Acceptance criteria

- [ ] FM27 launches normally with the instrumentation installed.
- [ ] FMMatchLens health endpoint responds.
- [ ] A live match is detected.
- [ ] Actual response payloads are captured and documented.
- [ ] Player/team identity and timestamps can be parsed.
- [ ] A match archive can be saved and replayed.
- [ ] José can ingest sample data without writing to the game.
- [ ] No save files or tactical settings are modified.

## Important compatibility note

FMMatchLens release v0.7.0 introduced FM27 Steam support; v0.7.1 is a subsequent fix.
The repository README may lag behind release notes. Follow the release-specific notes
and verify the BepInEx 6 IL2CPP x64 build required by that release. Do not assume an
older FM26 installation recipe is compatible.

## Updated 12 November 2026

The checklist above still stands. Current spike is the pitch-dimension failure path in handover section 22. GPU/VRAM for model selection is still unconfirmed.

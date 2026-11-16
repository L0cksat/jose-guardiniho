# José Guardiniho
## Technical Architecture & Development Handover
**Project planning baseline — 10 November 2026**

> Purpose: this document is the current source of truth for moving José Guardiniho development into Cursor. It records the goals, architecture, decisions, evidence, known risks, starter Python package, FMMatchLens investigation and proposed development sequence. It distinguishes verified facts from hypotheses and future design.

---

## 1. Project purpose

José Guardiniho is an AI assistant manager for Football Manager 27 (FM27). Its job is to observe live match telemetry, interpret the tactical situation, and recommend precise tactical adjustments that the human manager can choose to implement.

José is an adviser, not an autonomous game controller.

### Core product behaviour

José should:
- Observe live match state and player/team performance.
- Detect tactical patterns, problems and opportunities.
- Explain findings with supporting evidence from the match data.
- Recommend specific changes that exist in the FM27 interface.
- State confidence, expected benefit, trade-offs and urgency.
- Track whether the situation improves after a human implements a recommendation.
- Keep a match timeline so the user can understand what changed and why.

José must not:
- Click or change FM27 instructions automatically.
- Modify saves or game files.
- invent tactical instructions that do not exist in the installed FM27 version.
- Treat a single noisy frame as conclusive evidence.
- present model-generated explanations as facts when telemetry does not support them.

The human remains in control of all tactical decisions.

## 2. Current environment and constraints

| Area | Current information |
|---|---|
| Game | Football Manager 27, Steam, Windows |
| Match telemetry reference | FMMatchLens v0.7.3 (current test); v0.7.1 source investigation retained as historical reference |
| Plugin framework | BepInEx 6 IL2CPP |
| Game module | `game_plugin.dll` |
| Local model runtime | Ollama, intended to run natively on Windows |
| Development | Python backend; proposed C# BepInEx telemetry plugin; Angular dashboard later |
| Host memory | 32 GB RAM |
| GPU/VRAM | Not yet confirmed; model choice must wait for this |
| User's coding preference | Socratic, guided learning; C# is rusty (last studied around 2010) |
| Safety principle | José advises; user manually applies every change |

The local machine's exact GPU, VRAM, CPU and free disk capacity remain to be confirmed before selecting an Ollama model.

## 3. Product and system architecture

### 3.1 Proposed high-level architecture

```text
                         WINDOWS HOST
┌───────────────────────────────────────────────────────────────────┐
│                                                                   │
│  Football Manager 27 (Steam)                                      │
│       │                                                           │
│       │ in-process match-update hook                              │
│       ▼                                                           │
│  José Telemetry Plugin (C# / BepInEx 6 IL2CPP)                    │
│       │                                                           │
│       │ compact, versioned JSON events/snapshots                  │
│       ▼                                                           │
│  José Backend (Python / FastAPI)                                  │
│       ├── Telemetry ingestion and validation                      │
│       ├── Match state / rolling windows                           │
│       ├── Tactical observations and rules                         │
│       ├── Ollama client                                           │
│       ├── Recommendation validation                               │
│       └── SQLite persistence                                      │
│       │                                                           │
│       ├──────────────► Ollama (local LLM API)                     │
│       │                                                           │
│       ▼                                                           │
│  José Dashboard (Angular; planned)                                │
│       ├── Live match view                                         │
│       ├── Tactical alerts                                         │
│       ├── Evidence and confidence                                  │
│       └── Recommendation history                                   │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘

Separate development environment:
Docker / WSL2 → isolated coding agents and development tooling only.
```

### 3.2 Component responsibilities

**A. José Telemetry Plugin (C#)**  
Runs inside the FM27 process through BepInEx IL2CPP. It is responsible only for safe, efficient extraction and publication of game telemetry. It should not run LLM inference or tactical reasoning.

**B. José Backend (Python)**  
Receives telemetry, validates it, maintains current match state, derives observations, coordinates analysis, stores history and communicates with Ollama. This is the core application/service layer.

**C. Tactical analysis layer**  
A deterministic/rule-based layer should identify measurable patterns before an LLM is asked to explain or prioritise them. The LLM should reason over structured observations, not be asked to infer the entire match from raw, enormous frame dumps.

**D. Ollama**  
Hosts local language models. Model choice and quantisation depend on actual GPU VRAM, CPU and available RAM. Do not download a large model until hardware is checked.

**E. Dashboard**  
An Angular application is planned for live presentation. It should consume José's backend API/WebSocket, not communicate directly with FMMatchLens or read game memory.

**F. Persistence**  
SQLite is the initial local database candidate for match metadata, observations, recommendations and selected telemetry summaries. Raw high-frequency frames should be retained only when useful; avoid unbounded storage.

### 3.3 Process placement and isolation

- FM27, BepInEx plugin, José backend and Ollama run on the Windows host.
- Ollama is intended to run natively on Windows, not inside Docker.
- Docker/WSL2 is intended for isolated development agents, not for the live game integration.
- Development agents should have access only to the José project workspace and explicitly approved tooling.
- Do not mount the Docker socket into agent containers.
- Do not expose the game process, save files, SSH keys, personal folders or credentials to agents.
- Bind local services to loopback (`127.0.0.1`) unless a deliberate, reviewed requirement says otherwise.
- Do not expose the telemetry API or Ollama API to the LAN or public internet.

## 4. Telemetry strategy: validate FMMatchLens as the first data source

### 4.1 Current decision

The immediate preferred direction is to **consume FMMatchLens v0.7.3's local HTTP/WebSocket telemetry from the José backend**, rather than build another native hook now. This is a provisional integration decision based on successful live capture diagnostics and post-match frame retrieval.

José should own its backend, normalised data contract, analysis, persistence and dashboard. FMMatchLens remains an external telemetry provider, not José's application architecture. Do not make a José-owned native plugin the next task unless further tests show that the existing feed is insufficient or unreliable.

Archive ingestion remains a separate validation task. The fact that the API can return completed-match frames does not yet prove that `.fmlens` archive writing/finalisation or dashboard archive browsing works.

### 4.2 Evidence supporting this direction

FMMatchLens v0.7.3 has, in the user's current FM27.0 session:
- Loaded and reported plugin version `0.7.3`.
- Detected an unrecognised `game_plugin.dll` SHA-256 and reported attempting an AOB fallback GAME_MATCH hook at RVA `0x4764AC0`.
- Reported installing the GAME_MATCH Advance post-hook with a permanent native trampoline. This is plugin-reported installation success; the address has not been independently verified.
- Identified a candidate match with 40 players, home/away team UIDs and manager UIDs, and classified/locked it as the current session.
- Reported lock health with runtime teams readable, `missingTicks=0`, `outOfOrder=0`, and `records=1936` in the observed log sample.
- Reported health status `live`, `inMatch=true`, and one WebSocket connection during the match.
- After the match, returned API metadata with `status="ended"`, `totalFrameCount=23777`, and five requested frame objects when queried from tick 1.

These observations are strong evidence that the API frame endpoint can serve a substantial completed-match timeline. They do not yet prove every frame field is valid, that every tick is present, that WebSocket delivery is complete, or that archives are finalised correctly.

### 4.3 Future fallback option

A José-owned telemetry plugin may still be justified if FMMatchLens's API lacks required fields, loses data, proves unstable across game updates, or cannot meet José's latency/reliability requirements. If that becomes necessary, investigate the extraction path and dependencies first; do not copy the entire plugin or assume every offset is validated. Keep game-version-specific code isolated behind a compatibility layer.

## 5. FMMatchLens v0.7.1 source investigation

### 5.1 Version and build match

The source archive inspected is the plugin source from tag `v0.7.1`, commit:

- Tag: `v0.7.1`
- Commit: `f0582d3`
- Installed plugin: FMMatchLens 0.7.1
- Game: Football Manager 27.0, Steam
- Detected distribution/build: `steam-26340721`
- `game_plugin.dll` SHA-256:
  `252ff8fb5b7a4a5a5464db6ba632e309eef9b6e65ffa992ae20575a189e66c6a`
- Hook RVA: `0x4532A00`

These build identifiers match the user's BepInEx log. This makes v0.7.1 the appropriate source baseline for understanding the installed plugin. It does not prove that every internal field or method is correct for every future FM27 update.

### 5.2 Verified extraction pipeline

The inspected code establishes this broad sequence:

1. `Plugin.Load()` configures logging, creates archive/timeline/API services, starts the local API, and attempts to install the match hook.
2. `GameMatchTickHook.Start()` checks for a 64-bit process and locates `game_plugin.dll`.
3. `GamePluginBuildCatalog` identifies the module build using its hash and supplies a match-update hook RVA.
4. `INativeDetour.CreateAndApply()` installs a native detour and returns an original-function delegate.
5. The hook invokes the original match-update function.
6. After the original function returns, FMMatchLens opens a fresh virtual-memory read scope and attempts to capture updated match state.
7. Tick records and real-time frames are written into buffers.
8. Background drain/timeline/API components make captured data available outside the native hook callback.

Important implementation details:
- The hook has a retry timer because `game_plugin.dll` may not be loaded when the plugin first starts.
- The FM27 log showed the initial module-not-loaded warning followed by successful build detection and hook installation.
- The code serialises the selected animated instance's original-plus-capture section with a lock.
- It catches managed exceptions at the native callback boundary so they do not cross reverse-P/Invoke.
- It uses separate buffers and timers to keep more expensive processing away from the native callback path.
- Comments explicitly warn against a particular trampoline implementation because it can race when the original function is invoked concurrently.

### 5.3 Important source files

| Source file | Responsibility / investigation target |
|---|---|
| `Plugin.cs` | Plugin lifecycle, configuration, API startup, hook startup/retry |
| `Memory/GameMatchTickHook.cs` | Native detour, match-instance discovery, capture orchestration |
| `Memory/GamePluginBuildCatalog.cs` | Supported game build identification and hook RVA |
| `Memory/Offsets.cs` | Reverse-engineered structure offsets; requires validation |
| `Memory/VirtualMemory.cs` | Read-scope and memory-read safety |
| `Memory/MemoryReader.cs` | Typed reads: byte, integer, float, pointer, etc. |
| `Memory/CaptureSnapshots.cs` | Match/team/player metadata and snapshot extraction |
| `Memory/PlayerUidReader.cs` | Player identity resolution |
| `Memory/PlayerUidCache.cs` | Cached player UID mapping |
| `Memory/FramePlayerIdentityCache.cs` | Identity association for frame data |
| `Memory/TacticalFormationDecoder.cs` | Decodes position masks, roles and duties |
| `Memory/NativeMomentumSource.cs` | Reads native momentum source and pitch dimensions |
| `Memory/RealtimeTickFrameBuffer.cs` | Buffers real-time frames |
| `Memory/GameMatchTickRecordBuffer.cs` | Buffers tick records |
| `Domain/RealtimeTickFrame.cs` | Captured frame data structures |
| `Domain/TacticalSnapshot.cs` | Tactical snapshot domain model |
| `Services/RealtimeMatchTimeline.cs` | Timeline and live data orchestration |
| `Services/LocalApiServer.cs` | Local HTTP API |
| `Services/WebSocketHub.cs` | Live WebSocket publishing |
| `Services/ArchiveWriter.cs` | FMMatchLens archive writing; José intends to replace this |
| `Services/ArchiveReader.cs` | FMMatchLens archive reading; not required for José's initial collector |

### 5.4 Memory extraction and offsets

`MemoryReader.cs` wraps typed reads and checks whether memory ranges are readable through `VirtualMemory` before reading. It supports pointers and primitive types including floats.

`Offsets.cs` describes internal FM structures. Examples include:
- `GameMatch.HomeTeam`
- `GameMatch.AwayTeam`
- `GameMatch.BallPosition`
- `GameMatch.Tick`
- `GameMatch.DisplayTick`
- `GameMatch.Period`
- `Team.PlayerTable`
- `Team.PlayerCount`
- `MomentumEventSource.HalfPitchWidth`
- `MomentumEventSource.HalfPitchLength`

Offsets are relative to particular structures, not global addresses. Correctly resolving the base object and pointer chain is essential.

Some comments in `Offsets.cs` explicitly mark legacy/unconfirmed locations. Do not use every constant indiscriminately. Build a field-by-field validation table before adopting offsets.

### 5.5 Player and tactical data

FMMatchLens separates live frame capture from richer player metadata capture.

**Live frame examples**
- Player ID / slot and team.
- Position coordinates.
- Speed and angle.
- Rating and condition-related fields.
- Match statistics such as goals, shots, xG, passes, tackles and aerials.

**Player metadata examples**
- Name and display name.
- UID.
- Profile and attributes.
- Position familiarity.
- In-possession tactical assignment.
- Out-of-possession tactical assignment.
- Role and duty information.

This split is desirable for José: capture fast-changing values frequently and refresh slower-changing metadata only when necessary (for example at match start, squad change or substitution).

`TacticalFormationDecoder.cs` converts bit masks and role/duty values into readable tactical positions and role labels. Its decoded outputs should be cross-checked against the FM27 UI and known match states.

### 5.6 Match hook and capture safety

The hook executes inside the game process. This is a high-risk integration boundary.

Design requirements for José:
- Keep the native hook callback short and predictable.
- Call the original function exactly as required by the verified detour design.
- Do not allow managed exceptions to cross the native callback boundary.
- Avoid blocking I/O, HTTP calls, database operations or LLM calls in the hook.
- Avoid allocations and expensive reflection in high-frequency capture paths where practical.
- Use bounded buffers and explicit dropped-frame counters.
- Move serialisation, network publishing and analysis to background processing.
- Validate pointers, ranges, object lifetimes and game version before dereferencing.
- Provide a kill switch / clean unload path.
- Never assume a pointer remains valid across ticks without evidence.

## 6. Known FMMatchLens archive issue and pitch-dimension investigation

### 6.1 Observed log

The user's FMMatchLens v0.7.1 log showed:
- Plugin loaded for Football Manager 27.0.
- The match hook initially could not install because `game_plugin.dll` was not yet loaded.
- The plugin subsequently detected the exact DLL build and installed the hook.
- It locked onto a match simulation.
- It reported pre-lock frames committed: cached 5, appended 5, tick range 1–5.
- It reported `pitchBackfilled=0` and `pitchSourceTick=-1`.
- Archive writer then failed with `Pitch dimensions are invalid`.
- Finalisation failed for that `.fmlens` archive.

The dashboard error `Archive contains no complete match frames` is consistent with the failed archive finalisation. This specific log does not prove that archives only complete when the next match starts.

### 6.2 Relevant source path

In `NativeMomentumSource.cs`, FMMatchLens reads:
- Half pitch width at offset `0xE0`.
- Half pitch length at offset `0xE4`.

The source pointer is obtained through the match's momentum-event-source field. The code checks that the values are finite and positive. If validation fails, it does not return valid pitch dimensions.

The hook also has a `BackfillLeadingPitchDimensions()` mechanism intended to populate earlier frames from later frames with valid dimensions.

### 6.3 What is established vs unknown

Established:
- The archive writer rejects invalid pitch dimensions.
- The source code reads dimensions through the native momentum source.
- The observed log indicates no pitch backfill was performed for that archive.
- The previous successful frame sample contained `halfPitchWidth = 34.3125` and `halfPitchLength = 50.325`.

Unknown:
- Whether the pointer was null, stale, unreadable or pointed to a structure with zero/invalid values.
- Whether the dimensions are populated later in a match or vary by match context.
- Whether the FM27 offsets are correct in every runtime state.
- Whether the issue is specific to the failing match, a timing issue or an implementation defect.

Do not “fix” this by silently substituting hard-coded pitch dimensions. First instrument and validate the source pointer and raw values in a controlled test.

### 6.4 Updated v0.7.3 test — live hook and completed-match API retrieval

**Test context:** FM27.0, FMMatchLens v0.7.3, match ID `match-1794699680854`. The match has ended.

The user's `LogOutput.log` reported:
- Detected `game_plugin.dll` SHA-256: `8c6971ce0b1c8afe6529ea3f46205a5175aea988a97d7421a980da42e23fe340`.
- The build was not recognised by the exact build catalogue, so the plugin attempted its AOB fallback GAME_MATCH hook at RVA `0x4764AC0`.
- The log reported that the GAME_MATCH Advance post-hook was installed with a permanent native trampoline. This is evidence of the plugin's own successful installation report, not independent verification of the native address.
- A match candidate was found with 40 players (23 home, 17 away), team and manager UIDs, and `eligible=True`; classification reported `result=current_session` and `activeSessions=1`.
- Lock-health sample: `records=1936`, `missingTicks=0`, `outOfOrder=0`, `runtimeTeamsReadable=True`.

The health endpoint during the match returned `status="live"`, `pluginVersion="0.7.3"`, `gameVersion="27.0"`, `inMatch=true`, `tick=8385`, `frameCount=8385`, and `webSocketConnections=1`. These counters were observed at a different time/sample from the log's `records=1936`; do not assume they are the same counter.

After the match, the frame API returned:

```json
{
  "matchId": "match-1794699680854",
  "status": "ended",
  "totalFrameCount": 23777,
  "frames": []
}
```

The empty array was explained by the request query beginning at `fromTick=23778`, one tick beyond the last recorded tick implied by `totalFrameCount=23777`. Querying `fromTick=1&stride=1&limit=5` returned five frame objects with ticks 1–5 and sequences 1444, 1445, 1446, 1448 and 1451. This confirms that the completed-match API endpoint can retrieve frame objects from the beginning of this match. Sequence values are not contiguous in this sample; do not equate sequence gaps with missing ticks because all five requested ticks were returned.

**Still unresolved:** the dashboard continues to display this completed match as “Live Match”. The API itself reports `status="ended"`. This may be a dashboard state/selection issue, but the cause is not established. The user also previously observed `Archive writer failed: Pitch dimensions are invalid`; it is not yet established whether that warning applies to this v0.7.3 match or whether `.fmlens` archive finalisation succeeded.

**Next validation:** query the last five ticks (`fromTick=23773&stride=1&limit=5`) and inspect one complete frame object for its field structure and values. Then separately establish whether a `.fmlens` file exists and whether archive opening/replay works. Do not start another native hook project while the current API feed is being validated.

## 7. Telemetry data already observed

### 7.1 Live frame structure

A previously supplied live response contained:
- `matchId`
- `sequence`
- `tick`
- `displayTick`
- `capturedUnixMilliseconds`
- `period`
- `possessionTeam`
- `ballHolderPlayerId`
- Ball X/Y/Z coordinates in centimetres
- Half-pitch dimensions
- Home/away team statistics
- Player frame array
- Momentum fields
- Rating model fields

Observed player fields included:
- `slot`, `playerId`, `team`
- `isBallHolder`, `isSubstitute`, `isOnPitch`
- `x`, `y`, `speedCentimetersPerSecond`, `angleDegrees`
- `rating`
- `subbedOnMinute`, `subbedOffMinute`
- Goals, assists, xG, xA, shots, shots on target, blocked shots
- Passes, completed passes, progressive passes, key passes
- Tackles, aerials, interceptions, clearances
- Goalkeeper saves
- Distance in metres
- `ratingInputs`

### 7.2 Match metadata

A separate metadata response was observed and can be joined to frames by `matchId` and `playerId`.

It included:
- Match ID and start time.
- Match date and competition.
- Home/away team names and UIDs.
- Manager names and human-controlled status.
- Team colours.
- Pitch dimensions.
- Player identities, names, display names and profile information.
- Attributes and position familiarity.
- In-possession and out-of-possession roles/duties.

This separation is useful: store match/player metadata once and refer to players by stable IDs in live frames.

### 7.3 Data interpretation cautions

- `sequence` and `tick` are different counters.
- The four-frame sample showed sequence incrementing by one, while tick skipped one value between two frames. Do not assume one captured frame equals one simulation tick.
- Capture intervals varied in the four-frame sample; four frames are not enough to infer a sampling schedule.
- `tick` and `displayTick` must not be treated as match minutes without calibration.
- `shirtName` contained values such as `"82'"`, `"58'"`, `"Stages"` and `"20:00"` in the supplied metadata. Do not assume this field is a player name.
- Condition and match sharpness values appear scaled; establish their range and meaning before converting them to percentages.
- `seasonStats.friendly` may not represent the current match. Validate its time scope before using it.
- A player's nominal/squad position can differ from the actual in-possession and out-of-possession position.
- Momentum fields were empty in the supplied frame examples. Do not assume the native momentum subsystem is always available.
- The first live sample contained 39 player records; another archive contained 41. Player counts may vary with match squads and substitutes.

## 8. José telemetry contract (proposed, not implemented)

The plugin/backend boundary should use a small, versioned schema owned by José. Do not expose FMMatchLens's internal classes directly as José's permanent API.

Recommended initial event types:

1. `match_started`
2. `match_metadata`
3. `player_metadata`
4. `frame_snapshot`
5. `substitution`
6. `period_changed`
7. `match_ended`
8. `telemetry_health`

Recommended envelope:

```json
{
  "schema_version": 1,
  "event_type": "frame_snapshot",
  "match_id": "stable-match-id",
  "sequence": 12345,
  "game_tick": 1500,
  "display_tick": 1499,
  "captured_at_utc": "2026-11-10T11:47:00.000Z",
  "payload": {}
}
```

The exact schema, transport and event frequency remain design decisions. A local HTTP endpoint or WebSocket can be chosen after the first collector prototype. Keep the first iteration simple and observable.

Recommended principles:
- Explicit units in field names (`x_cm`, `speed_cm_s`, `distance_m`).
- Stable player IDs; do not use player names as keys.
- Include source/build identifier and telemetry schema version.
- Include capture health (dropped frames, invalid reads, stale data).
- Distinguish missing/unknown values from real zero values.
- Include monotonic sequence and timestamp.
- Avoid sending full player profiles every frame.
- Validate all incoming payloads in Python.

## 9. Python starter package: `jose-guardiniho`

A starter project ZIP was previously generated for the user. It was a deliberately minimal scaffold, not a completed José application. The original download was provided as `jose-guardiniho-starter.zip`. The current handover documents its intended contents and responsibilities.

### 9.1 Starter layout

```text
jose-guardiniho/
├── README.md
├── .gitignore
├── docs/
│   ├── architecture.md
│   ├── milestone-1.md
│   ├── model-selection.md
│   ├── vision.md                 (planned / may be added)
│   └── telemetry-contract.md     (planned / may be added)
└── backend/
    ├── requirements.txt
    ├── .env.example
    ├── app/
    │   ├── main.py
    │   ├── integrations/
    │   │   └── fmmatchlens.py
    │   ├── telemetry/
    │   │   └── models.py
    │   ├── analysis/
    │   │   └── observations.py
    │   └── llm/
    │       └── ollama_client.py
    └── tests/
        └── test_health.py
```

Note: the initial scaffold contained placeholder modules for the FMMatchLens integration, telemetry models, observations and Ollama client. The `vision.md` and `telemetry-contract.md` files above are recommended additions, not confirmed files in the original ZIP.

### 9.2 Python dependencies

The starter `requirements.txt` included:
- FastAPI — HTTP API framework.
- Uvicorn — ASGI server.
- Pydantic Settings — typed configuration from environment variables.
- HTTPX — asynchronous HTTP client, intended for local Ollama/plugin API communication.
- Pytest — automated tests.

Pin exact versions before a reproducible production setup. Add dependencies only when a concrete feature requires them.

### 9.3 Module responsibilities

**`backend/app/main.py`**
- FastAPI application entry point.
- Initial health/status routes.
- Later: telemetry ingestion and WebSocket routes.
- Should remain thin; business logic belongs in dedicated modules/services.

**`backend/app/integrations/fmmatchlens.py`**
- Originally a placeholder integration adapter.
- It must not become a permanent hard dependency on FMMatchLens.
- It can be retained temporarily for comparative testing or replaced with `jose_plugin.py` / `telemetry_ingest.py` when the José plugin is ready.
- Do not invent undocumented FMMatchLens API endpoints or response schemas.

**`backend/app/telemetry/models.py`**
- Pydantic models for validated match metadata, player metadata, frame snapshots and telemetry events.
- This should become the canonical Python representation of José's versioned telemetry contract.

**`backend/app/analysis/observations.py`**
- Deterministic analysis and observation models.
- Examples: flank overload, opposition progression, central compactness, isolated striker, pressing effectiveness.
- Observations must include evidence, time window, confidence and limitations.

**`backend/app/llm/ollama_client.py`**
- HTTPX-based client for Ollama's local API.
- Responsible for model invocation, timeout handling, error reporting and structured response parsing.
- The LLM should explain/rank grounded observations rather than invent raw match facts.

**`backend/tests/test_health.py`**
- Initial health endpoint test.
- Expand with telemetry validation, unit conversion, sequence handling, observation rules and Ollama client mocks.

### 9.4 Initial configuration

The scaffold included `.env.example`. Use environment configuration for settings such as:
- Backend bind host and port.
- Ollama base URL (expected local default: `http://127.0.0.1:11434`).
- Ollama model name (to be selected after hardware assessment).
- Database path.
- Logging level.

Do not commit real secrets. No cloud API key is required for the intended local Ollama workflow.

### 9.5 Suggested Python backend growth

```text
backend/app/
├── main.py
├── core/
│   ├── config.py
│   └── logging.py
├── api/
│   ├── routes_health.py
│   ├── routes_telemetry.py
│   └── routes_recommendations.py
├── telemetry/
│   ├── models.py
│   ├── validator.py
│   ├── state.py
│   └── normalizer.py
├── integrations/
│   ├── ollama.py
│   └── jose_plugin.py
├── analysis/
│   ├── observations.py
│   ├── rules/
│   ├── windows.py
│   └── confidence.py
├── recommendations/
│   ├── models.py
│   ├── instruction_catalog.py
│   └── validator.py
├── persistence/
│   ├── database.py
│   └── repositories/
└── tests/
```

This is a proposed evolution, not code already present.

## 10. Tactical intelligence design

José should use a layered reasoning approach:

1. **Raw telemetry** — positions, ball, team/player stats, time, roles.
2. **Normalisation** — units, team orientation, pitch coordinates, rolling windows, missing values.
3. **Derived metrics** — width, depth, distances, compactness, progression, pressure proxies, overloads.
4. **Observations** — evidence-backed statements about what is happening.
5. **Tactical interpretation** — likely causes and possible FM27 instruction changes.
6. **Recommendation validation** — check against a maintained catalogue of actual FM27 instructions/options.
7. **Human decision** — user chooses whether to implement.
8. **Outcome tracking** — compare subsequent telemetry to the pre-change baseline.

Each recommendation should ideally include:
- Problem/opportunity.
- Evidence and time window.
- Proposed instruction change, using exact FM27 wording.
- Expected effect.
- Potential downside/trade-off.
- Confidence.
- Urgency.
- What telemetry would confirm or disprove the diagnosis.

Do not let the LLM fabricate FM27 settings. Build a structured instruction catalogue from the actual game UI/manual/testing.

## 11. Development milestones

### Milestone 0 — Project baseline and learning setup
- Open the starter project in Cursor.
- Add this handover document to `docs/`.
- Verify Python environment and starter tests.
- Confirm Windows hardware for Ollama model choice.
- Keep a Git baseline and separate feature branches.

### Milestone 1 — Understand FMMatchLens
- Review v0.7.1 source in this order:
  1. `GameMatchTickHook.cs`
  2. `GamePluginBuildCatalog.cs`
  3. `Offsets.cs`
  4. `VirtualMemory.cs` and `MemoryReader.cs`
  5. `CaptureSnapshots.cs`
  6. `TacticalFormationDecoder.cs`
  7. `RealtimeTickFrame.cs`
  8. `RealtimeMatchTimeline.cs`
- Produce a data dictionary for the exact fields José needs.
- Mark each offset as verified, provisional or unknown.
- Identify the minimum viable capture fields.

### Milestone 2 — C# fundamentals and plugin skeleton
- Refresh C# basics as needed: types, classes, structs, nullable references, delegates, events, `using`/`IDisposable`, exceptions, generics, async concepts and project files.
- Create a separate José plugin project.
- Build and load a harmless BepInEx plugin before adding hooks.
- Verify logging and clean unload.

### Milestone 3 — Minimal live telemetry proof of concept
- Detect FM27 build.
- Install a validated hook.
- Capture match identity, tick, period, teams, ball position, pitch dimensions and player IDs/positions.
- Publish a versioned local JSON snapshot.
- No AI or dashboard yet.
- Compare values with FMMatchLens and the in-game UI.

### Milestone 4 — Robust telemetry
- Add substitutions, tactical assignments and useful player statistics.
- Add buffers, sequence tracking, health diagnostics and dropped-frame counters.
- Test half-time, match end, substitution, pause/speed changes and consecutive matches.
- Validate pointer and pitch-dimension handling.

### Milestone 5 — Python ingestion and state
- Implement Pydantic telemetry models.
- Add ingestion endpoint and validation.
- Maintain current match state and rolling windows.
- Add SQLite persistence for match summaries and observations.
- Add replay from captured test fixtures.

### Milestone 6 — Deterministic tactical analysis
- Start with a small number of measurable tactical observations.
- Unit-test rules with synthetic and recorded match data.
- Add evidence and confidence calculations.
- Avoid LLM use until the observations are stable.

### Milestone 7 — Ollama integration
- Confirm GPU/VRAM, CPU and free disk.
- Select a suitable local model and quantisation.
- Use Ollama on Windows host.
- Test structured outputs, latency, memory use and failure handling.
- The LLM explains and prioritises observations; it does not replace data validation.

### Milestone 8 — Dashboard and match-day workflow
- Angular dashboard.
- Live feed and recommendation panel.
- Evidence and trend views.
- Manual acknowledgement of implemented recommendations.
- Post-change evaluation.

## 12. Development team / agent concept

The earlier proposed multi-agent development team has these roles:

| Agent | Responsibility |
|---|---|
| José / Project Lead | Coordinate work, architecture decisions and reviews |
| Engineer | Backend, plugin integration and application implementation |
| Tactical Analyst | FM27 tactical instructions and football principles |
| Data Scientist | Telemetry interpretation, metrics and detection |
| QA Engineer | Tests, edge cases and recommendation quality |

Start with two development agents and expand only after isolation and workflows are verified. Agents should work on separate branches or bounded worktrees and must not independently modify the live game installation.

The tactical analyst must ground recommendations in actual FM27 options, not generic football terminology alone.

## 13. Security and reliability rules

- Keep the telemetry plugin local and purpose-limited.
- Bind local HTTP services to `127.0.0.1`.
- No public port forwarding.
- No Docker socket mounts for agents.
- No unrestricted host filesystem access.
- Do not provide agents with credentials, save folders or SSH keys.
- Use a bounded queue and explicit backpressure/drop behaviour.
- Keep the game hook free of blocking network, database and LLM work.
- Validate all input at the Python boundary.
- Keep test fixtures separate from live game state.
- Log enough to diagnose failures, but avoid logging secrets or excessive personal paths.
- Add compatibility checks before reading version-specific offsets.
- Fail closed: if the game build is unknown, disable memory capture rather than guess offsets.
- Provide a safe unload/disable mechanism.

## 14. Learning and collaboration style

The user wants to learn through a Socratic approach. Cursor and ChatGPT should act as tutors and collaborators, not simply generate large blocks of code.

Recommended working pattern:
1. Explain the problem and why the component exists.
2. Ask one focused question to test the user's understanding where useful.
3. Let the user predict what a code block or method does.
4. Explain unfamiliar C# concepts in context.
5. Make small changes with clear purpose.
6. Run one test or diagnostic at a time.
7. Review output before moving to the next step.
8. Keep a short decision log and update this document when architecture changes.

The user last studied C# around 2010 and considers their knowledge rusty. Assume familiarity with general programming concepts, but refresh modern C#/.NET syntax and BepInEx/IL2CPP concepts patiently. Avoid overwhelming the user with an entire codebase at once.

## 15. Open questions and decisions still required

1. What are the user's exact GPU model and dedicated VRAM?
2. Which Ollama model and quantisation fit the hardware?
3. Which FMMatchLens source components can legally and technically be reused in José's separate plugin?
4. Which offsets are verified for the current FM27 build?
5. What is the minimum useful capture frequency for tactical analysis?
6. Which telemetry fields are reliable and available throughout a match?
7. What causes the pitch-dimension read to fail in the observed match?
8. Should the initial plugin publish via HTTP POST, WebSocket, named pipe or another local transport?
9. What exact FM27 instruction catalogue and validation workflow will be used?
10. What should be retained in SQLite versus short-lived in-memory windows?

## 16. Cursor handover instructions

When this document is added to the repository, give Cursor the following instruction:

> Read `docs/Jose-Guardiniho-Technical-Architecture-Handover.md` before proposing implementation changes. Treat it as the current planning baseline, not as proof that unimplemented components already exist. Preserve the separation between the C# telemetry plugin, Python backend, Ollama and dashboard. Do not modify the installed FMMatchLens plugin or FM27 game files. Work in small, reviewable steps and explain modern C# concepts as we go. Use a Socratic teaching style: explain, ask focused questions, and let the user reason through important code before providing the solution. Do not invent undocumented FM27 offsets, endpoints or tactical instructions. Mark assumptions explicitly and ask before changing architectural decisions.

### Previous starter-package task (superseded)

The earlier instruction to inspect the starter package as the first Cursor task is superseded by Sections 17–19. The immediate priority is the FMMatchLens pitch-dimension source investigation. The starter ZIP remains a reference only; repository creation will be planned with the user after the telemetry spike.

---



## 17. Development approach update — build the project with the user, not for the user

**Decision (10 November 2026):** The existing José starter ZIP is a temporary reference/scaffold, not a fixed codebase or an obligation to preserve its current structure. The user wants to write the code themselves, with light-to-moderate guidance. The project should therefore be rebuilt deliberately in a new Git repository when the initial technical spike has clarified the telemetry boundary.

### Learning and implementation rules
- Do not generate the full application or plugin in one pass.
- Work in small, reviewable increments, with one clear learning objective per step.
- Explain the purpose of a file, class, function or dependency before asking the user to implement it.
- Prefer the user writing the first attempt; provide hints and targeted corrections before showing a complete solution.
- Use moderate guidance: do not make the user guess obscure C#, .NET, BepInEx or reverse-engineering details without support.
- Add dependencies only when a concrete requirement justifies them.
- Add tests alongside each meaningful behaviour, and run them before moving on.
- Keep the Markdown handover current after every substantive planning or implementation session.

### Proposed repository creation sequence
1. Complete a focused telemetry feasibility/diagnostic spike (see Section 18).
2. Agree the first thin vertical slice and its data contract.
3. Create a fresh Git repository and a minimal, understandable folder structure.
4. Write the README, project goals, architecture overview and initial decision records before adding application code.
5. Build the first component with the user, test it, then proceed to the next component.
6. Keep generated or AI-authored code to a minimum; Cursor should act as a tutor, reviewer and pair programmer.

The existing starter package may be mined for useful ideas or small pieces, but it should not dictate the final design. Do not create a second repository or migrate files until the user is ready to do that step.

## 18. Immediate next move — validate completed-match frame data

**Current status:** The earlier v0.7.1 archive pitch-dimension failure remains a historical issue, but it is no longer the immediate blocker for proving telemetry access. FMMatchLens v0.7.3 has reported installing its AOB fallback hook, identified a live match, and successfully returned five frames from a completed match through its HTTP API.

### Confirmed completed-match API retrieval (15 November 2026)
For match `match-1794699680854`, the user queried:

- `GET /api/match/frames?fromTick=1&stride=1&limit=5`
- `GET /api/match/frames?fromTick=23773&stride=1&limit=5`

Both requests returned five frame objects. Both responses reported `status="ended"` and `totalFrameCount=23777`.

Observed first-range ticks and sequences:

| Tick | Sequence |
|---:|---:|
| 1 | 1444 |
| 2 | 1445 |
| 3 | 1446 |
| 4 | 1448 |
| 5 | 1451 |

Observed final-range ticks and sequences:

| Tick | Sequence |
|---:|---:|
| 23773 | 64321 |
| 23774 | 64322 |
| 23775 | 64323 |
| 23776 | 64324 |
| 23777 | 64325 |

**Interpretation:** the API can retrieve both the beginning and end of the same completed match timeline. The earlier empty result was caused by querying `fromTick=23778`, immediately beyond `totalFrameCount=23777`; it was not evidence of a failed capture. The first sample's sequence values contain gaps, while the final sample's sequence values are consecutive. Do not infer missing game ticks from sequence gaps: tick values 1–5 were all returned. `sequence` and `tick` remain distinct counters.

This establishes endpoint accessibility and boundary retrieval, but does not yet validate every intermediate frame, every field's semantics, archive finalisation, or the dashboard's match-state UI. The dashboard still displays “Live Match” although the API reports `status="ended"`; treat this as a separate unresolved UI/state issue.

### Next diagnostic steps
1. Expand and copy one complete frame object (tick 1 is acceptable) so the available fields, nested player records, ball coordinates and team statistics can be inspected. The current table summaries do not expose the full frame schema.
2. Check whether a `.fmlens` file was created for this match and whether the dashboard can open/replay it through its archive workflow. Treat archive writing as separate from the API frame endpoint.
3. Investigate why the dashboard still labels the ended match “Live Match” even though the API response says `status="ended"`. Do not assume this UI label means the frame endpoint is still in a live state.
4. Once the frame schema is understood, prototype a read-only Python client against the existing loopback API. Do not add native hooks, patch FMMatchLens or let José modify FM27.

### Explicit non-goals
- Do not create another GAME_MATCH native hook now.
- Do not patch the installed FMMatchLens plugin or FM27 game files.
- Do not hardcode pitch dimensions or bypass archive validation.
- Do not assume the `.fmlens` archive is valid merely because the HTTP endpoint returns frames.
- Do not infer match minutes directly from `tick` without calibration.

## 19. Revised Cursor handover and first task

Cursor must respect the user's preference to learn by writing the code with light-to-moderate guidance. It should not simply generate a complete solution.

> Read this handover first. The current FMMatchLens v0.7.3 test has produced strong evidence that its local API can retrieve completed-match frame data. Do not create or reverse-engineer another native hook at this stage. The immediate task is read-only API/schema validation: inspect the final five ticks of match `match-1794699680854`, inspect a complete frame object, and document the response schema and field semantics. Separately determine whether a `.fmlens` archive exists and whether the dashboard can open it; the dashboard's “Live Match” label despite API `status="ended"` is a separate unresolved UI issue. Then propose a small Python HTTP client for the user to implement with guided steps and tests. Do not modify FMMatchLens or FM27. José must remain advisory-only: no automated tactical changes.
---

## Appendix A — Useful local endpoints and paths

| Service / resource | Value |
|---|---|
| FMMatchLens local API | `http://127.0.0.1:16726/` |
| FMMatchLens health endpoint observed in prior investigation | `http://127.0.0.1:16726/api/health` |
| Ollama API | `http://127.0.0.1:11434` |
| Proposed José backend | `http://127.0.0.1:8000` |
| FMMatchLens config | `E:\SteamLibrary\steamapps\common\Football Manager 27\BepInEx\config\com.fmmatchlens.plugin.cfg` |
| FMMatchLens archive folder | `<FM27 game root>\BepInEx\plugins\FMMatchLens\data\matches\` |
| José project suggested location | `C:\Projects\jose-guardiniho` |

The exact FMMatchLens endpoint routes should be verified against the installed plugin/API before use. The José backend port is a proposal.

## Appendix B — FMMatchLens references

- Repository: https://github.com/osnsyc/FMMatchLens
- Releases: https://github.com/osnsyc/FMMatchLens/releases
- v0.7.1 source tag: `v0.7.1` / commit `f0582d3`
- Installed plugin build: `steam-26340721`
- BepInEx IL2CPP documentation: https://docs.bepinex.dev/
- Ollama Windows: https://ollama.com/download/windows
- Docker Desktop: https://www.docker.com/products/docker-desktop/

FMMatchLens is a third-party project. Preserve its MIT licence and copyright notices if any of its source code is copied or adapted. Confirm the exact licence file and applicable notices in the repository before distributing a derivative build.

---

**Document status:** Living planning and handover document. Updated 15 November 2026 with FMMatchLens v0.7.3 AOB-hook diagnostics and confirmed first-and-last frame retrieval from a completed match. This is not a release specification; continue distinguishing verified results, proposals and hypotheses.

## 20. Video reference: using data to improve FM27 performance

The user shared this video as inspiration for a possible José feature:

- **Title:** [How to Use Data to Improve Performance in FM27](https://youtu.be/4xLzv77mq6k)
- **Status:** Reference identified by title, but the video's actual content and workflow have not yet been reviewed or verified.
- **Potential relevance:** It may inform how José turns match data into useful performance analysis and actionable tactical advice, rather than merely collecting and displaying telemetry.
- **Planning rule:** Do not treat the video's title as a feature specification. Review the actual video content (or a transcript / user-provided notes) with the user, identify the specific workflow or feature worth learning from, and then decide whether it belongs in José's product requirements. Preserve José's core principle that it advises the human manager and never changes FM27 instructions autonomously.

---

**Document status:** Living planning and handover document. Updated 15 November 2026 with FMMatchLens v0.7.3 AOB-hook diagnostics, confirmed completed-match API boundary retrieval, and revised validation tasks. The FM27 data-analysis video reference remains awaiting review. This is not a release specification; continue distinguishing verified results, proposals and hypotheses.

## 21. First detailed completed-match frame summary inspected (15 November 2026)

The user supplied a structured field summary of frame `tick=23774`, `sequence=64322` from completed match `match-1794699680854`. This is a summary/table rendering, not the complete raw JSON: each of the 40 `players` entries is abbreviated with an ellipsis, so nested player-field schema remains uninspected.

### Fields observed in the frame summary

- Frame identity/timing: `sequence`, `matchId`, `tick`, `displayTick`, `period`, `capturedUnixMilliseconds`.
- Match state: `possessionTeam`, `ballHolderPlayerId`, `ballXCentimeters`, `ballYCentimeters`, `ballZCentimeters`, `halfPitchWidth`, `halfPitchLength`.
- Momentum: `momentumEvents`, `momentum`, `rollingMomentum`, `momentumEventUpdates` (all shown as empty arrays in this frame).
- Team statistics for both `home` and `away`: goals, xG, possessionTime, shots, shotsOnTarget, shotsOffTarget, blockedShots, clearCutChances, passes, passesCompleted, crosses, crossesCompleted, aerials, aerialsWon, progressivePasses, finalThirdPasses, tacklesAttempted, tacklesWon, fouls, corners, offsides, yellowCards, redCards, firstHalfShots, secondHalfShots.
- Players: 40 entries, slots 0–22 assigned to home and slots 23–39 assigned to away in this frame. Each visible abbreviated entry includes at least `slot`, `playerId`, and `team`.
- Rating/tactical-related fields: `ratingModel`, `ratingBaseCondition`, `matchPhase`, `eventRewardBranch`, `activeBaseline`, `homeBackgroundInput`, `awayBackgroundInput`, `tactics`, `tacticsUnchangedFrom`.

### Exact sample values worth preserving

- `tick=23774`, `displayTick=23285`, `period=3`, `capturedUnixMilliseconds=1794701871968`.
- `possessionTeam="away"`; `ballHolderPlayerId=2000243827`, which matches the visible away player at slot 39.
- Ball coordinates: X `-2161` cm, Y `-2068` cm, Z `0` cm.
- `halfPitchWidth=34.3125`, `halfPitchLength=50.325` (units/coordinate interpretation still to be confirmed independently).
- Home: 3 goals, xG `1.6024594`, 8 shots, 3 on target, 534 passes, 462 completed.
- Away: 4 goals, xG `2.1646621`, 15 shots, 8 on target, 407 passes, 340 completed.
- `ratingBaseCondition=16777216`, `matchPhase=5`, `eventRewardBranch=0`, `activeBaseline=6700`.
- `tactics=null`; `tacticsUnchangedFrom=69`.

### Interpretation boundaries

This confirms that the frame summary exposes match-level statistics, ball coordinates/holder, player identifiers, and additional rating/phase/tactics-related fields. It does **not** yet establish the semantics or units of every field. In particular:

- Do not infer the meaning of `period=3` or `matchPhase=5` without cross-checking other frames and the in-game display.
- Do not assume `possessionTime` units, pitch-coordinate orientation, or the units of `halfPitchWidth` / `halfPitchLength` solely from their names.
- Treat team statistics as candidate cumulative match totals until successive frames and the FM match UI confirm their behaviour.
- `tactics=null` means no tactics object is present in this sample; it does not prove tactics are never exposed.
- `tacticsUnchangedFrom=69` is an observed value only; its semantics are unknown.
- The 40 player records include 23 home and 17 away entries. Do not assume all are on-pitch players until the complete player objects are inspected and active/on-pitch flags or positions are identified.
- The visible ball-holder ID matches one of the away player IDs in the same frame, demonstrating a useful join key in this sample, not yet a universal guarantee.

### Updated next step

Ask the user to expand and copy the complete raw JSON for one player object from `players` (preferably slot 39, the current ball holder) and, if practical, one home player object. This will reveal nested identity, position, on-pitch/substitute, coordinates, condition, rating and other available fields without guessing. The complete raw frame is still useful if readily accessible, but the immediate priority is the unabridged player object. After that, compare a second frame (ideally a nearby tick) to determine which fields change and which appear cumulative or static. Keep archive-file validation and the dashboard's stale “Live Match” label as separate tasks.

---

**Document status:** Updated 15 November 2026 with the first detailed completed-match frame field summary. The nested player-object schema and field semantics remain unvalidated.

## 22. Complete player-object summaries inspected (15 November 2026)

The user supplied two detailed player-object field summaries from frame `tick=23774`, `sequence=64322`, match `match-1794699680854`: away slot 39 (the current ball holder) and home slot 22 (a West Brom player). These are field summaries of the objects, not raw JSON text, but unlike the earlier frame table they expose the complete visible field set for each selected player.

### Player fields observed

- Identity/team: `slot`, `playerId`, `team`.
- Ball state and movement: `isBallHolder`, `x`, `y`, `speedCentimetersPerSecond`, `angleDegrees`.
- Match participation: `isSubstitute`, `isOnPitch`, `subbedOnMinute`, `subbedOffMinute`.
- Rating/physical: `rating`, `rawInternalRating`, `overallPhysicalCondition`, `matchSharpness`, `distanceM`.
- Player match statistics: penalties, own goals, goals, assists, xG, xA, shots, shots on target, blocked shots, clear-cut chances, woodwork, dribbles, fouls, fouled, crosses/completed, passes/completed, progressive passes, key passes, tackles attempted/won, key tackles, aerials/won, interceptions, throw-ins, corners, defensive/attacking free kicks, clearances, shots faced, and save categories.
- Opaque/internal fields: `ratingInputs`, `statsPacked`, `internalW25`, `internalW24`, `specialW2C` through `specialW31`, `inPossessionRoleDuty`, `outOfPossessionRoleDuty`, `specialConditionA`, `specialConditionB`, `totalEligibleDuration`, `ratingEventsCommonLength`, `ratingEventsTail`, `momentumEventUpdates`, `ratingModel`, `ratingBaseCondition`, `matchPhase`, `eventRewardBranch`, `activeBaseline`, `homeBackgroundInput`, `awayBackgroundInput`, `tactics`, `tacticsUnchangedFrom`.

### Away player: slot 39, ID 2000243827

- `team="away"`, `isBallHolder=true`, `isSubstitute=true`, `isOnPitch=true`.
- Position fields: `x=-38.311916`, `y=-0.18658848`; speed `203` cm/s; angle `180` degrees.
- Substitution: came on at minute 51; `subbedOffMinute=0`.
- Rating `7.45`, raw internal rating `7445`; physical condition `82`, sharpness `72`, distance `5287.1616` m.
- Contributions: 1 assist, xG `0.0380103`, xA `0.42837316`, 1 shot (on target), 1 dribble, 27 passes (22 completed), 6 progressive passes, 2 key passes, 2 tackles attempted (0 won), 1 interception.
- Opaque values include `statsPacked="ulPbPgAAAAACAAACAAMCAgAAAAAAAAADAAAXAAQAEwADAAEB"`, in-possession role/duty `"562949957615616"`, out-of-possession role/duty `"274882101248"`, `totalEligibleDuration=11094`, `ratingEventsCommonLength=0`, empty `ratingEventsTail` and `momentumEventUpdates`, and `tactics=null`.

### Home player: slot 22, ID 2000566343 (West Brom)

- `team="home"`, `isBallHolder=false`, `isSubstitute=true`, `isOnPitch=true`.
- Position fields: `x=-38.252754`, `y=0.12285055`; speed `376` cm/s; angle `208` degrees.
- Substitution: came on at minute 80; `subbedOffMinute=0`.
- Rating `7.25`, raw internal rating `7253`; physical condition `97`, sharpness `71`, distance `1989.1887` m.
- Contributions: 1 goal, xG `0.14543009`, 1 shot (on target), 2 fouls, 1 cross (not completed), 10 passes (all completed).
- Opaque values include `statsPacked="AAAAAAAAAAAAAAAAAAEBAQABAAAAAgABAAAIAAAACAAAAAEB"`, in-possession role/duty `"8912896"`, out-of-possession role/duty `"4398050705408"`, `totalEligibleDuration=4240`, `ratingEventsCommonLength=1`, empty `ratingEventsTail`, and `tactics=null`.

### Confirmed observations and interpretation limits

- Both objects expose the same broad schema and distinguish `isSubstitute` from `isOnPitch`. Both examples are substitutes who are currently on the pitch; their substitution-on minutes differ (51 and 80).
- The frame-level `ballHolderPlayerId=2000243827` matches slot 39's `playerId`, and that player's `isBallHolder=true`. This is a strong within-frame consistency check for the ball-holder join key.
- `speedCentimetersPerSecond` is explicitly named in centimetres per second. The sample values correspond to 2.03 m/s and 3.76 m/s respectively.
- `rawInternalRating` is numerically close to `rating * 1000` in these two examples (7445 vs 7450; 7253 vs 7250), but do not implement a conversion or assume exact equality until more samples are checked.
- Player positions `x` and `y` are decimal values, while ball coordinates in the frame object are centimetres. Do not assume the player coordinates use the same units or axis orientation until compared with pitch dimensions and known in-game positions.
- `distanceM` is labelled in metres, but its accumulation/reset scope still needs validation.
- `overallPhysicalCondition` and `matchSharpness` are observed as values 82/72 and 97/71. Do not assume a percentage scale or equate either to a particular FM UI condition indicator without validation.
- Player stats appear suitable candidates for per-player match analysis, but their accumulation scope and update cadence should be tested across successive frames.
- `inPossessionRoleDuty` and `outOfPossessionRoleDuty` are numeric strings and likely encoded values; `statsPacked` is a packed string. Treat all as opaque until their encoding is documented or reverse-engineered safely from source. Do not feed raw opaque values to José's tactical reasoning as if they were human-readable roles.
- `totalEligibleDuration`, `ratingEventsCommonLength`, `ratingEventsTail`, `ratingInputs`, `specialCondition*`, `internalW*`, and `specialW*` remain unexplained. `ratingEventsCommonLength` differs between the two samples (0 vs 1), while both `ratingEventsTail` arrays are empty; investigate only if rating analysis requires it.
- `tactics=null` appears in both selected player objects and the parent frame summary. This does not establish that tactics are never available.

### Updated next steps

1. Compare one of these players across two nearby ticks to identify which fields are instantaneous (position/speed/ball state) and which are cumulative or slowly changing (distance, statistics, condition, rating).
2. Confirm player coordinate units and orientation against pitch dimensions and a known in-game position; do not assume `x` is longitudinal or lateral yet.
3. Check whether player names and stable metadata are available through the separate match/player metadata endpoint, since these player objects contain IDs but no visible names.
4. Validate rating scale, condition/sharpness scale, distance accumulation and substitution-state semantics against FM27's match UI.
5. Keep role/duty numeric strings and packed/internal fields opaque until a reliable mapping is found.
6. Once these checks are adequate, define a typed, read-only Python model for the known fields and preserve unknown fields without interpreting them.

---

**Document status:** Updated 15 November 2026 with two detailed player-object field summaries from the completed match. Player-level schema availability is now substantially established; units, field semantics, identity/name joining, coordinate orientation and cumulative-stat behaviour still require validation.

## 23. Consecutive-frame comparison: tick 23773 vs 23774 (15 November 2026)

The user supplied the completed-match frame summary for `tick=23773`, `sequence=64321`, immediately preceding the already inspected `tick=23774`, `sequence=64322`, for match `match-1794699680854`.

### Frame-level observations at tick 23773

- `tick=23773`, `sequence=64321`, `displayTick=23285`, `period=3`.
- `capturedUnixMilliseconds=1794701871968`.
- Possession remains `away`; `ballHolderPlayerId=2000243827`.
- Ball coordinates: `(-2161, -2068, 0)` centimetres.
- The same team score and match-stat summary as the tick-23774 summary was supplied: home 3 goals / xG 1.6024594; away 4 goals / xG 2.1646621, with the same visible team-stat values.
- `momentumEvents`, `momentum`, and `rollingMomentum` are empty; the frame lists 40 player entries.

### First adjacent-tick comparison: away player 2000243827, slot 39

The full visible player record supplied for slot 39 at tick 23773 matches the previously supplied tick-23774 record field-for-field for all displayed values. Examples include:

- `isBallHolder=true`, position `x=-38.311916`, `y=-0.18658848`, speed `203` cm/s, angle `180` degrees.
- Rating `7.45`; condition `82`; sharpness `72`; distance `5287.1616` m.
- Substitution state: `isSubstitute=true`, `isOnPitch=true`, `subbedOnMinute=51`, `subbedOffMinute=0`.
- Match contributions: 1 assist, xG `0.0380103`, xA `0.42837316`, 1 shot/on target, 27 passes / 22 completed, 6 progressive passes, 2 key passes, 2 tackles attempted, 1 interception.
- `ratingInputs` summary begins with the same `statsPacked` value `ulPbPgAAAAACAAACAAMCAgAAAAAAAAADAAAXAAQAEwADAAEB` and the visible `internalW25=0`, `internalW24=0` values.

The frame-level `capturedUnixMilliseconds` is also identical at ticks 23773 and 23774 (`1794701871968`). Thus, the tick counter advanced by one while the supplied timestamp and selected player's visible record did not change.

### What this does and does not establish

- It establishes that the selected player's visible values can be identical across adjacent tick numbers in this capture. It does **not** establish whether this is normal sampling behaviour, timestamp resolution behaviour, duplicate-frame emission, or a consequence of the game's update cadence.
- Since this player's record is unchanged, this comparison cannot yet distinguish cumulative from instantaneous player fields or establish their update cadence.
- The unchanged team-stat summaries and ball-holder/ball-position values in the supplied summaries are further evidence that these adjacent frame records may contain repeated state, but the user supplied table summaries rather than raw JSON, so avoid asserting byte-for-byte identical frames.
- Do not deduplicate frames or treat identical timestamps as duplicate records without more evidence. Preserve `tick` and `sequence` independently; the sequence increased from 64321 to 64322 while tick increased from 23773 to 23774.

### Immediate next experiment

Retrieve the complete player object for home slot 22, player ID `2000566343`, from tick 23773. Compare it with the already captured tick-23774 object. This second player comparison will show whether the unchanged slot-39 record is isolated or shared by another player, and may expose changes in fields such as position, speed, distance, rating or match statistics. Continue to use exact tick labels when copying data; do not infer the tick from sequence alone.

---

**Document status:** Updated 15 November 2026. First adjacent-tick player comparison completed; the away player's visible record and frame timestamp are unchanged between ticks 23773 and 23774. A second player comparison is pending. No field update cadence or cumulative-stat semantics have yet been established.

## 24. Second adjacent-tick player comparison: home slot 22 (15 November 2026)

The user supplied the player object for home slot 22, player ID `2000566343`, in response to the request for this player at tick 23773. The player-object message itself did not repeat the frame-level `tick` or `sequence`; the comparison below treats it as the requested tick-23773 sample, but the tick association should be confirmed if exact provenance is needed.

Compared with the previously supplied tick-23774 object for the same player, every displayed field is unchanged:

- Position `x=-38.252754`, `y=0.12285055`; speed `376` cm/s; angle `208` degrees; `isBallHolder=false`.
- Rating `7.25`; physical condition `97`; sharpness `71`; distance `1989.1887` m.
- Substitution state `isSubstitute=true`, `isOnPitch=true`, `subbedOnMinute=80`, `subbedOffMinute=0`.
- All displayed match statistics are unchanged: 1 goal, xG `0.14543009`, 1 shot/on target, 2 fouls, 1 cross, 10 passes / 10 completed, and the remaining displayed event counts zero.
- The abbreviated `ratingInputs` summary begins with the same `statsPacked` value `AAAAAAAAAAAAAAAAAAEBAQABAAAAAgABAAAIAAAACAAAAAEB` and visible `internalW25=0`, `internalW24=0` values.

### Combined interpretation of the two player comparisons

- Both selected players (away slot 39 and home slot 22) have identical displayed player-object values in the tick-23773 and tick-23774 samples.
- The frame-level timestamp is also identical across the two frame summaries: `capturedUnixMilliseconds=1794701871968`.
- The frame `sequence` and `tick` nevertheless each increment by one (64321/23773 to 64322/23774).
- This makes a repeated-state or sampling/update-cadence explanation more plausible than an isolated player-specific lack of movement, but it does not prove the underlying game state was unchanged. We have not compared raw serialized frames or inspected the producer's timestamp/update logic.
- Do not conclude that player positions, speeds, distance, ratings or match statistics are inherently static, nor that the frames are duplicates. The current evidence only says the two sampled player objects and displayed frame timestamp did not change across these adjacent tick labels.

### Revised next experiment

Retrieve one or more frames further apart (for example ticks 23770 and 23775, or another pair with a known interval) and compare the same players, including position, speed, distance, rating, statistics, ball state and timestamps. Prefer raw JSON or an unabridged export where possible. This should help distinguish a timestamp-resolution issue, repeated-frame emission, and ordinary game-state sampling cadence. Keep every frame's `tick` and `sequence` as separate fields and do not deduplicate on timestamp alone.

---

**Document status:** Updated 15 November 2026. Two player records have now been compared across the adjacent tick labels 23773 and 23774 (with the home player's tick association inferred from the requested retrieval, because its player-only message omitted the frame header). Both records are unchanged in all displayed fields, and the frame timestamps match. Update cadence, duplicate-frame behaviour and cumulative-stat semantics remain unverified.

## 25. Second completed match identified; match separation confirmed (15 November 2026)

While investigating the first completed match (`match-1794699680854`), the user started/ran another match. A subsequent FMMatchLens match-status/metadata response identified a different completed match:

- `matchId="match-1794705819664"`
- `status="ended"`
- `totalFrameCount=23653`
- `frames=[]` in the supplied response.

### Interpretation and handling

- This is a distinct match from `match-1794699680854`; match IDs must be the primary partition key for all frame ingestion, storage, comparisons and analysis. Never merge telemetry solely because it came from the same FMMatchLens session or endpoint.
- `status="ended"` and `totalFrameCount=23653` indicate that FMMatchLens reports a completed match with 23,653 frames.
- The empty `frames` array in this response is not evidence that no frames were recorded. It appears to be a metadata/status response; actual frame retrieval must be tested separately using the frame endpoint and the new match's context.
- Do not assume that the earlier match remains accessible through the live endpoint after the second match. Its continued availability needs an explicit retrieval test or archive lookup.

### Next retrieval test

For the new match, request its final frame using the documented frame endpoint with `fromTick=23653`, `stride=1`, and `limit=1` (subject to confirming that the endpoint is scoped to the new match and not silently returning another active/archive context). Record the returned `matchId`, `tick`, `sequence`, timestamp, player count and ball state. If the endpoint returns a frame, verify that its `matchId` is exactly `match-1794705819664`. Then test an earlier tick from this same match. Keep the earlier match's observations intact and separately labelled.

---

**Document status:** Updated 15 November 2026. A second completed match has been identified with 23,653 reported frames. Its actual frame retrieval and the continued accessibility of the first match have not yet been tested.

## 26. Second match archive binary inspection (15 November 2026)

Current status: The raw .fmlens binary archive for the second match (match-1794705819664) was successfully inspected, confirming that FMMatchLens v0.7.3 is successfully writing and finalising local archive files.

Verified binary structure and contents

Headers and Blocks: The file begins with the FMLENS2 version header, contains compressed frame chunks marked as BLK2, and includes an index footer marked as BÍLIB.

Match Context: The embedded string data confirms the match is Leicester vs. Man City, with an in-game date of 2026-08-29.

Rich Metadata Dictionary: The archive embeds a comprehensive string table containing static player data. This includes:

Player names (e.g., Vivianne Miedema, Lauren Hemp, Alex Greenwood, Bunny Shaw, Yui Hasegawa).

Dates of birth and preferred foot (e.g., Right Foot, Left Foot).

Positional familiarity labels (e.g., GK, DL, DC, DR, WBL, DM, MC, AML, AMC, AMR, ST).

The complete suite of Football Manager player attributes (e.g., Acceleration, Pace, Agility, Anticipation, Composure, Decisions, Positioning, Vision, Passing, Tackling).

Architectural implications for José Guardiniho

Validation of the Metadata Split: This string table explains why the live JSON frame objects inspected in Section 22 omitted player names and attributes. FMMatchLens explicitly separates static, heavy metadata (written once to the header/API) from the high-frequency dynamic frames (which only store playerId, coordinates, and changing stats to save space).

Backend Ingestion Rule: The José Python backend must mirror this architecture. It should fetch the match and player metadata exactly once via the API at the start of the match (or upon a substitution event) and cache it in memory. High-frequency live frames should then be joined to this cached metadata using playerId as the stable primary key before being passed to the analysis layer.

Archive Health: The successful creation of this FMLENS2 binary demonstrates that the Pitch dimensions are invalid error observed in v0.7.1 is not currently blocking v0.7.3 from writing archives for completed matches.

**Document status:** Updated 15 November 2026. A second completed match has been identified with 23,653 reported frames. Its actual frame retrieval and the continued accessibility of the first match have not yet been tested.

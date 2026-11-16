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
| Match telemetry reference | FMMatchLens v0.7.1 |
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

## 4. Telemetry strategy: move beyond depending on FMMatchLens

### 4.1 Decision

The current preferred direction is to build a **José-owned telemetry plugin**, using FMMatchLens v0.7.1 as a technical reference and selectively adapting/reusing code where the licence and technical review permit.

José should not depend on FMMatchLens as a complete product, archive format, dashboard or runtime API.

This is a strategic direction, not yet an implemented or tested replacement.

### 4.2 Why this direction

FMMatchLens has demonstrated that it can:
- Load as a BepInEx 6 IL2CPP plugin in the user's FM27 Steam installation.
- Detect the relevant `game_plugin.dll` build.
- Install a native match-update hook.
- Identify a live match simulation and capture player/frame information.
- Expose local telemetry through its own API and dashboard.

A purpose-built José collector could avoid depending on:
- The `.fmlens` archive writer and its finalisation lifecycle.
- FMMatchLens's dashboard and API schema.
- Data fields and processing José does not need.
- Upstream changes to archive format or dashboard behaviour.

The new collector will still depend on FM27's internal structures and offsets. It will therefore require maintenance when the game updates.

### 4.3 What not to do

Do not immediately copy the entire FMMatchLens plugin. First understand the extraction path and dependencies. Keep the new implementation small, with game-version-specific code isolated behind a compatibility layer.

Do not assume that all offsets in the source are validated. The source itself contains comments identifying unconfirmed or candidate fields. Every field used by José must be validated against live game output.

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

## 18. Immediate next move — diagnose the FMMatchLens pitch-dimension failure

**Current blocker:** The user's live FMMatchLens v0.7.1 test installed its hook and identified the expected FM27 build, but archive finalisation failed with `Pitch dimensions are invalid.` The log also reported `pitchBackfilled=0` and `pitchSourceTick=-1`. The resulting archive was incomplete and the dashboard could not find complete match frames.

This is the next technical investigation because it tests whether the relevant native data can be read reliably and helps define the minimum viable telemetry contract. It does not mean José should adopt FMMatchLens's archive writer or depend on its dashboard/API.

### Known evidence
- FMMatchLens v0.7.1 loaded in FM27 and successfully installed the match-update hook for build `steam-26340721`.
- The plugin detected the user's `game_plugin.dll` SHA-256 and matched the known build catalogue entry.
- The match simulation was detected and pre-lock frames were committed.
- The writer then rejected the archive because pitch dimensions were invalid.
- The diagnostic log showed no valid pitch dimensions available for backfilling.
- The exact cause is **not yet known**: possible causes include an invalid/null source pointer, unreadable or stale memory, an unexpected value, a capture-timing issue, or an offset/source-resolution issue. These are hypotheses, not findings.

### Diagnostic sequence
1. Inspect `Memory/NativeMomentumSource.cs` and identify the exact pointer chain, offsets, read checks and validation rules used for half-pitch width and length.
2. Trace where `NativeMomentumSource` is called from `Memory/GameMatchTickHook.cs` and how its results are placed into `Domain/RealtimeTickFrame.cs` or the archive writer input.
3. Check the relevant definitions and comments in `Memory/Offsets.cs`; distinguish confirmed offsets from candidate/unconfirmed ones.
4. Identify what diagnostic values can safely be logged (pointer validity, read success, raw dimensions, tick and capture phase) without destabilising the game.
5. If a new controlled match test is needed, change only one variable at a time and capture the fresh BepInEx log. Do not patch the installed plugin or invent pitch dimensions to make the archive pass.
6. Record whether the failure is specific to the momentum/pitch metadata path or indicates a wider problem with frame capture.

### First hands-on task for the user
Open the existing source clone at:
`F:\MY PROJECTS REPOSITORIES\FMMatchLens-source`

Start by locating and reading these three files in this order:
- `Memory/NativeMomentumSource.cs`
- `Memory/GameMatchTickHook.cs`
- `Memory/Offsets.cs`

The first learning step should be to understand the data flow, not to edit code. The user can paste the relevant method(s) or file contents in manageable sections. We will walk through the pointer chain and validation logic together before deciding whether another game test or a small diagnostic change is justified.

### Explicit non-goals for this step
- Do not copy the whole FMMatchLens plugin.
- Do not edit the installed FMMatchLens plugin or FM27 game files.
- Do not hardcode pitch dimensions or bypass validation.
- Do not implement the LLM, dashboard, agent team or full Python backend yet.
- Do not treat the failed archive as evidence that all telemetry capture is broken.

## 19. Revised Cursor handover and first task

Cursor must respect the user's preference to learn by writing the code with light-to-moderate guidance. It should not simply generate a complete solution.

> Read this handover first. The existing starter ZIP is a disposable prototype/reference, not a mandatory base. The user wants to create the José repository deliberately and write the code themselves with light-to-moderate guidance. Teach in small steps: explain the purpose, ask one focused question where useful, let the user attempt the code, review it, and add tests. Do not produce large unrequested code dumps.
>
> The immediate task is source investigation only: trace why FMMatchLens v0.7.1 reports `Pitch dimensions are invalid`, starting with `NativeMomentumSource.cs`, then `GameMatchTickHook.cs`, then `Offsets.cs`. Do not modify the installed plugin or game files. Separate verified facts from hypotheses. Do not invent offsets, memory layouts, endpoint routes or tactical instructions. Once the failure path is understood, propose the smallest safe next diagnostic or test and wait for the user's agreement before implementation.

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

**Document status:** Living planning and handover document. Updated 10 November 2026 with the guided-from-scratch development decision and the next telemetry diagnostic task. This is not a release specification; continue distinguishing verified results, proposals and hypotheses.

## 20. Video reference: using data to improve FM27 performance

The user shared this video as inspiration for a possible José feature:

- **Title:** [How to Use Data to Improve Performance in FM27](https://youtu.be/4xLzv77mq6k)
- **Status:** Reference identified by title, but the video's actual content and workflow have not yet been reviewed or verified.
- **Potential relevance:** It may inform how José turns match data into useful performance analysis and actionable tactical advice, rather than merely collecting and displaying telemetry.
- **Planning rule:** Do not treat the video's title as a feature specification. Review the actual video content (or a transcript / user-provided notes) with the user, identify the specific workflow or feature worth learning from, and then decide whether it belongs in José's product requirements. Preserve José's core principle that it advises the human manager and never changes FM27 instructions autonomously.

---

**Document status:** Living planning and handover document. Updated 10 November 2026 with the guided-from-scratch development decision, the next telemetry diagnostic task, and the FM27 data-analysis video reference awaiting review. This is not a release specification; continue distinguishing verified results, proposals and hypotheses.

## 21. Telemetry source investigation — `NativeMomentumSource.cs`

**Review date:** 11 November 2026  
**Status:** Source reviewed; root cause of the pitch-dimension failure remains unconfirmed.

The user supplied the complete contents of `Memory/NativeMomentumSource.cs` from the FMMatchLens v0.7.1 source checkout. This file defines an `internal readonly record struct NativeMomentumSource` and a static `TryRead(nint match, out NativeMomentumSource value)` method.

### Observed read sequence

1. Reject a null `match` pointer.
2. Calculate the address of the momentum-source pointer holder using `Offsets.GameMatch.MomentumEventSource`.
3. Check that the holder is readable, then read the source pointer with `Marshal.ReadIntPtr`.
4. Check that the source memory range through `HalfPitchLength + sizeof(float)` is readable.
5. Read the event-buffer begin/end pointers, calculate the byte length, and validate alignment, maximum event count, integer range and buffer readability.
6. Read `HalfPitchWidth` and `HalfPitchLength` as floats.
7. Reject either dimension if non-finite or less than or equal to zero.
8. Read the latest event tick if the event buffer is non-empty. Calculation metadata is optional and is read only if the larger source range is readable.
9. Return the populated snapshot.

`ReadFloat` interprets a 32-bit integer read from native memory as IEEE-754 float bits using `BitConverter.Int32BitsToSingle`.

### Initial interpretation

- The method is a pointer-chain reader, not a calculation of pitch dimensions. It follows a pointer stored in the match object, then reads fields from the pointed-to native structure using offsets.
- A `false` return can result from multiple checks, not only invalid pitch values. Therefore, a log message saying pitch dimensions are invalid must be traced to the caller and writer validation before concluding that this method's float validation is the precise failure point.
- The width and length checks enforce finiteness and positivity, but do not enforce plausible upper/lower bounds.
- The field names `HalfWidth` and `HalfLength` indicate half-pitch values. Previously observed valid telemetry included `34.3125` and `50.325`; these are useful comparison values, not universal hard-coded constants.
- `calculation` is deliberately optional: failure to read the optional calculation metadata does not prevent publishing when the essential event and pitch data are valid.
- The code alone does not establish whether the failure is caused by an incorrect offset, a null/stale pointer, timing/initialisation, unreadable memory, or uninitialised/invalid field values.

### Next source files to inspect

Request and review these in order, without modifying the source yet:

1. `Memory/Offsets.cs` — verify the declared offsets for `GameMatch.MomentumEventSource` and all `MomentumEventSource` fields, plus the event structure size and tick offset.
2. `Memory/GameMatchTickHook.cs` — trace where `NativeMomentumSource.TryRead` is called, how its failure is handled, and how pitch dimensions reach captured frames and archive writing.
3. If needed, inspect `Memory/VirtualMemory.cs` to understand exactly what `IsReadable` guarantees and how memory-read scopes are managed.

### Diagnostic principle

Do not patch offsets, insert guessed pitch constants, or weaken validation at this stage. First establish the exact failure path and compare raw read values, pointer validity, and timing against a successful capture. Any instrumentation should be minimal, build-specific, and safe inside the native match-update hook.

### Guided learning note

The user wants to write José's code from scratch with light-to-moderate guidance. Explain native pointers, offsets, `nint`, `Marshal`, `record struct`, and validation in context; use focused questions and small diagnostic steps rather than dumping a complete replacement implementation.

---

**Document status:** Living planning and handover document. Updated 11 November 2026 after reviewing `NativeMomentumSource.cs`. Root cause remains open; next file is `Memory/Offsets.cs`.

## 22. Pitch-dimension failure path (12 November 2026)

**Status:** Failure *path* mapped. Why the native floats are missing or invalid is still unconfirmed.

### Offsets used by the reader

| Constant | Value | Meaning |
|---|---|---|
| `GameMatch.MomentumEventSource` | `0x14EA8` | Pointer field on the match object, not the pitch floats |
| `MomentumEventSource.HalfPitchWidth` | `0xE0` | Float on the pointed-to source object |
| `MomentumEventSource.HalfPitchLength` | `0xE4` | Float on the pointed-to source object |

These constants are not marked unconfirmed in `Offsets.cs`. They are still unverified at runtime.

### Call chain (verified from source)

1. `MomentumCalculator.Capture` is the only `NativeMomentumSource.TryRead` call site found in the plugin (`Memory/MomentumCalculator.cs`).
2. The `bool` from `TryRead` is discarded. On failure, `source` stays `default` (zeros, including `Address == 0`).
3. `CaptureLocked` returns early when `_disposed`, `match == default`, `source.Count == 0`, or `!source.HasCalculationData`. That is a quiet return, not an exception, and it does not mention pitch.
4. `GameMatchTickHook.CaptureNativeMomentumEvents` copies `snapshot.HalfWidth` / `HalfLength` onto the frame and returns immediately if `snapshot.Address == 0`.
5. `HasValidPitchDimensions` requires finite values, `> 0`, and `<= 1000`. That is stricter than `TryRead` (finite and `> 0` only).
6. `BackfillLeadingPitchDimensions` finds the first valid frame. If none, `sourceIndex` stays `-1` and it returns `(0, -1)`.
7. `CommitPreLockFrames` logs those two numbers. An empty cache can also return `-1`, but the observed log committed ticks 1–5, so this was a real backfill miss, not an empty cache.

### What the observed log means

`pitchBackfilled=0` and `pitchSourceTick=-1` mean no pre-lock frame passed `HasValidPitchDimensions`. The archive writer then rejects the match. This does **not** yet prove whether `TryRead` returned false, the pointer was null, the range was unreadable, or the floats were zero / non-finite / above 1000.

### Next diagnostic (agreed 12 November 2026)

Work only on a **copy** of the FMMatchLens plugin source, never the installed plugin or FM27 files. Do not hardcode pitch dimensions.

Log, at most once per several ticks, from `MomentumCalculator.Capture` after `TryRead`:
- whether `TryRead` returned true
- `source.Address`
- `source.HalfWidth` and `source.HalfLength` (raw)
- match tick if already available in that method

Keep the log off the native match-update hook callback. One change at a time. Re-run one match and compare the new BepInEx log with the previous archive failure.

---

**Document status:** Living planning and handover document. Updated 12 November 2026 after mapping the pitch-dimension failure path. Root cause of the native read remains open. Next step is a bounded diagnostic log on a plugin copy.

# José Guardiniho

Local-first AI assistant manager for Football Manager 27 (Steam).

## Current milestone: telemetry proof of concept

This starter is deliberately read-only. It does not modify Football Manager, save games,
match tactics, or the match engine.

## Architecture

- FM27 + FMMatchLens: match telemetry source.
- Python/FastAPI: José runtime and API.
- Ollama: local model runtime (model selection pending GPU/VRAM check).
- SQLite: later milestone for match observations and recommendations.
- Angular: planned dashboard.
- OpenGrokBot + Docker: optional development-agent environment, isolated from FM27.

## Requirements

- Windows 10 22H2 or Windows 11 x64
- Python 3.11+ (3.12 recommended)
- Git
- Ollama for Windows
- FM27 Steam and a verified FMMatchLens/BepInEx installation

## Run the backend

PowerShell:

```powershell
cd backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/health

## Safety boundaries

1. The first release is telemetry-only and advisory.
2. No write access to FM27, save files, or game memory.
3. Do not mount the Docker socket into agent containers.
4. Do not expose Ollama or José's API to the LAN; bind to loopback.
5. Do not provide agents with credentials or personal folders.
6. Treat all telemetry as data, not executable instructions.

## Next steps

1. Verify Ollama installation and identify GPU/VRAM.
2. Verify FMMatchLens v0.7.1 with FM27 Steam.
3. Capture a short test match and inspect the real API payloads.
4. Implement the adapter against observed endpoints and schemas.
5. Add archived-match replay before live tactical reasoning.

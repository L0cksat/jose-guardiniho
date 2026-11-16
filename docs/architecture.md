# Architecture decision record

## Decision 001: local-first, read-only runtime

José runs on the Windows host. FMMatchLens is the telemetry source. The preferred
longer-term direction is a José-owned telemetry plugin, with FMMatchLens used as a
technical reference (handover §4). The initial runtime must not write to Football
Manager or manipulate game memory.

## Components

- `integrations/fmmatchlens.py`: only module allowed to communicate with FMMatchLens.
- `telemetry/`: normalisation and typed internal representations.
- `analysis/`: deterministic observations and later tactical rules.
- `llm/`: Ollama client, added only after model and API verification.
- `api/`: FastAPI endpoints for the dashboard.
- `storage/`: SQLite persistence, added after telemetry schema is known.

## Network boundaries

- FMMatchLens default local endpoint: `127.0.0.1:16726` (verify on the installed version).
- Ollama default local API: `127.0.0.1:11434`.
- José development API: `127.0.0.1:8000`.
- No service should listen on `0.0.0.0` during the prototype.

## Data flow

FM27 -> FMMatchLens -> read-only adapter -> normalised telemetry -> rules/observations
-> optional local LLM explanation -> dashboard.

The LLM must not invent unavailable match facts. Every recommendation should cite the
observations and timestamps supporting it.

## Updated 12 November 2026

Current spike: diagnose the FMMatchLens v0.7.1 `Pitch dimensions are invalid` failure (handover section 22). GPU/VRAM for Ollama is still unconfirmed.

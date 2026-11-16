# Local model selection

Do not choose a model based on system RAM alone. Record:

- GPU make/model
- Dedicated VRAM
- Windows version
- Whether the GPU is shared/integrated
- Available disk space for model files

Start with one modest instruct model, benchmark latency and memory use, then compare
a larger model if hardware permits. José's tactical rules should remain deterministic;
the LLM explains evidence and drafts recommendations rather than calculating match
statistics from raw data.

## Updated 12 November 2026

GPU/VRAM is still unconfirmed; do not choose a model yet. Current engineering spike is the pitch-dimension failure path (handover section 22).

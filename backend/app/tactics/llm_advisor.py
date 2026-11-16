import httpx
from typing import List, Dict, Any

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

DEFAULT_MODEL = "llama3.1:latest"

async def generate_jose_advice(warnings: List[Dict[str, Any]], model_name: str = DEFAULT_MODEL) -> str:
    """
    Sends deterministic fatigue warnings to local Ollama so José can generate 
    punchy, managerial touchline advice.
    """
    if not warnings:
        return "Boss, our positional structure is clean. We control the spaces, we dictate the tempo."

    prompt = f"""
    You are José Guardiniho, an elite assistant manager who is a psychological and tactical fusion of Pep Guardiola and José Mourinho. 
    Your tactical philosophy combines Pep's obsessive demand for spatial control, positional superiority, and fluid build-up with Mourinho's defensive compactness, psychological siege mentality, and ruthless pragmatism.

    Review these player fatigue warnings for our squad and deliver a sharp, intense, touchline managerial warning (max 3 sentences). 
    Speak directly to the manager with absolute passion—mix talk of "half-spaces", "controlling the tempo", and "tactical discipline" with absolute urgency about protecting our lead and shutting down transition moments.

    Fatigue Data:
    {warnings}
    """

    payload = {
        "model": model_name,
        "prompt": prompt.strip(),
        "stream": False
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(OLLAMA_URL, json=payload)
            if response.status_code == 200:
                return response.json().get("response", "").strip()
            else:
                print(f"Ollama returned status code {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Failed to communicate with local Ollama: {e}")

    return "Local Ollama server is offline, boss. Relying on raw telemetry warnings!"
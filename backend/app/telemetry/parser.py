import re
from typing import Dict, List, Optional

def parse_fmlens_player_metadata(file_path: str) -> Dict[int, str]:
    """Scans the .fmlens file binary content to extract embedded player names 
    and map them into a dictionary."""
    player_map: Dict[int, str] = {}

    try:
        with open(file_path, "rb") as f:
            content = f.read()

        text_content = content.decode("latin-1", errors="ignore")

        raw_names = re.findall(r'[A-Z][a-z]+(?:\s+[A-Z][a-z\-]+)+', text_content)

        excluded_terms = {"Away Home", "Barclays Women", "Super League", "Man Utd", "Chelsea", "Arsenal", "Liverpool", "Crystal Palace", "Brighton", "London City Lionesses", "West Ham", "Aston Villa", "Man City", "Charlton", "Birmingham City", "Everton", "Tottenham Hotspur"}
        unique_names : List[str] = []
        seen = set()

        for name in raw_names:
            if name not in seen and not any(term in name for term in excluded_terms):
                seen.add(name)
                unique_names.append(name)

        for idx, name in enumerate(unique_names, start=1):
            player_map[idx] = name

    except Exception as e:
        print(f"Failed to parse player metadata from {file_path}: {e}")
    return player_map

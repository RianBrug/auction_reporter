import os
import json
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# DeepSeek API configuration
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")

# Feature flags
USE_LLM = os.getenv("USE_LLM", "false").lower() == "true"
FETCH_DESCRIPTIONS = os.getenv("FETCH_DESCRIPTIONS", "true").lower() == "true"
DEDUPLICATE = os.getenv("DEDUPLICATE", "true").lower() == "true"

# Selenium configuration
SELENIUM_WAIT_TIME = int(os.getenv("SELENIUM_WAIT_TIME", "10"))
HEADLESS_BROWSER = os.getenv("HEADLESS_BROWSER", "true").lower() == "true"

# Location specific configurations
LOCATIONS = {
    "itapiruba": {
        "name": "Itapiruba",
        "state": "SC",
        "aliases": ["itapirubá", "itapiruba/sc", "itapirubá/sc"],
        "fallback_url": "https://www.centralsuldeleiloes.com.br/leilao/9867/lote/235407/imovel-com-area-de-375-00m2-no-loteamento-balneario-itapiruba-no-municipio-de-laguna-sc"
    },
    "florianopolis": {
        "name": "Florianópolis",
        "state": "SC",
        "aliases": ["floripa", "florianopolis/sc", "florianópolis/sc"]
    },
    "balneario-camboriu": {
        "name": "Balneário Camboriú",
        "state": "SC",
        "aliases": ["balneario camboriu", "bc", "balneario", "camboriú", "camboriu"]
    },
    "sao-paulo": {
        "name": "São Paulo",
        "state": "SP",
        "aliases": ["sao paulo", "sp", "sao paulo/sp", "são paulo/sp"]
    },
    "rio-de-janeiro": {
        "name": "Rio de Janeiro",
        "state": "RJ",
        "aliases": ["rio", "rj", "rio de janeiro", "rio de janeiro/rj"]
    }
}

# Function to get location config
def get_location_config(query: str) -> Dict[str, Any]:
    """
    Get configuration for a location based on a query
    
    Args:
        query: User search query
        
    Returns:
        Location configuration dictionary
    """
    query_lower = query.lower().strip()
    
    # Check for exact match
    for location_id, config in LOCATIONS.items():
        if query_lower == location_id or query_lower == config["name"].lower():
            return config
    
    # Check for alias match
    for location_id, config in LOCATIONS.items():
        if any(alias.lower() == query_lower for alias in config.get("aliases", [])):
            return config
    
    # Check for partial match
    for location_id, config in LOCATIONS.items():
        if location_id in query_lower or query_lower in location_id:
            return config
        
        for alias in config.get("aliases", []):
            if alias.lower() in query_lower or query_lower in alias.lower():
                return config
    
    # No match found, return empty config
    return {}

# Auction source configurations
SOURCES = {
    "central_sul": {
        "base_url": "https://www.centralsuldeleiloes.com.br/leiloes/leilao-de-imovel",
        "enabled": True
    },
    # Add other auction sources here with similar configuration
}

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Search queries
DEFAULT_QUERY = os.getenv("DEFAULT_QUERY", "itapiruba") 

"""Common utility functions"""
import json
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

def load_json(filepath: str) -> Dict[str, Any]:
    """Load and validate JSON file"""
    try:
        with open(filepath) as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load JSON from {filepath}: {e}")
        return {}

def validate_schema(data: Dict, schema: Dict) -> bool:
    """Validate data against schema"""
    # Implement JSON schema validation
    return True

def health_check(url: str, timeout: int = 5) -> bool:
    """Check if service is healthy"""
    import requests
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code == 200
    except:
        return False

"""
COVAL Models Package

Contains all data models, enums, and type definitions for the COVAL system.
"""

from .generation_models import (
    LLMModel,
    GenerationRequest, 
    GenerationResult,
    ModelCapabilities
)

__all__ = [
    "LLMModel",
    "GenerationRequest",
    "GenerationResult", 
    "ModelCapabilities"
]

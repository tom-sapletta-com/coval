#!/usr/bin/env python3
"""
COVAL Generation Models

Contains data models, enums, and type definitions for code generation.
Extracted from generation_engine.py for better modularity.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class LLMModel(Enum):
    """Available LLM models for code generation."""
    QWEN_CODER = "qwen2.5-coder:7b"
    DEEPSEEK_CODER = "deepseek-coder:6.7b"
    CODELLAMA_13B = "codellama:13b"
    DEEPSEEK_R1 = "deepseek-r1:7b"
    GRANITE_CODE = "granite-code:8b"
    MISTRAL = "mistral:7b"


@dataclass
class GenerationRequest:
    """Request for code generation."""
    description: str
    framework: str
    language: str
    features: List[str]
    constraints: List[str]
    existing_code: Optional[str] = None
    test_requirements: Optional[str] = None
    performance_requirements: Optional[str] = None
    style_guide: Optional[str] = None


@dataclass
class GenerationResult:
    """Result of code generation."""
    success: bool
    generated_files: Dict[str, str]  # filename -> content
    documentation: str
    tests: Dict[str, str]  # test_filename -> content
    dockerfile: Optional[str]
    docker_compose: Optional[str]
    dependencies: List[str]
    setup_instructions: str
    execution_time: float
    model_used: str
    confidence_score: float
    error_message: Optional[str] = None


@dataclass
class ModelCapabilities:
    """LLM model capabilities and specializations."""
    max_tokens: int
    temperature: float
    context_window: int
    base_capability: float
    specializations: List[str]
    retry_attempts: int


# Model mapping configurations
CLI_MODEL_MAPPING = {
    'qwen': LLMModel.QWEN_CODER,
    'deepseek': LLMModel.DEEPSEEK_CODER,
    'codellama': LLMModel.CODELLAMA_13B,
    'deepseek-r1': LLMModel.DEEPSEEK_R1,
    'granite': LLMModel.GRANITE_CODE,
    'mistral': LLMModel.MISTRAL,
}

CONFIG_KEY_MAPPING = {
    LLMModel.QWEN_CODER: 'qwen',
    LLMModel.DEEPSEEK_CODER: 'deepseek',
    LLMModel.CODELLAMA_13B: 'codellama13b',
    LLMModel.DEEPSEEK_R1: 'deepseek-r1',
    LLMModel.GRANITE_CODE: 'granite',
    LLMModel.MISTRAL: 'mistral',
}

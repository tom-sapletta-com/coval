"""
COVAL v2.0 - Intelligent Code Generation, Execution, and Repair System

A comprehensive Python package for iterative code generation, execution, and repair
with Docker integration and transparent deployment capabilities.

Features:
- Iterative code generation with multiple LLM models
- Docker Compose integration with volume mounting
- Transparent deployment system
- Legacy code cleanup and cost optimization
- Adaptive evaluation and learning
"""

__version__ = "2.0.0"
__author__ = "Tom Sapletta"
__email__ = "tom@sapletta.com"

from .core.iteration_manager import IterationManager
from .core.cost_calculator import CostCalculator
from .engines.generation_engine import GenerationEngine
from .engines.repair_engine import RepairEngine
from .docker.deployment_manager import DeploymentManager

__all__ = [
    'IterationManager',
    'CostCalculator', 
    'GenerationEngine',
    'RepairEngine',
    'DeploymentManager',
]

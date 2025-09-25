#!/usr/bin/env python3
"""
COVAL Generation Engine

Handles code generation using multiple LLM models with iterative improvement.
Integrates with the existing LLM configuration and model management system.
"""

import os
import json
import yaml
import logging
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


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


class GenerationEngine:
    """
    Code generation engine that works with multiple LLM models.
    
    Features:
    - Multi-model support with automatic model selection
    - Framework-specific code generation
    - Iterative refinement based on feedback
    - Integration with existing repair system
    - Docker containerization support
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "llm.config.yaml"
        self.config = self._load_config()
        self.model_capabilities = self._load_model_capabilities()
        
        # Generation templates
        self.templates_dir = Path(__file__).parent.parent / "templates"
        self.templates_dir.mkdir(exist_ok=True)
        
        # Setup logging
        self._setup_logging()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load LLM configuration."""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        
        logger.warning(f"Config file {self.config_path} not found, using defaults")
        # Return minimal default config
        return {
            'global': {
                'timeout': 60,
                'max_iterations': 5
            },
            'models': {
                'qwen2.5-coder': {
                    'model_name': 'qwen2.5-coder:7b',
                    'max_tokens': 16384,
                    'temperature': 0.2,
                    'base_capability': 0.85
                }
            }
        }
    
    def _load_model_capabilities(self) -> Dict[str, ModelCapabilities]:
        """Load model capabilities from configuration."""
        capabilities = {}
        
        for model_key, model_config in self.config.get('models', {}).items():
            capabilities[model_key] = ModelCapabilities(
                max_tokens=model_config.get('max_tokens', 8192),
                temperature=model_config.get('temperature', 0.2),
                context_window=model_config.get('context_window', 8192),
                base_capability=model_config.get('base_capability', 0.7),
                specializations=model_config.get('specialization', []),
                retry_attempts=model_config.get('retry_attempts', 3)
            )
        
        return capabilities
    
    def _setup_logging(self):
        """Setup logging for generation engine."""
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    def select_optimal_model(self, request: GenerationRequest) -> Tuple[str, LLMModel]:
        """
        Select the optimal model for a generation request.
        
        Args:
            request: Generation request with requirements
            
        Returns:
            Tuple of (model_config_key, LLMModel)
        """
        best_model = None
        best_score = 0.0
        best_key = None
        
        for model_key, capabilities in self.model_capabilities.items():
            score = self._calculate_model_score(request, capabilities)
            
            if score > best_score:
                best_score = score
                best_model = self._get_llm_model_enum(model_key)
                best_key = model_key
        
        if best_model is None:
            # Default to qwen if no specific match
            best_key = 'qwen2.5-coder'
            best_model = LLMModel.QWEN_CODER
        
        logger.info(f"Selected model {best_model.value} (score: {best_score:.2f}) for {request.framework} {request.language}")
        return best_key, best_model
    
    def _calculate_model_score(self, request: GenerationRequest, capabilities: ModelCapabilities) -> float:
        """Calculate how well a model matches the request requirements."""
        score = capabilities.base_capability
        
        # Language/framework specialization bonus
        specializations = [s.lower() for s in capabilities.specializations]
        if request.language.lower() in specializations:
            score += 0.1
        if request.framework.lower() in specializations:
            score += 0.15
        
        # Feature matching
        for feature in request.features:
            if any(spec in feature.lower() for spec in specializations):
                score += 0.05
        
        # Token capacity bonus for complex requests
        estimated_complexity = len(request.description) + len(' '.join(request.features))
        if estimated_complexity > 1000 and capabilities.max_tokens > 12000:
            score += 0.1
        
        # Context window bonus for existing code
        if request.existing_code and len(request.existing_code) > 5000:
            if capabilities.context_window > 16000:
                score += 0.1
        
        return min(score, 1.0)
    
    def _get_llm_model_enum(self, model_key: str) -> LLMModel:
        """Convert model key to LLMModel enum."""
        model_mapping = {
            'qwen2.5-coder': LLMModel.QWEN_CODER,
            'deepseek-coder': LLMModel.DEEPSEEK_CODER,
            'codellama': LLMModel.CODELLAMA_13B,
            'deepseek-r1': LLMModel.DEEPSEEK_R1,
            'granite-code': LLMModel.GRANITE_CODE,
            'mistral': LLMModel.MISTRAL
        }
        return model_mapping.get(model_key, LLMModel.QWEN_CODER)
    
    def _ensure_model_available(self, model: LLMModel) -> bool:
        """Ensure the specified model is available via ollama."""
        model_name = model.value
        logger.info(f"🔍 Checking model availability: {model_name}")
        
        try:
            # Check if model is available
            result = subprocess.run(
                ["ollama", "list"], 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            if result.returncode == 0 and model_name in result.stdout:
                logger.info(f"✅ Model {model_name} is available")
                return True
            
            # Pull model if not available
            logger.info(f"📥 Pulling model: {model_name}")
            pull_result = subprocess.run(
                ["ollama", "pull", model_name],
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if pull_result.returncode == 0:
                logger.info(f"✅ Successfully pulled model: {model_name}")
                return True
            else:
                logger.error(f"❌ Failed to pull model: {pull_result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"⏱️ Timeout pulling model: {model_name}")
            return False
        except FileNotFoundError:
            logger.error("❌ Ollama not installed or not in PATH")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            return False
    
    def generate_code(self, request: GenerationRequest, output_dir: Path) -> GenerationResult:
        """
        Generate code according to the request.
        
        Args:
            request: Generation request
            output_dir: Directory to write generated code
            
        Returns:
            GenerationResult with success status and generated files
        """
        start_time = datetime.now()
        
        # Select optimal model
        model_key, model = self.select_optimal_model(request)
        
        # Ensure model is available
        if not self._ensure_model_available(model):
            return GenerationResult(
                success=False,
                generated_files={},
                documentation="",
                tests={},
                dockerfile=None,
                docker_compose=None,
                dependencies=[],
                setup_instructions="",
                execution_time=0.0,
                model_used=model.value,
                confidence_score=0.0,
                error_message="Model not available"
            )
        
        try:
            # Generate the prompt
            prompt = self._create_generation_prompt(request)
            
            # Call LLM for generation
            generation_response = self._call_llm(model, prompt, model_key)
            
            if not generation_response:
                raise Exception("Failed to get response from LLM")
            
            # Parse and extract generated code
            files, docs, tests = self._parse_generation_response(generation_response)
            
            # Generate Docker files
            dockerfile = self._generate_dockerfile(request, files)
            docker_compose = self._generate_docker_compose(request)
            
            # Extract dependencies
            dependencies = self._extract_dependencies(request, files)
            
            # Write files to output directory
            self._write_generated_files(output_dir, files, tests)
            
            # Generate setup instructions
            setup_instructions = self._generate_setup_instructions(request, dependencies)
            
            # Calculate confidence score
            confidence = self._calculate_confidence_score(request, files, tests)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"✅ Code generation completed in {execution_time:.2f}s")
            
            return GenerationResult(
                success=True,
                generated_files=files,
                documentation=docs,
                tests=tests,
                dockerfile=dockerfile,
                docker_compose=docker_compose,
                dependencies=dependencies,
                setup_instructions=setup_instructions,
                execution_time=execution_time,
                model_used=model.value,
                confidence_score=confidence
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ Code generation failed: {e}")
            
            return GenerationResult(
                success=False,
                generated_files={},
                documentation="",
                tests={},
                dockerfile=None,
                docker_compose=None,
                dependencies=[],
                setup_instructions="",
                execution_time=execution_time,
                model_used=model.value,
                confidence_score=0.0,
                error_message=str(e)
            )
    
    def _create_generation_prompt(self, request: GenerationRequest) -> str:
        """Create a comprehensive prompt for code generation."""
        prompt_parts = [
            f"Generate a complete {request.framework} application in {request.language}.",
            f"Description: {request.description}",
            "",
            "Requirements:",
        ]
        
        for feature in request.features:
            prompt_parts.append(f"- {feature}")
        
        if request.constraints:
            prompt_parts.append("\nConstraints:")
            for constraint in request.constraints:
                prompt_parts.append(f"- {constraint}")
        
        if request.existing_code:
            prompt_parts.extend([
                "\nExisting code to integrate or modify:",
                "```",
                request.existing_code,
                "```"
            ])
        
        if request.test_requirements:
            prompt_parts.extend([
                "\nTest requirements:",
                request.test_requirements
            ])
        
        prompt_parts.extend([
            "",
            "Please provide:",
            "1. Complete, working source code files",
            "2. Comprehensive tests",
            "3. Documentation",
            "4. Dependencies list",
            "5. Setup instructions",
            "",
            "Format the response with clear file separations using:",
            "===== FILENAME: path/to/file.ext =====",
            "===== TESTS: path/to/test_file.py =====",
            "===== DOCUMENTATION =====",
            "===== DEPENDENCIES =====",
            "===== SETUP =====",
        ])
        
        return "\n".join(prompt_parts)
    
    def _call_llm(self, model: LLMModel, prompt: str, model_key: str) -> Optional[str]:
        """Call the LLM with the generation prompt."""
        try:
            # Create temporary file for prompt
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(prompt)
                prompt_file = f.name
            
            # Get model configuration
            model_config = self.config['models'].get(model_key, {})
            temperature = model_config.get('temperature', 0.2)
            
            # Call ollama
            cmd = [
                "ollama", "run", model.value,
                f"--temperature={temperature}",
                f"< {prompt_file}"
            ]
            
            result = subprocess.run(
                " ".join(cmd),
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.config['global'].get('timeout', 300)
            )
            
            # Cleanup
            os.unlink(prompt_file)
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logger.error(f"LLM call failed: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            return None
    
    def _parse_generation_response(self, response: str) -> Tuple[Dict[str, str], str, Dict[str, str]]:
        """Parse the LLM response to extract files, documentation, and tests."""
        files = {}
        tests = {}
        documentation = ""
        
        # Split response into sections
        sections = response.split("=====")
        current_section = None
        current_content = []
        
        for section in sections:
            section = section.strip()
            
            if section.startswith("FILENAME:"):
                # Save previous section
                if current_section and current_content:
                    content = "\n".join(current_content).strip()
                    if current_section.startswith("FILENAME:"):
                        filename = current_section.replace("FILENAME:", "").strip()
                        files[filename] = content
                    elif current_section.startswith("TESTS:"):
                        filename = current_section.replace("TESTS:", "").strip()
                        tests[filename] = content
                
                current_section = section
                current_content = []
            elif section.startswith("TESTS:"):
                # Save previous file
                if current_section and current_content:
                    content = "\n".join(current_content).strip()
                    if current_section.startswith("FILENAME:"):
                        filename = current_section.replace("FILENAME:", "").strip()
                        files[filename] = content
                
                current_section = section
                current_content = []
            elif section.startswith("DOCUMENTATION"):
                current_section = "DOCUMENTATION"
                current_content = []
            elif section.startswith("DEPENDENCIES") or section.startswith("SETUP"):
                # Skip these for now, we'll handle them separately
                current_section = None
                current_content = []
            else:
                if current_section:
                    current_content.append(section)
        
        # Handle last section
        if current_section and current_content:
            content = "\n".join(current_content).strip()
            if current_section.startswith("FILENAME:"):
                filename = current_section.replace("FILENAME:", "").strip()
                files[filename] = content
            elif current_section.startswith("TESTS:"):
                filename = current_section.replace("TESTS:", "").strip()
                tests[filename] = content
            elif current_section == "DOCUMENTATION":
                documentation = content
        
        return files, documentation, tests
    
    def _generate_dockerfile(self, request: GenerationRequest, files: Dict[str, str]) -> str:
        """Generate Dockerfile for the application."""
        if request.language.lower() == 'python':
            return self._generate_python_dockerfile(request)
        elif request.language.lower() in ['javascript', 'typescript']:
            return self._generate_node_dockerfile(request)
        else:
            return self._generate_generic_dockerfile(request)
    
    def _generate_python_dockerfile(self, request: GenerationRequest) -> str:
        """Generate Python-specific Dockerfile."""
        return """FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["python", "main.py"]
"""
    
    def _generate_node_dockerfile(self, request: GenerationRequest) -> str:
        """Generate Node.js-specific Dockerfile."""
        return """FROM node:18-alpine

WORKDIR /app

# Copy package files first for better caching
COPY package*.json ./
RUN npm ci --only=production

# Copy application code
COPY . .

# Expose port
EXPOSE 3000

# Run application
CMD ["node", "index.js"]
"""
    
    def _generate_generic_dockerfile(self, request: GenerationRequest) -> str:
        """Generate generic Dockerfile."""
        return """FROM ubuntu:22.04

WORKDIR /app

# Install basic dependencies
RUN apt-get update && apt-get install -y \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Default command
CMD ["./start.sh"]
"""
    
    def _generate_docker_compose(self, request: GenerationRequest) -> str:
        """Generate docker-compose.yml for the application."""
        return f"""version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - .:/app
    environment:
      - NODE_ENV=development
    restart: unless-stopped
    
    # Add database if needed
    depends_on:
      - db
      
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: {request.framework.lower()}
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
"""
    
    def _extract_dependencies(self, request: GenerationRequest, files: Dict[str, str]) -> List[str]:
        """Extract dependencies from generated files."""
        dependencies = []
        
        # Check for Python requirements
        if 'requirements.txt' in files:
            deps = [line.strip() for line in files['requirements.txt'].split('\n') if line.strip()]
            dependencies.extend(deps)
        
        # Check for Node.js package.json
        if 'package.json' in files:
            try:
                package_data = json.loads(files['package.json'])
                deps = list(package_data.get('dependencies', {}).keys())
                dependencies.extend(deps)
            except json.JSONDecodeError:
                pass
        
        return dependencies
    
    def _write_generated_files(self, output_dir: Path, files: Dict[str, str], tests: Dict[str, str]):
        """Write generated files to the output directory."""
        # Write main files
        for filename, content in files.items():
            file_path = output_dir / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        # Write test files
        for filename, content in tests.items():
            file_path = output_dir / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
    
    def _generate_setup_instructions(self, request: GenerationRequest, dependencies: List[str]) -> str:
        """Generate setup instructions for the generated code."""
        instructions = [
            f"# Setup Instructions for {request.framework} Application",
            "",
            "## Prerequisites",
        ]
        
        if request.language.lower() == 'python':
            instructions.extend([
                "- Python 3.11+",
                "- pip package manager",
                "",
                "## Installation",
                "```bash",
                "pip install -r requirements.txt",
                "```"
            ])
        elif request.language.lower() in ['javascript', 'typescript']:
            instructions.extend([
                "- Node.js 18+",
                "- npm or yarn",
                "",
                "## Installation", 
                "```bash",
                "npm install",
                "```"
            ])
        
        instructions.extend([
            "",
            "## Running with Docker",
            "```bash",
            "docker-compose up --build",
            "```",
            "",
            "## Development",
            "1. Make your changes",
            "2. Test with: `docker-compose up --build`",
            "3. Access at: http://localhost:8000",
        ])
        
        return "\n".join(instructions)
    
    def _calculate_confidence_score(self, request: GenerationRequest, 
                                  files: Dict[str, str], tests: Dict[str, str]) -> float:
        """Calculate confidence score for the generation."""
        score = 0.0
        
        # Basic file generation score
        if files:
            score += 0.3
        
        # Test coverage bonus
        if tests:
            score += 0.2
        
        # Documentation bonus
        total_content = sum(len(content) for content in files.values())
        if total_content > 1000:  # Substantial content
            score += 0.2
        
        # Feature completeness (rough estimate)
        feature_keywords = [f.lower() for f in request.features]
        all_content = ' '.join(files.values()).lower()
        matched_features = sum(1 for keyword in feature_keywords if keyword in all_content)
        if feature_keywords:
            score += (matched_features / len(feature_keywords)) * 0.3
        else:
            score += 0.3  # No specific features requested
        
        return min(score, 1.0)

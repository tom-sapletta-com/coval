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
import shutil
import time
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
        """Load LLM configuration, create default if missing."""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        
        # Auto-generate config from defaults
        print("🔧 Creating llm.config.yaml with default settings...")
        self._create_default_config()
        
        # Load the newly created config
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _create_default_config(self):
        """Create default llm.config.yaml from template."""
        # Try to copy from package config first
        package_config = Path(__file__).parent.parent / "config" / "llm.config.yaml"
        
        if package_config.exists():
            shutil.copy2(package_config, self.config_path)
            return
        
        # Fallback: create minimal config if package config doesn't exist
        default_config = {
            'qwen': {
                'model': 'qwen2.5-coder:7b',
                'max_tokens': 16384,
                'temperature': 0.2,
                'retry_attempts': 3,
                'base_capability': 0.85,
                'context_window': 32768,
                'specialization': 'code_generation_json'
            },
            'deepseek-r1': {
                'model': 'deepseek-r1:7b',
                'max_tokens': 20480,
                'temperature': 0.1,
                'retry_attempts': 3,
                'base_capability': 0.88,
                'context_window': 32768,
                'specialization': 'reasoning_code_repair'
            },
            'global': {
                'timeout_seconds': 120,
                'max_repair_iterations': 5,
                'success_threshold': 0.8
            }
        }
        
        with open(self.config_path, 'w') as f:
            yaml.safe_dump(default_config, f, default_flow_style=False, indent=2)
    
    def _load_model_capabilities(self) -> Dict[str, ModelCapabilities]:
        """Load model capabilities from configuration."""
        capabilities = {}
        
        # Check if config has 'models' section or models at top level
        models_config = self.config.get('models', self.config)
        
        # Process model configurations
        for model_key, model_config in models_config.items():
            if model_key in ['global']:
                continue
                
            if isinstance(model_config, dict):
                # Handle specialization as string or list
                specialization = model_config.get('specialization', [])
                if isinstance(specialization, str):
                    specialization = [specialization]
                
                capabilities[model_key] = ModelCapabilities(
                    max_tokens=model_config.get('max_tokens', 8192),
                    temperature=model_config.get('temperature', 0.2),
                    context_window=model_config.get('context_window', 8192),
                    base_capability=model_config.get('base_capability', 0.7),
                    specializations=specialization,
                    retry_attempts=model_config.get('retry_attempts', 3)
                )
        
        return capabilities
    
    def _setup_logging(self):
        """Setup simplified logging for generation engine."""
        # Set to WARNING to reduce verbose output, only show errors
        logger.setLevel(logging.WARNING)
    
    def select_optimal_model(self, request: GenerationRequest, preferred_model: Optional[str] = None) -> Tuple[str, LLMModel]:
        """
        Select the optimal model for a generation request.
        
        Args:
            request: Generation request with requirements
            preferred_model: User-specified model preference (overrides automatic selection)
            
        Returns:
            Tuple of (model_config_key, LLMModel)
        """
        # If user specified a model, prioritize it
        if preferred_model:
            model_enum = self._get_model_enum_from_cli_name(preferred_model)
            model_key = self._get_config_key_from_enum(model_enum)
            
            if model_key in self.model_capabilities:
                return model_key, model_enum
            else:
                logger.warning(f"Preferred model {preferred_model} not configured, falling back to automatic selection")
        
        # Automatic model selection
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
            best_key = 'qwen'
            best_model = LLMModel.QWEN_CODER
        
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
    
    def _get_model_enum_from_cli_name(self, cli_name: str) -> LLMModel:
        """Convert CLI model name to LLMModel enum."""
        cli_mapping = {
            'qwen': LLMModel.QWEN_CODER,
            'qwen2.5-coder': LLMModel.QWEN_CODER,
            'deepseek': LLMModel.DEEPSEEK_CODER,
            'deepseek-coder': LLMModel.DEEPSEEK_CODER,
            'codellama': LLMModel.CODELLAMA_13B,
            'codellama13b': LLMModel.CODELLAMA_13B,
            'deepseek-r1': LLMModel.DEEPSEEK_R1,
            'granite': LLMModel.GRANITE_CODE,
            'granite-code': LLMModel.GRANITE_CODE,
            'mistral': LLMModel.MISTRAL
        }
        return cli_mapping.get(cli_name, LLMModel.QWEN_CODER)
    
    def _get_config_key_from_enum(self, model_enum: LLMModel) -> str:
        """Convert LLMModel enum back to config key."""
        enum_to_key = {
            LLMModel.QWEN_CODER: 'qwen2.5-coder',
            LLMModel.DEEPSEEK_CODER: 'deepseek-coder', 
            LLMModel.CODELLAMA_13B: 'codellama',
            LLMModel.DEEPSEEK_R1: 'deepseek-r1',
            LLMModel.GRANITE_CODE: 'granite-code',
            LLMModel.MISTRAL: 'mistral'
        }
        return enum_to_key.get(model_enum, 'qwen2.5-coder')
    
    def _ensure_model_available(self, model_key: str) -> bool:
        """Ensure the specified model is available via ollama."""
        # Get actual model name from config - handle both structures
        models_config = self.config.get('models', self.config)
        model_config = models_config.get(model_key, {})
        model_name = model_config.get('model_name', model_config.get('model', model_key))
        
        print(f"🔍 {model_name}...", end=" ", flush=True)
        
        try:
            # Check if model is available
            result = subprocess.run(
                ["ollama", "list"], 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            if result.returncode == 0 and model_name in result.stdout:
                print("✅")
                return True
            
            # Pull model if not available
            print(f"📥 Pulling {model_name}...", end=" ", flush=True)
            pull_result = subprocess.run(
                ["ollama", "pull", model_name],
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if pull_result.returncode == 0:
                print("✅")
                return True
            else:
                print("❌")
                logger.error(f"Failed to pull {model_name}: {pull_result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("⏱️")
            logger.error(f"Timeout pulling {model_name}")
            return False
        except FileNotFoundError:
            print("❌")
            logger.error("Ollama not installed")
            return False
        except Exception as e:
            print("❌")
            logger.error(f"Model check error: {e}")
            return False
    
    def generate_code(self, request: GenerationRequest, output_dir: Path, preferred_model: Optional[str] = None) -> GenerationResult:
        """
        Generate code according to the request.
        
        Args:
            request: Generation request
            output_dir: Directory to write generated code
            
        Returns:
            GenerationResult with success status and generated files
        """
        start_time = datetime.now()
        
        print("🎯 Selecting model...", end=" ", flush=True)
        # Select optimal model (prioritize user preference)
        model_key, model = self.select_optimal_model(request, preferred_model)
        print(f"✅ {model_key}")
        
        # Ensure model is available
        if not self._ensure_model_available(model_key):
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
            print("📝 Creating prompt...", end=" ", flush=True)
            # Generate the prompt
            prompt = self._create_generation_prompt(request)
            print("✅")
            
            print("🤖 Generating code...", end=" ", flush=True)
            # Call LLM for generation
            generation_response = self._call_llm(model_key, prompt)
            
            if not generation_response:
                print("❌")
                raise Exception("Failed to get response from LLM")
            print("✅")
            
            print("📄 Processing files...", end=" ", flush=True)
            # Parse and extract generated code
            files, docs, tests = self._parse_generation_response(generation_response)
            
            # Generate Docker files
            dockerfile = self._generate_dockerfile(request, files)
            docker_compose = self._generate_docker_compose(request)
            
            # Extract dependencies
            dependencies = self._extract_dependencies(request, files)
            print("✅")
            
            print("💾 Writing files...", end=" ", flush=True)
            # Write files to output directory
            self._write_generated_files(output_dir, files, tests)
            print("✅")
            
            # Generate setup instructions
            setup_instructions = self._generate_setup_instructions(request, dependencies)
            
            # Calculate confidence score
            confidence = self._calculate_confidence_score(request, files, tests)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            print(f"🎉 Generation completed in {execution_time:.1f}s")
            
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
                model_used=self.config.get(model_key, {}).get('model', model_key),
                confidence_score=confidence
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            print(f"❌ Generation failed: {e}")
            
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
                model_used=self.config.get(model_key, {}).get('model', model_key),
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
            "IMPORTANT RULES:",
            "- Generate ONLY clean, executable source code",
            "- Do NOT include merge conflict markers (<<<<<<, ======, >>>>>>)",
            "- Do NOT include template placeholders like {{variable}}",
            "- Do NOT use SEARCH/REPLACE patterns or diff syntax", 
            "- Do NOT wrap code in markdown code blocks (```)",
            "- Provide complete, ready-to-run files",
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
    
    def _call_llm(self, model_key: str, prompt: str) -> Optional[str]:
        """Call the LLM with the generation prompt."""
        # Get model configuration and actual model name - handle both structures
        models_config = self.config.get('models', self.config)
        model_config = models_config.get(model_key, {})
        model_name = model_config.get('model_name', model_config.get('model', model_key))

        # Base timeout and retry strategy
        base_timeout = int(self.config.get('global', {}).get('timeout_seconds', 120))
        max_retries = int(model_config.get('retry_attempts', 3))
        # Exponential backoff timeouts: base, 2x, 4x (capped)
        timeouts = [base_timeout, base_timeout * 2, base_timeout * 4]

        cmd = ["ollama", "run", model_name]

        last_error: Optional[str] = None
        for attempt in range(1, max_retries + 1):
            timeout = timeouts[min(attempt - 1, len(timeouts) - 1)]
            try:
                result = subprocess.run(
                    cmd,
                    input=prompt,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )

                if result.returncode == 0:
                    return result.stdout.strip()
                else:
                    last_error = result.stderr.strip()
                    logger.warning(f"LLM call failed (attempt {attempt}/{max_retries}): {last_error}")
            except subprocess.TimeoutExpired:
                last_error = f"Timed out after {timeout} seconds"
                logger.warning(f"LLM call timed out (attempt {attempt}/{max_retries}, timeout={timeout}s)")
            except Exception as e:
                last_error = str(e)
                logger.error(f"Error calling LLM (attempt {attempt}/{max_retries}): {e}")

            # Small backoff between retries
            if attempt < max_retries:
                time.sleep(2)

        # All attempts failed
        if last_error:
            logger.error(f"LLM call failed after {max_retries} attempts: {last_error}")
        return None
    
    def _clean_generated_content(self, content: str) -> str:
        """Clean generated content from problematic patterns."""
        import re
        
        # Remove merge conflict markers and surrounding content
        content = re.sub(r'```python\s*\n<<<<<<< SEARCH.*?>>>>>>> REPLACE\s*\n```', '', content, flags=re.DOTALL)
        content = re.sub(r'<<<<<<< SEARCH.*?>>>>>>> REPLACE', '', content, flags=re.DOTALL)
        content = re.sub(r'<<<<<<<.*?>>>>>>>', '', content, flags=re.DOTALL)
        
        # Remove standalone markdown code block wrappers
        content = re.sub(r'^```(?:python|javascript|typescript|)?\s*\n', '', content, flags=re.MULTILINE)
        content = re.sub(r'\n```\s*$', '', content, flags=re.MULTILINE)
        
        # Remove template placeholders
        content = re.sub(r'\{\{.*?\}\}', '', content)
        
        # Remove diff-style patterns
        content = re.sub(r'^[+-]\s*', '', content, flags=re.MULTILINE)
        
        # Clean up multiple empty lines
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        
        # Strip leading/trailing whitespace
        content = content.strip()
        
        return content

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
                    content = self._clean_generated_content(content)  # Clean content
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
                    content = self._clean_generated_content(content)  # Clean content
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
            content = self._clean_generated_content(content)  # Clean content
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

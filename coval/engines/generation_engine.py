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

# Import modular components
from ..models.generation_models import (
    LLMModel, GenerationRequest, GenerationResult, ModelCapabilities,
    CLI_MODEL_MAPPING, CONFIG_KEY_MAPPING
)
from ..parsers.response_parser import ResponseParser
from ..generators.prompt_generator import PromptGenerator
from ..generators.docker_generator import DockerGenerator
from ..validators.content_cleaner import ContentCleaner

logger = logging.getLogger(__name__)


# Models, dataclasses and enums are now imported from the models package


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
        
        # Initialize modular components
        self.response_parser = ResponseParser()
        self.prompt_generator = PromptGenerator()
        self.docker_generator = DockerGenerator()
        self.content_cleaner = ContentCleaner()
        
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
        # TEMPORARY: Set to DEBUG to diagnose file generation issue
        logger.setLevel(logging.DEBUG)
        
        # Add console handler if not present
        if not logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('🐛 %(levelname)s: %(message)s')
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
    
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
            logger.debug(f"User specified preferred model: {preferred_model}")
            model_enum = self._get_model_enum_from_cli_name(preferred_model)
            model_key = self._get_config_key_from_enum(model_enum)
            logger.debug(f"Mapped CLI name '{preferred_model}' -> enum '{model_enum}' -> config key '{model_key}'")
            logger.debug(f"Available model capabilities keys: {list(self.model_capabilities.keys())}")
            
            if model_key in self.model_capabilities:
                logger.info(f"Using preferred model: {preferred_model} (key: {model_key})")
                return model_key, model_enum
            else:
                logger.warning(f"Preferred model {preferred_model} (key: {model_key}) not found in capabilities. Available: {list(self.model_capabilities.keys())}")
                logger.warning(f"Falling back to automatic selection")
        
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
        """Convert LLMModel enum back to config key matching llm.config.yaml."""
        enum_to_key = {
            LLMModel.QWEN_CODER: 'qwen',  # Fixed: use 'qwen' key from config, not 'qwen2.5-coder'
            LLMModel.DEEPSEEK_CODER: 'deepseek', 
            LLMModel.CODELLAMA_13B: 'codellama13b',
            LLMModel.DEEPSEEK_R1: 'deepseek-r1',
            LLMModel.GRANITE_CODE: 'granite',
            LLMModel.MISTRAL: 'mistral'
        }
        return enum_to_key.get(model_enum, 'qwen')
    
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
            
            # CRITICAL DEBUG: Check LLM response
            print(f"\n🐛 DEBUG: LLM response length: {len(generation_response)}")
            print(f"🐛 DEBUG: Response preview: {generation_response[:200]}...")
            
            # Parse and extract generated code
            files, docs, tests = self._parse_generation_response(generation_response)
            
            # CRITICAL DEBUG: Check parsing results
            print(f"\n🐛 DEBUG: Parsed {len(files)} files, {len(tests)} tests")
            for filename, content in files.items():
                print(f"🐛 DEBUG: File '{filename}': {len(content)} chars")
            
            # Generate Docker files
            dockerfile = self._generate_dockerfile(request, files)
            docker_compose = self._generate_docker_compose(request)
            
            # Extract dependencies
            dependencies = self._extract_dependencies(request, files)
            print("✅")
            
            print("💾 Writing files...", end=" ", flush=True)
            
            # CRITICAL DEBUG: Check before writing
            print(f"\n🐛 DEBUG: About to write {len(files)} files to {output_dir}")
            
            # Write files to output directory
            self._write_generated_files(output_dir, files, tests)
            
            # CRITICAL DEBUG: Verify files were written
            written_files = list(output_dir.rglob("*"))
            print(f"\n🐛 DEBUG: Files on disk after writing: {len(written_files)}")
            for file in written_files:
                if file.is_file():
                    print(f"🐛 DEBUG: Written file: {file.name} ({file.stat().st_size} bytes)")
            
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
        """Create a comprehensive prompt for code generation using modular generator."""
        return self.prompt_generator.create_generation_prompt(request)
    
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
        """Clean generated content using modular ContentCleaner."""
        return self.content_cleaner.clean_generated_content(content)

    def _parse_generation_response(self, response: str) -> Tuple[Dict[str, str], str, Dict[str, str]]:
        """Parse the LLM response to extract files, documentation, and tests using modular parser."""
        return self.response_parser.parse_generation_response(response)
    
    # Duplicate parsing methods removed - now using modular ResponseParser
    
    # All parsing methods moved to modular ResponseParser
    
    def _generate_dockerfile(self, request: GenerationRequest, files: Dict[str, str]) -> str:
        """Generate Dockerfile using modular DockerGenerator."""
        return self.docker_generator.generate_dockerfile(request, files)
    
    # Docker generation methods moved to modular DockerGenerator
    
    # Node.js Docker generation moved to modular DockerGenerator
    
    # Generic Docker generation moved to modular DockerGenerator
    
    def _generate_docker_compose(self, request: GenerationRequest) -> str:
        """Generate docker-compose.yml using modular DockerGenerator."""
        return self.docker_generator.generate_docker_compose(request)
    
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

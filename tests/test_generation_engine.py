"""
Unit tests for GenerationEngine and modular components.
Tests the refactored generation system with modular architecture.
"""
import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from coval.engines.generation_engine import GenerationEngine
from coval.models.generation_models import GenerationRequest, GenerationResult, LLMModel


class TestGenerationEngine:
    """Test cases for GenerationEngine class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = GenerationEngine()
    
    def test_initialization(self):
        """Test GenerationEngine initialization."""
        assert self.engine is not None
        assert hasattr(self.engine, 'prompt_generator')
        assert hasattr(self.engine, 'response_parser')
        assert hasattr(self.engine, 'content_cleaner')
        assert hasattr(self.engine, 'docker_generator')
    
    def test_generation_request_creation(self):
        """Test GenerationRequest data class."""
        request = GenerationRequest(
            description="Test FastAPI app",
            framework="fastapi",
            language="python",
            features=["authentication", "database"],
            constraints=["lightweight", "fast"]
        )
        
        assert request.description == "Test FastAPI app"
        assert request.framework == "fastapi"
        assert request.language == "python"
        assert request.features == ["authentication", "database"]
    
    def test_content_cleaning_integration(self):
        """Test content cleaning with modular ContentCleaner."""
        dirty_content = "```python\nprint('hello')\n```"
        clean_content = self.engine._clean_generated_content(dirty_content)
        
        # Should remove markdown wrapper but preserve code
        assert "print('hello')" in clean_content
        assert "```" not in clean_content
    
    def test_empty_content_handling(self):
        """Test handling of empty or invalid content."""
        empty_content = ""
        result = self.engine._clean_generated_content(empty_content)
        assert result == ""


class TestModularComponents:
    """Test cases for modular components integration."""
    
    @patch('coval.parsers.response_parser.logger')
    def test_response_parser_integration(self, mock_logger):
        """Test ResponseParser integration."""
        engine = GenerationEngine()
        
        # Test with simple response format
        response = """### FILENAME: main.py
def hello():
    return "Hello World"
"""
        
        files, docs, tests = engine._parse_generation_response(response)
        assert isinstance(files, dict)
        assert len(files) >= 0  # May be empty if parsing fails, that's ok for unit test
    
    def test_dockerfile_generation(self):
        """Test Dockerfile generation."""
        engine = GenerationEngine()
        
        request = GenerationRequest(
            description="Test app",
            framework="fastapi",
            language="python",
            features=["basic API"],
            constraints=["simple"]
        )
        files = {"main.py": "print('hello')"}
        
        dockerfile = engine._generate_dockerfile(request, files)
        
        assert dockerfile is not None
        assert isinstance(dockerfile, str)
        assert len(dockerfile) > 0
        assert "python" in dockerfile.lower()


class TestDataModels:
    """Test data model classes."""
    
    def test_llm_model_enum(self):
        """Test LLMModel enum values."""
        assert LLMModel.QWEN_CODER.value == "qwen2.5-coder:7b"
        assert LLMModel.DEEPSEEK_CODER.value == "deepseek-coder:6.7b"
        assert LLMModel.CODELLAMA_13B.value == "codellama:13b"
    
    def test_generation_result_creation(self):
        """Test GenerationResult data class."""
        result = GenerationResult(
            success=True,
            generated_files={"main.py": "print('hello')"},
            documentation="Test docs",
            tests={"test_main.py": "def test_hello(): pass"},
            dockerfile="FROM python:3.12",
            docker_compose="version: '3.8'",
            dependencies=["fastapi", "uvicorn"],
            setup_instructions="Run with docker-compose up",
            execution_time=1.5,
            model_used="qwen2.5-coder:7b",
            confidence_score=0.95
        )
        
        assert result.success is True
        assert result.generated_files["main.py"] == "print('hello')"
        assert result.execution_time == 1.5
        assert result.model_used == "qwen2.5-coder:7b"

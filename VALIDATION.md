# COVAL Validation Guidelines

## 📋 Table of Contents
1. [Overview](#overview)
2. [Testing Strategy](#testing-strategy)
3. [Unit Testing](#unit-testing)
4. [Integration Testing](#integration-testing)
5. [Validation Criteria](#validation-criteria)
6. [CI/CD Pipeline](#cicd-pipeline)
7. [Test Automation](#test-automation)
8. [Quality Gates](#quality-gates)

---

## 1. Overview

### 1.1 Purpose
COVAL (Code Validation and Learning) is an intelligent code generation, execution, and deployment system using multiple LLM models. This document outlines comprehensive validation guidelines to ensure robust, reliable, and deployable applications.

### 1.2 Key Components to Validate
- **GenerationEngine**: Code generation with smart content cleaning
- **DeploymentManager**: Docker container management and health monitoring
- **Model Selection**: Multi-model support with fallback strategies
- **Content Cleaning**: Removal of merge conflicts and invalid patterns
- **Health Monitoring**: Application deployment verification

### 1.3 System Requirements
- Python 3.8+
- Docker 20.10+
- Ollama (for LLM models)
- 8GB RAM minimum
- 20GB disk space

---

## 2. Testing Strategy

### 2.1 Testing Pyramid

```
                    ┌─────────────────┐
                    │  E2E Tests      │ 5%
                    │  Full Workflow  │
                ┌───┴─────────────────┴───┐
                │  Integration Tests      │ 20%
                │  Component Interaction  │
            ┌───┴─────────────────────────┴───┐
            │  Unit Tests                     │ 75%
            │  Individual Functions/Classes   │
            └─────────────────────────────────┘
```

### 2.2 Test Categories

#### 2.2.1 Unit Tests (75%)
- **GenerationEngine** methods: `_clean_generated_content`, model selection, parsing
- **DeploymentManager** methods: container creation, health checks, deployment
- **Utility functions**: file operations, configuration parsing
- **Model mapping**: CLI to config key resolution

#### 2.2.2 Integration Tests (20%)
- **Full COVAL workflow**: generate → clean → deploy → verify
- **Docker integration**: container lifecycle management
- **LLM integration**: model communication and fallback
- **File system operations**: iteration management

#### 2.2.3 End-to-End Tests (5%)
- **Complete user scenarios**: CLI commands with real deployments
- **Multi-model validation**: testing all supported models
- **Error recovery**: handling and cleanup of failed deployments

---

## 3. Unit Testing

### 3.1 GenerationEngine Tests

#### 3.1.1 Content Cleaning Tests
```python
def test_clean_generated_content_removes_merge_conflicts():
    """Test removal of merge conflict markers"""
    engine = GenerationEngine()
    content = """
def function():
<<<<<<< HEAD
    return "old"
=======
    return "new"
>>>>>>> branch
    """
    
    cleaned = engine._clean_generated_content(content)
    assert "<<<<<<< HEAD" not in cleaned
    assert "=======" not in cleaned
    assert ">>>>>>> branch" not in cleaned
    assert "return" in cleaned  # Valid code preserved

def test_clean_generated_content_preserves_valid_code():
    """Test that valid code is not removed"""
    engine = GenerationEngine()
    content = """
def api_function():
    return {"status": "success"}
    """
    
    cleaned = engine._clean_generated_content(content)
    assert "def api_function" in cleaned
    assert "return" in cleaned
    assert len(cleaned.strip()) > 0
```

#### 3.1.2 Model Selection Tests
```python
def test_model_selection_maps_cli_to_config():
    """Test CLI model names map to config keys"""
    engine = GenerationEngine()
    
    # Test qwen mapping
    model_config = engine._get_model_config("qwen")
    assert model_config is not None
    assert "qwen2.5-coder" in model_config.get("model", "")
    
def test_model_selection_fallback():
    """Test fallback when model not available"""
    engine = GenerationEngine()
    
    # Test with non-existent model
    model_config = engine._get_model_config("nonexistent")
    assert model_config is not None  # Should fallback
```

#### 3.1.3 Response Parsing Tests
```python
def test_parse_llm_response_valid_json():
    """Test parsing valid LLM response"""
    engine = GenerationEngine()
    response = '''
    Here's the code:
    ```json
    {"files": {"main.py": "print('hello')"}}
    ```
    '''
    
    result = engine._parse_llm_response(response)
    assert result is not None
    assert "files" in result
    assert "main.py" in result["files"]
```

### 3.2 DeploymentManager Tests

#### 3.2.1 Container Management Tests
```python
def test_create_container_with_valid_config():
    """Test container creation with valid configuration"""
    manager = DeploymentManager()
    
    config = {
        "image": "python:3.11-slim",
        "ports": {"8000/tcp": 8001},
        "environment": {"ENV": "test"}
    }
    
    container = manager.create_container("test-app", config)
    assert container is not None
    assert container.status in ["created", "running"]

def test_health_check_monitoring():
    """Test health check functionality"""
    manager = DeploymentManager()
    
    # Mock a running container
    result = manager.check_health("test-container", "http://localhost:8001/health")
    assert isinstance(result, bool)

def test_container_cleanup():
    """Test proper container cleanup"""
    manager = DeploymentManager()
    
    # Should not raise exceptions
    manager.cleanup_container("test-container")
```

#### 3.2.2 Deployment Process Tests
```python
def test_deploy_iteration_success():
    """Test successful iteration deployment"""
    manager = DeploymentManager()
    
    iteration_path = Path("/tmp/test-iteration")
    result = manager.deploy_iteration(iteration_path, port=8001)
    
    assert result.success is True
    assert result.container_id is not None
    assert result.health_check_url is not None
```

---

## 4. Integration Testing

### 4.1 Full Workflow Tests

#### 4.1.1 Generate → Clean → Deploy → Verify
```python
def test_complete_coval_workflow():
    """Test the complete COVAL workflow end-to-end"""
    
    # 1. Generate code
    engine = GenerationEngine()
    result = engine.generate(
        description="Create a FastAPI app with health endpoint",
        framework="fastapi",
        features=["health-check"]
    )
    
    assert result.success
    assert len(result.files) > 0
    
    # 2. Verify cleaning
    for file_content in result.files.values():
        assert "<<<<<<< HEAD" not in file_content
        assert "=======" not in file_content
        assert ">>>>>>> branch" not in file_content
    
    # 3. Deploy
    manager = DeploymentManager()
    deployment = manager.deploy_iteration(result.iteration_path)
    
    assert deployment.success
    assert deployment.container_id is not None
    
    # 4. Verify health
    health_ok = manager.check_health(
        deployment.container_id, 
        deployment.health_check_url
    )
    assert health_ok is True

def test_model_fallback_integration():
    """Test model fallback when primary model fails"""
    engine = GenerationEngine()
    
    # Test with non-existent model, should fallback
    result = engine.generate(
        description="Simple API",
        model="nonexistent-model"
    )
    
    assert result.success  # Should succeed with fallback
    assert result.model_used != "nonexistent-model"
```

### 4.2 Docker Integration Tests

#### 4.2.1 Container Lifecycle
```python
def test_container_lifecycle_management():
    """Test complete container lifecycle"""
    manager = DeploymentManager()
    
    # Create
    container = manager.create_container("test-lifecycle", {
        "image": "python:3.11-slim",
        "ports": {"8000/tcp": 8001}
    })
    
    # Start
    manager.start_container(container.id)
    
    # Health check
    time.sleep(2)  # Wait for startup
    health = manager.check_health(container.id, "http://localhost:8001/health")
    
    # Cleanup
    manager.cleanup_container(container.id)
    
    # Verify cleanup
    assert not manager.container_exists(container.id)
```

---

## 5. Validation Criteria

### 5.1 Code Quality Metrics

#### 5.1.1 Generated Code Quality
- **No merge conflict markers**: `<<<<<<< HEAD`, `=======`, `>>>>>>> branch`
- **No template placeholders**: `{{variable}}`, `[TODO]`, `FIXME`
- **Valid Python syntax**: All generated files must pass `python -m py_compile`
- **PEP 8 compliance**: Code formatting according to Python standards
- **Security compliance**: No hardcoded secrets or passwords

#### 5.1.2 FastAPI App Requirements
```python
# Required endpoints for generated FastAPI apps
REQUIRED_ENDPOINTS = [
    "/health",           # Health check endpoint
    "/docs",            # Swagger documentation
    "/redoc",           # ReDoc documentation
]

# Authentication requirements
AUTH_REQUIREMENTS = [
    "JWT token support",
    "Password hashing with bcrypt/passlib",
    "User registration endpoint",
    "User login endpoint",
    "Token validation middleware"
]
```

### 5.2 Deployment Validation

#### 5.2.1 Docker Container Requirements
- **Container starts successfully**: No startup errors
- **Health endpoint responds**: `/health` returns 200 OK within 30 seconds
- **Port mapping works**: External port accessibility verified
- **Environment variables**: Proper configuration injection
- **Log output**: Container logs show successful startup

#### 5.2.2 Performance Criteria
```python
PERFORMANCE_REQUIREMENTS = {
    "startup_time": 30,      # seconds max
    "response_time": 1000,   # milliseconds max for /health
    "memory_usage": 512,     # MB max container memory
    "cpu_usage": 50,         # % max CPU during startup
}
```

### 5.3 Model Validation

#### 5.3.1 Multi-Model Support
```python
def test_all_supported_models():
    """Validate all configured models work correctly"""
    models = ["qwen", "deepseek", "deepseek-r1", "codellama13b", "granite", "mistral"]
    
    for model in models:
        engine = GenerationEngine(model=model)
        result = engine.generate("Create a simple function")
        assert result.success, f"Model {model} failed to generate code"
        assert result.model_used == model or result.fallback_used, f"Model {model} mapping failed"

def test_model_fallback_chain():
    """Test the fallback chain when models are unavailable"""
    engine = GenerationEngine(model="nonexistent")
    result = engine.generate("Create a simple function")
    
    assert result.success  # Should succeed with fallback
    assert result.fallback_used is True
    assert result.model_used in ["qwen", "deepseek", "mistral"]  # Known working models
```

---

## 6. CI/CD Pipeline

### 6.1 GitHub Actions Workflow

#### 6.1.1 Test Pipeline
```yaml
name: COVAL Validation
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v3
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest pytest-cov
      
      - name: Run unit tests
        run: |
          pytest tests/unit/ -v --cov=coval --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  integration-tests:
    runs-on: ubuntu-latest
    services:
      docker:
        image: docker:dind
        options: --privileged
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v3
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest
      
      - name: Run integration tests
        run: |
          pytest tests/integration/ -v

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v3
        with:
          python-version: '3.11'
      
      - name: Install Ollama
        run: |
          curl -fsSL https://ollama.ai/install.sh | sh
          ollama pull qwen2.5-coder:7b
      
      - name: Run E2E tests
        run: |
          pytest tests/e2e/ -v
```

### 6.2 Quality Gates

#### 6.2.1 Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
  
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
  
  - repo: local
    hooks:
      - id: pytest-unit
        name: pytest-unit
        entry: pytest tests/unit/
        language: system
        pass_filenames: false
```

#### 6.2.2 Coverage Requirements
```python
# pytest.ini
[tool:pytest]
addopts = --cov=coval --cov-report=html --cov-report=term --cov-fail-under=80
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

---

## 7. Test Automation

### 7.1 Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── unit/                    # Unit tests (75%)
│   ├── __init__.py
│   ├── test_generation_engine.py
│   ├── test_deployment_manager.py
│   ├── test_model_selection.py
│   └── test_content_cleaning.py
├── integration/             # Integration tests (20%)
│   ├── __init__.py
│   ├── test_full_workflow.py
│   ├── test_docker_integration.py
│   └── test_model_fallback.py
└── e2e/                     # End-to-end tests (5%)
    ├── __init__.py
    ├── test_cli_commands.py
    └── test_real_deployment.py
```

### 7.2 Test Fixtures

#### 7.2.1 Common Fixtures
```python
# conftest.py
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock

@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def mock_llm_response():
    """Mock LLM response for testing"""
    return {
        "files": {
            "main.py": """
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "healthy"}
""",
            "requirements.txt": "fastapi==0.110.0\nuvicorn==0.27.0"
        }
    }

@pytest.fixture
def mock_docker_client():
    """Mock Docker client for testing"""
    mock_client = Mock()
    mock_container = Mock()
    mock_container.id = "test-container-123"
    mock_container.status = "running"
    mock_client.containers.create.return_value = mock_container
    return mock_client
```

### 7.3 Automated Test Scripts

#### 7.3.1 Run All Tests Script
```bash
#!/bin/bash
# scripts/run_tests.sh

set -e

echo "🧪 Running COVAL Test Suite"
echo "=========================="

# Unit tests
echo "📝 Running unit tests..."
python -m pytest tests/unit/ -v --cov=coval --cov-report=term-missing

# Integration tests
echo "🔗 Running integration tests..."
python -m pytest tests/integration/ -v

# E2E tests (if Ollama available)
if command -v ollama &> /dev/null; then
    echo "🌐 Running E2E tests..."
    python -m pytest tests/e2e/ -v
else
    echo "⚠️  Skipping E2E tests (Ollama not available)"
fi

echo "✅ All tests completed!"
```

---

## 8. Quality Gates

### 8.1 Minimum Requirements

#### 8.1.1 Code Coverage
- **Unit test coverage**: ≥ 80%
- **Integration coverage**: ≥ 60%
- **Critical path coverage**: 100% (generation, deployment, cleanup)

#### 8.1.2 Performance Benchmarks
```python
# Performance test requirements
BENCHMARK_REQUIREMENTS = {
    "generation_time": {
        "simple_app": 30,     # seconds max
        "complex_app": 120,   # seconds max
    },
    "deployment_time": {
        "container_start": 30,  # seconds max
        "health_check": 10,     # seconds max
    },
    "memory_usage": {
        "generation": 1024,     # MB max
        "deployment": 512,      # MB max per container
    }
}
```

### 8.2 Release Criteria

#### 8.2.1 Must Pass Before Release
- [ ] All unit tests pass (100%)
- [ ] All integration tests pass (100%)
- [ ] Code coverage ≥ 80%
- [ ] All supported models tested
- [ ] Docker deployment successful
- [ ] No merge conflict markers in generated code
- [ ] Health checks pass for all generated apps
- [ ] Documentation updated
- [ ] Security scan passed

#### 8.2.2 Quality Metrics Dashboard
```python
# Example metrics tracking
QUALITY_METRICS = {
    "test_success_rate": 100,        # % of tests passing
    "code_coverage": 85,             # % code coverage
    "deployment_success_rate": 95,   # % successful deployments
    "model_availability": 90,        # % models responding
    "avg_generation_time": 45,       # seconds average
    "avg_deployment_time": 25,       # seconds average
}
```

### 8.3 Monitoring and Alerting

#### 8.3.1 Health Monitoring
- **Model availability**: Check all configured models every hour
- **Docker daemon**: Verify Docker service is running
- **Generated app health**: Monitor deployed containers
- **Test suite status**: Run regression tests nightly

#### 8.3.2 Alert Conditions
- Model fallback rate > 20%
- Deployment failure rate > 10%
- Test failure rate > 5%
- Average generation time > 60 seconds
- Container startup time > 45 seconds

---

## Summary

This validation framework ensures COVAL maintains high quality and reliability through:

- **Comprehensive testing** at unit, integration, and E2E levels
- **Automated quality gates** preventing regression
- **Performance monitoring** maintaining acceptable response times
- **Multi-model validation** ensuring fallback strategies work
- **Docker integration testing** verifying deployment success
- **Continuous monitoring** of system health

Follow these guidelines to maintain COVAL's production readiness and ensure all generated applications meet deployment standards.
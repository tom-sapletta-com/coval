# COVAL Makefile - Comprehensive Development Automation
# Author: Tom Sapletta
# Description: Automates testing, building, version management, and publishing

# Project configuration
PROJECT_NAME := coval
PYTHON := python3
PIP := pip
VENV_DIR := venv
DOCKER_IMAGE := $(PROJECT_NAME)
DOCKER_REGISTRY := your-registry.com  # Change this to your registry
CURRENT_VERSION := $(shell grep "version=" setup.py | sed 's/.*version="\([^"]*\)".*/\1/')
BRANCH := $(shell git rev-parse --abbrev-ref HEAD)

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

# Default target
.PHONY: help
help: ## Show this help message
	@echo "$(BLUE)COVAL Development Makefile$(NC)"
	@echo "$(YELLOW)Available targets:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# === ENVIRONMENT SETUP ===
.PHONY: venv
venv: ## Create virtual environment
	@echo "$(BLUE)Creating virtual environment...$(NC)"
	$(PYTHON) -m venv $(VENV_DIR)
	@echo "$(GREEN)Virtual environment created. Activate with: source $(VENV_DIR)/bin/activate$(NC)"

.PHONY: install
install: ## Install project dependencies
	@echo "$(BLUE)Installing dependencies...$(NC)"
	$(PIP) install -r requirements.txt
	$(PIP) install -e .
	@echo "$(GREEN)Dependencies installed successfully$(NC)"

.PHONY: install-dev
install-dev: ## Install development dependencies
	@echo "$(BLUE)Installing development dependencies...$(NC)"
	$(PIP) install -r requirements.txt
	$(PIP) install -e ".[dev]"
	@echo "$(GREEN)Development dependencies installed$(NC)"

.PHONY: install-docs
install-docs: ## Install documentation dependencies
	@echo "$(BLUE)Installing documentation dependencies...$(NC)"
	$(PIP) install -e ".[docs]"
	@echo "$(GREEN)Documentation dependencies installed$(NC)"

.PHONY: setup
setup: venv install-dev ## Complete development environment setup
	@echo "$(GREEN)Development environment setup complete!$(NC)"

# === TESTING ===
.PHONY: test
test: ## Run all tests
	@echo "$(BLUE)Running tests...$(NC)"
	pytest tests/ -v --cov=$(PROJECT_NAME) --cov-report=html --cov-report=term

.PHONY: test-fast
test-fast: ## Run tests without coverage
	@echo "$(BLUE)Running fast tests...$(NC)"
	pytest tests/ -v -x

.PHONY: test-integration
test-integration: ## Run integration tests
	@echo "$(BLUE)Running integration tests...$(NC)"
	pytest tests/integration/ -v

.PHONY: test-unit
test-unit: ## Run unit tests only
	@echo "$(BLUE)Running unit tests...$(NC)"
	pytest tests/unit/ -v

# === CODE QUALITY ===
.PHONY: lint
lint: ## Run all linting tools
	@echo "$(BLUE)Running linting tools...$(NC)"
	black --check $(PROJECT_NAME)/ tests/
	flake8 $(PROJECT_NAME)/ tests/
	mypy $(PROJECT_NAME)/

.PHONY: format
format: ## Format code with black
	@echo "$(BLUE)Formatting code...$(NC)"
	black $(PROJECT_NAME)/ tests/
	@echo "$(GREEN)Code formatted$(NC)"

.PHONY: check
check: lint test ## Run all checks (lint + test)
	@echo "$(GREEN)All checks passed!$(NC)"

# === VERSION MANAGEMENT ===
.PHONY: version
version: ## Show current version
	@echo "$(BLUE)Current version: $(YELLOW)$(CURRENT_VERSION)$(NC)"
	@echo "$(BLUE)Current branch: $(YELLOW)$(BRANCH)$(NC)"

.PHONY: version-patch
version-patch: ## Increment patch version (x.y.Z+1)
	@echo "$(BLUE)Incrementing patch version...$(NC)"
	$(eval NEW_VERSION := $(shell echo $(CURRENT_VERSION) | awk -F. '{$$3++; print $$1"."$$2"."$$3}'))
	@$(MAKE) _update-version NEW_VERSION=$(NEW_VERSION)

.PHONY: version-minor
version-minor: ## Increment minor version (x.Y+1.0)
	@echo "$(BLUE)Incrementing minor version...$(NC)"
	$(eval NEW_VERSION := $(shell echo $(CURRENT_VERSION) | awk -F. '{$$2++; $$3=0; print $$1"."$$2"."$$3}'))
	@$(MAKE) _update-version NEW_VERSION=$(NEW_VERSION)

.PHONY: version-major
version-major: ## Increment major version (X+1.0.0)
	@echo "$(BLUE)Incrementing major version...$(NC)"
	$(eval NEW_VERSION := $(shell echo $(CURRENT_VERSION) | awk -F. '{$$1++; $$2=0; $$3=0; print $$1"."$$2"."$$3}'))
	@$(MAKE) _update-version NEW_VERSION=$(NEW_VERSION)

.PHONY: _update-version
_update-version:
	@sed -i 's/version="[^"]*"/version="$(NEW_VERSION)"/' setup.py
	@sed -i 's/__version__ = "[^"]*"/__version__ = "$(NEW_VERSION)"/' $(PROJECT_NAME)/__init__.py
	@git add setup.py $(PROJECT_NAME)/__init__.py
	@git commit -m "Bump version to $(NEW_VERSION)"
	@git tag -a "v$(NEW_VERSION)" -m "Release version $(NEW_VERSION)"
	@echo "$(GREEN)Version updated to $(NEW_VERSION) and tagged$(NC)"

# === BUILDING ===
.PHONY: clean
clean: ## Clean build artifacts
	@echo "$(BLUE)Cleaning build artifacts...$(NC)"
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	find . -type f -name "*.pyc" -delete
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)Clean complete$(NC)"

.PHONY: build
build: clean ## Build Python package
	@echo "$(BLUE)Building Python package...$(NC)"
	$(PYTHON) -m build
	@echo "$(GREEN)Package built successfully$(NC)"

.PHONY: build-wheel
build-wheel: clean ## Build wheel package only
	@echo "$(BLUE)Building wheel package...$(NC)"
	$(PYTHON) -m build --wheel
	@echo "$(GREEN)Wheel package built$(NC)"

.PHONY: build-sdist
build-sdist: clean ## Build source distribution only
	@echo "$(BLUE)Building source distribution...$(NC)"
	$(PYTHON) -m build --sdist
	@echo "$(GREEN)Source distribution built$(NC)"

# === DOCKER ===
.PHONY: docker-build
docker-build: ## Build Docker image
	@echo "$(BLUE)Building Docker image...$(NC)"
	docker build -t $(DOCKER_IMAGE):$(CURRENT_VERSION) .
	docker tag $(DOCKER_IMAGE):$(CURRENT_VERSION) $(DOCKER_IMAGE):latest
	@echo "$(GREEN)Docker image built: $(DOCKER_IMAGE):$(CURRENT_VERSION)$(NC)"

.PHONY: docker-run
docker-run: ## Run Docker container
	@echo "$(BLUE)Running Docker container...$(NC)"
	docker run -it --rm -p 8000:8000 $(DOCKER_IMAGE):latest

.PHONY: docker-push
docker-push: docker-build ## Push Docker image to registry
	@echo "$(BLUE)Pushing Docker image to registry...$(NC)"
	docker tag $(DOCKER_IMAGE):$(CURRENT_VERSION) $(DOCKER_REGISTRY)/$(DOCKER_IMAGE):$(CURRENT_VERSION)
	docker tag $(DOCKER_IMAGE):$(CURRENT_VERSION) $(DOCKER_REGISTRY)/$(DOCKER_IMAGE):latest
	docker push $(DOCKER_REGISTRY)/$(DOCKER_IMAGE):$(CURRENT_VERSION)
	docker push $(DOCKER_REGISTRY)/$(DOCKER_IMAGE):latest
	@echo "$(GREEN)Docker image pushed$(NC)"

.PHONY: docker-clean
docker-clean: ## Clean Docker images and containers
	@echo "$(BLUE)Cleaning Docker artifacts...$(NC)"
	docker system prune -f
	docker image prune -f
	@echo "$(GREEN)Docker cleanup complete$(NC)"

# === PUBLISHING ===
.PHONY: publish-test
publish-test: build ## Publish to TestPyPI
	@echo "$(BLUE)Publishing to TestPyPI...$(NC)"
	$(PYTHON) -m twine upload --repository testpypi dist/*
	@echo "$(GREEN)Published to TestPyPI$(NC)"

.PHONY: publish-pypi
publish-pypi: build ## Publish to PyPI
	@echo "$(BLUE)Publishing to PyPI...$(NC)"
	$(PYTHON) -m twine upload dist/*
	@echo "$(GREEN)Published to PyPI$(NC)"

.PHONY: publish-docker
publish-docker: docker-push ## Alias for docker-push

.PHONY: publish
publish: publish-pypi ## Publish to PyPI (default publish target)

# === DEVELOPMENT ===
.PHONY: run
run: ## Run the application locally
	@echo "$(BLUE)Running COVAL locally...$(NC)"
	$(PYTHON) -m $(PROJECT_NAME).cli --help

.PHONY: run-generate
run-generate: ## Run COVAL generate command example
	@echo "$(BLUE)Running COVAL generate example...$(NC)"
	coval generate -d "Create a simple FastAPI app" --deploy

.PHONY: run-repair
run-repair: ## Run COVAL repair command example
	@echo "$(BLUE)Running COVAL repair example...$(NC)"
	coval repair -e logs/error.log --analyze

.PHONY: logs
logs: ## Show application logs
	@echo "$(BLUE)Showing logs...$(NC)"
	tail -f logs/*.log 2>/dev/null || echo "No log files found"

.PHONY: status
status: ## Show project status
	@echo "$(BLUE)COVAL Project Status:$(NC)"
	@echo "Version: $(YELLOW)$(CURRENT_VERSION)$(NC)"
	@echo "Branch: $(YELLOW)$(BRANCH)$(NC)"
	@echo "Python: $(YELLOW)$(shell $(PYTHON) --version)$(NC)"
	@echo "Virtual env: $(YELLOW)$(VIRTUAL_ENV)$(NC)"
	@git status --short

# === CI/CD AUTOMATION ===
.PHONY: ci
ci: install-dev check build ## Complete CI pipeline
	@echo "$(GREEN)CI pipeline completed successfully!$(NC)"

.PHONY: release-patch
release-patch: check version-patch build publish-pypi docker-push ## Release patch version
	@echo "$(GREEN)Patch release completed!$(NC)"

.PHONY: release-minor
release-minor: check version-minor build publish-pypi docker-push ## Release minor version
	@echo "$(GREEN)Minor release completed!$(NC)"

.PHONY: release-major  
release-major: check version-major build publish-pypi docker-push ## Release major version
	@echo "$(GREEN)Major release completed!$(NC)"

# === MAINTENANCE ===
.PHONY: update-deps
update-deps: ## Update all dependencies
	@echo "$(BLUE)Updating dependencies...$(NC)"
	$(PIP) list --outdated --format=freeze | grep -v '^\-e' | cut -d = -f 1 | xargs -n1 $(PIP) install -U
	$(PIP) freeze > requirements.txt
	@echo "$(GREEN)Dependencies updated$(NC)"

.PHONY: security-check
security-check: ## Run security checks
	@echo "$(BLUE)Running security checks...$(NC)"
	$(PIP) install safety bandit
	safety check
	bandit -r $(PROJECT_NAME)/
	@echo "$(GREEN)Security checks completed$(NC)"

.PHONY: cleanup-iterations
cleanup-iterations: ## Clean old COVAL iterations
	@echo "$(BLUE)Cleaning old iterations...$(NC)"
	coval cleanup -c 10 --force
	@echo "$(GREEN)Old iterations cleaned$(NC)"

.PHONY: backup
backup: ## Create project backup
	@echo "$(BLUE)Creating backup...$(NC)"
	tar -czf backup-$(PROJECT_NAME)-$(shell date +%Y%m%d-%H%M%S).tar.gz \
		--exclude=venv \
		--exclude=.git \
		--exclude=__pycache__ \
		--exclude=.pytest_cache \
		--exclude=htmlcov \
		--exclude=build \
		--exclude=dist \
		--exclude=*.egg-info \
		.
	@echo "$(GREEN)Backup created$(NC)"

# === ALL-IN-ONE TARGETS ===
.PHONY: dev-setup
dev-setup: setup install-dev ## Complete development setup
	@echo "$(GREEN)Development environment ready!$(NC)"

.PHONY: quick-test
quick-test: format test-fast ## Quick development test cycle

.PHONY: full-check
full-check: format lint test security-check ## Complete code quality check

.PHONY: deploy-local
deploy-local: build docker-build docker-run ## Build and deploy locally

# Make sure we have required tools
.PHONY: check-tools
check-tools: ## Check if required tools are installed
	@echo "$(BLUE)Checking required tools...$(NC)"
	@command -v $(PYTHON) >/dev/null 2>&1 || { echo "$(RED)Python not found$(NC)"; exit 1; }
	@command -v git >/dev/null 2>&1 || { echo "$(RED)Git not found$(NC)"; exit 1; }
	@command -v docker >/dev/null 2>&1 || { echo "$(RED)Docker not found$(NC)"; exit 1; }
	@echo "$(GREEN)All required tools are available$(NC)"

# Include check-tools as prerequisite for key targets
install: check-tools
build: check-tools
docker-build: check-tools

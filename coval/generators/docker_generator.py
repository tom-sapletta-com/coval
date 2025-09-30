#!/usr/bin/env python3
"""
COVAL Docker Generator

Handles generation of Dockerfile and docker-compose.yml files.
Extracted from generation_engine.py for better modularity and testability.
"""

import logging
from typing import Dict, Optional
from ..models.generation_models import GenerationRequest

logger = logging.getLogger(__name__)


class DockerGenerator:
    """
    Generates Docker configuration files for applications.
    
    Features:
    - Language-specific Dockerfile generation
    - Framework-optimized configurations
    - Multi-service docker-compose setups
    - Production-ready security practices
    """
    
    def __init__(self):
        """Initialize the Docker generator."""
        self.setup_templates()
    
    def setup_templates(self):
        """Setup Docker templates for different languages and frameworks."""
        self.dockerfile_templates = {
            'python': {
                'base_image': 'python:3.11-slim',
                'package_manager': 'pip',
                'requirements_file': 'requirements.txt',
                'default_port': 8000
            },
            'javascript': {
                'base_image': 'node:18-alpine',
                'package_manager': 'npm',
                'requirements_file': 'package.json',
                'default_port': 3000
            },
            'typescript': {
                'base_image': 'node:18-alpine',
                'package_manager': 'npm',
                'requirements_file': 'package.json',
                'default_port': 3000
            }
        }
        
        self.framework_configs = {
            'fastapi': {
                'port': 8000,
                'start_command': ['uvicorn', 'main:app', '--host', '0.0.0.0', '--port', '8000'],
                'health_endpoint': '/health'
            },
            'flask': {
                'port': 5000,
                'start_command': ['python', 'app.py'],
                'health_endpoint': '/health'
            },
            'express': {
                'port': 3000,
                'start_command': ['node', 'index.js'],
                'health_endpoint': '/health'
            }
        }
    
    def generate_dockerfile(self, request: GenerationRequest, files: Dict[str, str]) -> str:
        """
        Generate Dockerfile for the application.
        
        Args:
            request: Generation request with framework and language info
            files: Generated application files
            
        Returns:
            Dockerfile content as string
        """
        language = request.language.lower()
        framework = request.framework.lower()
        
        logger.debug(f"Generating Dockerfile for {language} {framework} application")
        
        if language == 'python':
            return self._generate_python_dockerfile(request, files)
        elif language in ['javascript', 'typescript']:
            return self._generate_node_dockerfile(request, files)
        else:
            return self._generate_generic_dockerfile(request, files)
    
    def _generate_python_dockerfile(self, request: GenerationRequest, files: Dict[str, str]) -> str:
        """Generate Python-specific Dockerfile."""
        framework_config = self.framework_configs.get(request.framework.lower(), {})
        port = framework_config.get('port', 8000)
        
        # Check if we have specific requirements
        has_requirements = 'requirements.txt' in files
        
        dockerfile_content = f"""FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
"""
        
        if has_requirements:
            dockerfile_content += """COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
"""
        else:
            # Default FastAPI requirements
            dockerfile_content += """RUN pip install --no-cache-dir fastapi uvicorn
"""
        
        dockerfile_content += f"""
# Copy application code
COPY . .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app \\
    && chown -R app:app /app
USER app

# Expose port
EXPOSE {port}

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:{port}/health || exit 1

# Start application
"""
        
        if request.framework.lower() == 'fastapi':
            dockerfile_content += f'CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "{port}"]'
        elif request.framework.lower() == 'flask':
            dockerfile_content += 'CMD ["python", "app.py"]'
        else:
            dockerfile_content += 'CMD ["python", "main.py"]'
        
        return dockerfile_content
    
    def _generate_node_dockerfile(self, request: GenerationRequest, files: Dict[str, str]) -> str:
        """Generate Node.js-specific Dockerfile."""
        framework_config = self.framework_configs.get(request.framework.lower(), {})
        port = framework_config.get('port', 3000)
        
        has_package_json = 'package.json' in files
        
        dockerfile_content = f"""FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package files first for better caching
"""
        
        if has_package_json:
            dockerfile_content += """COPY package*.json ./
RUN npm ci --only=production
"""
        else:
            # Default Express setup
            dockerfile_content += """RUN npm init -y && npm install express
"""
        
        dockerfile_content += f"""
# Copy application code
COPY . .

# Create non-root user for security
RUN addgroup -g 1001 -S nodejs \\
    && adduser -S nextjs -u 1001 \\
    && chown -R nextjs:nodejs /app
USER nextjs

# Expose port
EXPOSE {port}

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
    CMD wget --no-verbose --tries=1 --spider http://localhost:{port}/health || exit 1

# Start application
"""
        
        if request.framework.lower() == 'express':
            dockerfile_content += 'CMD ["node", "index.js"]'
        else:
            dockerfile_content += 'CMD ["npm", "start"]'
        
        return dockerfile_content
    
    def _generate_generic_dockerfile(self, request: GenerationRequest, files: Dict[str, str]) -> str:
        """Generate generic Dockerfile."""
        return f"""FROM ubuntu:22.04

# Install basic dependencies
RUN apt-get update && apt-get install -y \\
    curl \\
    wget \\
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy application
COPY . .

# Make start script executable
RUN chmod +x start.sh

# Expose port (default)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8080/health || exit 1

# Start application
CMD ["./start.sh"]
"""
    
    def generate_docker_compose(self, request: GenerationRequest, include_database: bool = True) -> str:
        """
        Generate docker-compose.yml for the application.
        
        Args:
            request: Generation request
            include_database: Whether to include database services
            
        Returns:
            docker-compose.yml content as string
        """
        framework_config = self.framework_configs.get(request.framework.lower(), {})
        port = framework_config.get('port', 8000)
        
        logger.debug(f"Generating docker-compose.yml for {request.framework} application")
        
        compose_content = f"""version: '3.8'

services:
  app:
    build: .
    ports:
      - "{port}:{port}"
    environment:
      - NODE_ENV=production
      - DATABASE_URL=postgresql://user:password@db:5432/appdb
    depends_on:
      - db
    restart: unless-stopped
    networks:
      - app-network
"""
        
        if include_database:
            compose_content += """
  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=appdb
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped
    networks:
      - app-network

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped
    networks:
      - app-network
"""
        
        compose_content += """
networks:
  app-network:
    driver: bridge

volumes:
  postgres_data:
"""
        
        return compose_content
    
    def generate_dockerignore(self) -> str:
        """Generate .dockerignore file."""
        return """# Version control
.git
.gitignore

# Dependencies
node_modules/
venv/
env/
.env
__pycache__/
*.pyc

# IDE files
.vscode/
.idea/
*.swp
*.swo

# OS files
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Build artifacts
dist/
build/
*.egg-info/

# Testing
.coverage
.pytest_cache/
test_results/

# Documentation
docs/
README.md
LICENSE

# Docker
Dockerfile*
docker-compose*
.dockerignore
"""
    
    def generate_start_script(self, request: GenerationRequest) -> str:
        """
        Generate start.sh script for the application.
        
        Args:
            request: Generation request
            
        Returns:
            start.sh script content
        """
        framework_config = self.framework_configs.get(request.framework.lower(), {})
        port = framework_config.get('port', 8000)
        
        if request.language.lower() == 'python':
            if request.framework.lower() == 'fastapi':
                return f"""#!/bin/bash
set -e

echo "Starting FastAPI application..."

# Run database migrations if needed
# python -m alembic upgrade head

# Start the application
exec uvicorn main:app --host 0.0.0.0 --port {port} --workers 1
"""
            elif request.framework.lower() == 'flask':
                return f"""#!/bin/bash
set -e

echo "Starting Flask application..."

# Set environment variables
export FLASK_APP=app.py
export FLASK_ENV=production

# Run database migrations if needed
# flask db upgrade

# Start the application
exec python app.py
"""
        elif request.language.lower() in ['javascript', 'typescript']:
            return f"""#!/bin/bash
set -e

echo "Starting Node.js application..."

# Install production dependencies if needed
# npm ci --only=production

# Run database migrations if needed
# npm run migrate

# Start the application
exec node index.js
"""
        
        # Generic start script
        return f"""#!/bin/bash
set -e

echo "Starting application..."

# Check if main executable exists
if [ -f "main.py" ]; then
    exec python main.py
elif [ -f "app.py" ]; then
    exec python app.py
elif [ -f "index.js" ]; then
    exec node index.js
elif [ -f "server.js" ]; then
    exec node server.js
else
    echo "No main application file found!"
    exit 1
fi
"""
    
    def generate_production_compose(self, request: GenerationRequest) -> str:
        """Generate production-ready docker-compose.yml with additional services."""
        framework_config = self.framework_configs.get(request.framework.lower(), {})
        port = framework_config.get('port', 8000)
        
        return f"""version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app
    restart: unless-stopped
    networks:
      - app-network

  app:
    build: .
    environment:
      - NODE_ENV=production
      - DATABASE_URL=postgresql://user:password@db:5432/appdb
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
    restart: unless-stopped
    networks:
      - app-network
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '0.5'
          memory: 512M

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=appdb
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    restart: unless-stopped
    networks:
      - app-network

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    restart: unless-stopped
    networks:
      - app-network

  monitoring:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    restart: unless-stopped
    networks:
      - app-network

networks:
  app-network:
    driver: bridge

volumes:
  postgres_data:
  redis_data:
"""

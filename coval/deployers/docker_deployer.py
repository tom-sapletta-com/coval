#!/usr/bin/env python3
"""
COVAL Docker Deployer

Main deployment orchestrator that uses modular components to handle Docker deployments.
Replaces the monolithic deployment_manager.py with a clean, modular architecture.
"""

import os
import logging
import tempfile
import shutil
import socket
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import docker
from docker.errors import DockerException, BuildError, APIError

from .container_manager import ContainerManager, ContainerConfig, ContainerStatus
from .health_checker import HealthChecker, HealthCheckConfig, HealthStatus, ApplicationHealth

logger = logging.getLogger(__name__)


@dataclass
class DeploymentConfig:
    """Configuration for a deployment."""
    iteration_id: str
    project_name: str
    framework: str
    language: str
    source_path: Path
    dockerfile_path: Optional[Path] = None
    compose_path: Optional[Path] = None
    base_port: int = 8000
    environment: Dict[str, str] = None
    health_check_config: Optional[HealthCheckConfig] = None


@dataclass
class DeploymentResult:
    """Result of a deployment operation."""
    success: bool
    iteration_id: str
    container_name: str
    container_id: Optional[str]
    image_name: str
    port_mappings: Dict[int, int]
    health_status: HealthStatus
    deployment_time: float
    error_message: Optional[str] = None
    logs_path: Optional[str] = None


class DockerDeployer:
    """
    Main Docker deployment orchestrator using modular components.
    
    Features:
    - Uses ContainerManager for proper container lifecycle management
    - Uses HealthChecker for comprehensive health monitoring
    - Fixes container naming conflicts and cleanup issues
    - Clean separation of concerns with modular architecture
    - Robust error handling and logging
    """
    
    def __init__(self, project_root: str = "."):
        """
        Initialize the DockerDeployer.
        
        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root).resolve()
        self.deployments_dir = self.project_root / "deployments"
        self.deployments_dir.mkdir(exist_ok=True)
        
        # Initialize modular components
        self.container_manager = ContainerManager()
        self.health_checker = HealthChecker()
        
        # Track active deployments
        self.active_deployments: Dict[str, DeploymentResult] = {}
        
        logger.debug("✓ DockerDeployer initialized with modular components")
    
    def _find_next_available_port(self, start_port: int = 8000) -> int:
        """
        Find the next available port starting from start_port, incrementing by 1.
        
        Args:
            start_port: Starting port number (default: 8000)
            
        Returns:
            int: Next available port number
        """
        current_port = start_port
        
        # Check currently used ports by active deployments
        used_ports = set()
        for deployment in self.active_deployments.values():
            for host_port in deployment.port_mappings.values():
                used_ports.add(host_port)
        
        # Check Docker containers
        try:
            docker_client = docker.from_env()
            containers = docker_client.containers.list()
            for container in containers:
                if container.ports:
                    for port_mapping in container.ports.values():
                        if port_mapping:
                            for mapping in port_mapping:
                                if mapping.get('HostPort'):
                                    used_ports.add(int(mapping['HostPort']))
        except Exception as e:
            logger.warning(f"Could not check Docker container ports: {e}")
        
        # Find next available port
        while current_port in used_ports or self._is_port_in_use(current_port):
            current_port += 1
            if current_port > 65535:  # Max port number
                raise RuntimeError("No available ports found")
        
        logger.info(f"🔌 Found next available port: {current_port}")
        return current_port
    
    def _is_port_in_use(self, port: int) -> bool:
        """
        Check if a port is currently in use on localhost.
        
        Args:
            port: Port number to check
            
        Returns:
            bool: True if port is in use, False otherwise
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(('localhost', port))
                return False
            except socket.error:
                return True
    
    def deploy(self, config: DeploymentConfig) -> DeploymentResult:
        """
        Deploy an iteration using Docker with comprehensive error handling.
        
        Args:
            config: Deployment configuration
            
        Returns:
            DeploymentResult: Result of the deployment
        """
        start_time = datetime.now()
        logger.info(f"🚀 Starting deployment for iteration: {config.iteration_id}")
        
        # Auto-increment port if base_port is 8000 (default) to avoid conflicts
        if config.base_port == 8000:
            auto_port = self._find_next_available_port(8000)
            config.base_port = auto_port
            logger.info(f"🔌 Auto-assigned port {auto_port} to avoid conflicts")
        
        # Create deployment result
        result = DeploymentResult(
            success=False,
            iteration_id=config.iteration_id,
            container_name=f"coval-{config.iteration_id}",
            container_id=None,
            image_name=f"coval-{config.iteration_id}:latest",
            port_mappings={8000: config.base_port},
            health_status=HealthStatus.UNKNOWN,
            deployment_time=0.0
        )
        
        try:
            # Step 1: Build Docker image
            logger.info("🔨 Building Docker image...")
            build_success = self._build_image(config, result)
            if not build_success:
                return result
            
            # Step 2: Create and start container
            logger.info("🐳 Creating container...")
            container_status = self._create_and_start_container(config, result)
            if not container_status or container_status.status == 'failed':
                result.error_message = f"Failed to create container: {container_status.error_message if container_status else 'Unknown error'}"
                return result
            
            result.container_id = container_status.container_id
            
            # Step 3: Wait for application to become healthy
            logger.info("🔍 Checking application health...")
            health_config = config.health_check_config or self.health_checker.get_health_config_for_framework(config.framework)
            
            is_healthy = self.health_checker.wait_for_healthy(
                host="localhost",
                port=config.base_port,
                config=health_config,
                max_wait_time=120  # 2 minutes
            )
            
            if is_healthy:
                result.health_status = HealthStatus.HEALTHY
                result.success = True
                logger.info(f"✅ Deployment successful: {config.iteration_id}")
                
                # Start continuous health monitoring
                self.health_checker.start_monitoring(
                    app_name=config.iteration_id,
                    host="localhost",
                    port=config.base_port,
                    config=health_config
                )
            else:
                result.health_status = HealthStatus.UNHEALTHY
                result.error_message = "Application failed health checks"
                logger.error(f"❌ Deployment failed - application unhealthy: {config.iteration_id}")
            
            # Track the deployment
            self.active_deployments[config.iteration_id] = result
            
        except Exception as e:
            logger.error(f"❌ Deployment failed with exception: {e}")
            result.error_message = str(e)
        
        finally:
            result.deployment_time = (datetime.now() - start_time).total_seconds()
        
        return result
    
    def stop_deployment(self, iteration_id: str) -> bool:
        """
        Stop a deployment and cleanup resources.
        
        Args:
            iteration_id: ID of the iteration to stop
            
        Returns:
            bool: True if stopped successfully, False otherwise
        """
        logger.info(f"🛑 Stopping deployment: {iteration_id}")
        
        container_name = f"coval-{iteration_id}"
        
        try:
            # Stop health monitoring
            self.health_checker.stop_monitoring(iteration_id)
            
            # Stop and remove container
            success = self.container_manager.stop_and_remove_container(container_name)
            
            # Remove from active deployments
            if iteration_id in self.active_deployments:
                del self.active_deployments[iteration_id]
            
            if success:
                logger.info(f"✅ Deployment stopped successfully: {iteration_id}")
            else:
                logger.warning(f"⚠️ Deployment stop had issues: {iteration_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Failed to stop deployment {iteration_id}: {e}")
            return False
    
    def get_deployment_status(self, iteration_id: str) -> Optional[DeploymentResult]:
        """
        Get status of a deployment.
        
        Args:
            iteration_id: ID of the iteration
            
        Returns:
            DeploymentResult or None if not found
        """
        deployment = self.active_deployments.get(iteration_id)
        
        if deployment:
            # Update with current health status
            app_health = self.health_checker.get_application_health(iteration_id)
            if app_health:
                deployment.health_status = app_health.overall_status
        
        return deployment
    
    def list_active_deployments(self) -> List[DeploymentResult]:
        """List all active deployments."""
        return list(self.active_deployments.values())
    
    def get_health_report(self, iteration_id: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive health report for a deployment.
        
        Args:
            iteration_id: ID of the iteration
            
        Returns:
            Health report dict or None if not found
        """
        return self.health_checker.generate_health_report(iteration_id)
    
    def cleanup_old_deployments(self, keep_count: int = 3) -> Dict[str, bool]:
        """
        Cleanup old deployments, keeping only the most recent ones.
        
        Args:
            keep_count: Number of deployments to keep
            
        Returns:
            Dict mapping iteration IDs to cleanup success status
        """
        logger.info(f"🧹 Cleaning up old deployments (keeping {keep_count})")
        
        # Sort deployments by deployment time (most recent first)
        sorted_deployments = sorted(
            self.active_deployments.items(),
            key=lambda x: x[1].deployment_time,
            reverse=True
        )
        
        results = {}
        
        # Keep the most recent deployments, cleanup the rest
        for i, (iteration_id, deployment) in enumerate(sorted_deployments):
            if i >= keep_count:
                results[iteration_id] = self.stop_deployment(iteration_id)
            else:
                results[iteration_id] = True  # Kept
        
        return results
    
    def _build_image(self, config: DeploymentConfig, result: DeploymentResult) -> bool:
        """
        Build Docker image for the application.
        
        Args:
            config: Deployment configuration
            result: Deployment result to update
            
        Returns:
            bool: True if built successfully, False otherwise
        """
        try:
            # Prepare build context
            build_context = self._prepare_build_context(config)
            
            # Build image
            docker_client = self.container_manager.docker_client
            
            logger.debug(f"Building image: {result.image_name}")
            image, build_logs = docker_client.images.build(
                path=str(build_context),
                tag=result.image_name,
                rm=True,  # Remove intermediate containers
                forcerm=True,  # Always remove intermediate containers
                pull=True  # Pull base image updates
            )
            
            logger.info(f"✅ Image built successfully: {result.image_name}")
            return True
            
        except BuildError as e:
            error_msg = f"Docker build failed: {e}"
            logger.error(error_msg)
            result.error_message = error_msg
            return False
        except Exception as e:
            error_msg = f"Unexpected error building image: {e}"
            logger.error(error_msg)
            result.error_message = error_msg
            return False
    
    def _prepare_build_context(self, config: DeploymentConfig) -> Path:
        """
        Prepare build context directory with all necessary files.
        
        Args:
            config: Deployment configuration
            
        Returns:
            Path: Path to the build context directory
        """
        # Create temporary build context
        build_context = self.deployments_dir / f"build-{config.iteration_id}"
        build_context.mkdir(exist_ok=True)
        
        # Copy source files
        if config.source_path.is_dir():
            # Copy entire directory
            for item in config.source_path.iterdir():
                if item.is_file():
                    shutil.copy2(item, build_context)
                elif item.is_dir() and item.name not in {'.git', '__pycache__', 'node_modules'}:
                    shutil.copytree(item, build_context / item.name, dirs_exist_ok=True)
        else:
            # Copy single file
            shutil.copy2(config.source_path, build_context)
        
        # Ensure Dockerfile exists
        dockerfile_path = build_context / "Dockerfile"
        if not dockerfile_path.exists():
            if config.dockerfile_path and config.dockerfile_path.exists():
                shutil.copy2(config.dockerfile_path, dockerfile_path)
            else:
                # Create basic Dockerfile based on framework
                self._create_default_dockerfile(config, dockerfile_path)
        
        # Create start script if needed
        start_script = build_context / "start.sh"
        if not start_script.exists():
            self._create_start_script(config, start_script)
        
        return build_context
    
    def _create_default_dockerfile(self, config: DeploymentConfig, dockerfile_path: Path):
        """Create a default Dockerfile based on the framework."""
        if config.language.lower() == 'python':
            dockerfile_content = f"""FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt* ./
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Copy application code
COPY . .

# Make start script executable
RUN chmod +x start.sh

# Expose port
EXPOSE {config.base_port}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \\
    CMD curl -f http://localhost:{config.base_port}/health || exit 1

# Run application
CMD ["./start.sh"]
"""
        else:
            dockerfile_content = f"""FROM node:18-alpine

WORKDIR /app

# Copy package files first for better caching
COPY package*.json ./
RUN npm ci --only=production

# Copy application code
COPY . .

# Make start script executable
RUN chmod +x start.sh

# Expose port
EXPOSE {config.base_port}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \\
    CMD curl -f http://localhost:{config.base_port}/health || exit 1

# Run application
CMD ["./start.sh"]
"""
        
        dockerfile_path.write_text(dockerfile_content)
        logger.debug(f"Created default Dockerfile for {config.language}")
    
    def _create_start_script(self, config: DeploymentConfig, start_script_path: Path):
        """Create a start script for the application."""
        if config.framework.lower() == 'fastapi':
            script_content = f"""#!/bin/bash
set -e

echo "Starting {config.framework} application..."

# Install dependencies if requirements.txt exists
if [ -f requirements.txt ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

# Start the application
if [ -f main.py ]; then
    echo "Starting with uvicorn..."
    uvicorn main:app --host 0.0.0.0 --port {config.base_port}
elif [ -f app.py ]; then
    echo "Starting with uvicorn..."
    uvicorn app:app --host 0.0.0.0 --port {config.base_port}
else
    echo "No main.py or app.py found, starting with python..."
    python -m uvicorn main:app --host 0.0.0.0 --port {config.base_port}
fi
"""
        elif config.framework.lower() == 'flask':
            script_content = f"""#!/bin/bash
set -e

echo "Starting {config.framework} application..."

# Install dependencies if requirements.txt exists
if [ -f requirements.txt ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

# Start the application
export FLASK_APP=main.py
export FLASK_RUN_HOST=0.0.0.0
export FLASK_RUN_PORT={config.base_port}
flask run
"""
        else:
            # Generic script
            script_content = f"""#!/bin/bash
set -e

echo "Starting application..."

# Start the application based on available files
if [ -f main.py ]; then
    python main.py
elif [ -f app.py ]; then
    python app.py
elif [ -f package.json ]; then
    npm start
else
    echo "No known entry point found"
    exit 1
fi
"""
        
        start_script_path.write_text(script_content)
        start_script_path.chmod(0o755)
        logger.debug(f"Created start script for {config.framework}")
    
    def _create_and_start_container(self, config: DeploymentConfig, result: DeploymentResult) -> Optional[ContainerStatus]:
        """
        Create and start container using ContainerManager.
        
        Args:
            config: Deployment configuration
            result: Deployment result to update
            
        Returns:
            ContainerStatus or None if failed
        """
        container_config = ContainerConfig(
            name=result.container_name,
            image=result.image_name,
            ports={f"{config.base_port}/tcp": config.base_port},
            volumes={},  # Using build context, no volume mounts needed
            environment=config.environment or {},
            restart_policy={"Name": "unless-stopped"}
        )
        
        # Create container
        container_status = self.container_manager.create_container(container_config)
        
        if container_status.status == 'failed':
            return container_status
        
        # Start container
        success = self.container_manager.start_container(result.container_name)
        
        if not success:
            container_status.status = 'failed'
            container_status.error_message = "Failed to start container"
        
        return container_status

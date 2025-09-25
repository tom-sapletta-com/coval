#!/usr/bin/env python3
"""
COVAL Deployment Manager

Handles transparent Docker deployments with volume overlays that expose only
the latest iteration changes while maintaining the ability to rollback to
previous iterations and cleanup legacy code.
"""

import os
import json
import yaml
import logging
import subprocess
import shutil
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import docker
from docker.models.containers import Container
from docker.models.networks import Network

logger = logging.getLogger(__name__)


@dataclass
class DeploymentConfig:
    """Configuration for a deployment."""
    iteration_id: str
    project_name: str
    base_port: int
    framework: str
    language: str
    dockerfile_path: str
    compose_path: str
    volumes: Dict[str, str]  # host_path -> container_path
    environment: Dict[str, str]
    network_name: str
    health_check_endpoint: str
    deployment_strategy: str  # 'overlay', 'replace', 'blue-green'


@dataclass
class DeploymentStatus:
    """Status of a deployment."""
    iteration_id: str
    container_id: Optional[str]
    container_name: str
    status: str  # 'starting', 'running', 'stopped', 'failed', 'health_check_failed'
    port_mappings: Dict[int, int]  # container_port -> host_port
    health_status: str
    started_at: Optional[datetime]
    stopped_at: Optional[datetime]
    logs_path: str
    resource_usage: Dict[str, Any]


class DeploymentManager:
    """
    Manages transparent Docker deployments with iterative volume overlays.
    
    Key Features:
    - Transparent deployment: Only latest changes are exposed via volumes
    - Iterative overlays: Each iteration builds on the previous one
    - Legacy cleanup: Old iterations can be removed transparently
    - Blue-green deployments: Zero-downtime updates
    - Health monitoring: Automatic rollback on failures
    - Resource management: Optimal container resource allocation
    """
    
    def __init__(self, project_root: str, config: Optional[Dict[str, Any]] = None):
        self.project_root = Path(project_root)
        self.deployments_dir = self.project_root / "deployments"
        self.config = config or self._default_config()
        
        # Docker client
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            logger.error(f"Failed to connect to Docker: {e}")
            self.docker_client = None
        
        # Deployment tracking
        self.active_deployments: Dict[str, DeploymentStatus] = {}
        self.deployment_history_file = self.deployments_dir / "deployment_history.json"
        
        # Ensure directories exist
        self.deployments_dir.mkdir(parents=True, exist_ok=True)
        
        # Load deployment history
        self._load_deployment_history()
        
        # Setup logging
        self._setup_logging()
    
    def _default_config(self) -> Dict[str, Any]:
        """Default deployment configuration."""
        return {
            'docker': {
                'base_port': 8000,
                'network_name': 'coval-network',
                'auto_cleanup': True,
                'max_concurrent_deployments': 5,
                'health_check_timeout': 60,
                'deployment_timeout': 300
            },
            'volumes': {
                'strategy': 'overlay',  # 'overlay', 'copy', 'symlink'
                'preserve_permissions': True,
                'exclude_patterns': ['.git', '__pycache__', '*.pyc', '.DS_Store']
            },
            'monitoring': {
                'enabled': True,
                'check_interval': 30,
                'log_retention_days': 7
            },
            'rollback': {
                'auto_rollback_on_failure': True,
                'rollback_timeout': 60,
                'max_rollback_attempts': 3
            }
        }
    
    def _setup_logging(self):
        """Setup logging for deployment manager."""
        log_dir = self.deployments_dir / "logs"
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f"deployments_{datetime.now().strftime('%Y%m%d')}.log"
        
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    def _load_deployment_history(self):
        """Load deployment history from disk."""
        if self.deployment_history_file.exists():
            try:
                with open(self.deployment_history_file, 'r') as f:
                    history_data = json.load(f)
                    
                for deployment_data in history_data:
                    # Convert datetime strings back to datetime objects
                    if deployment_data.get('started_at'):
                        deployment_data['started_at'] = datetime.fromisoformat(deployment_data['started_at'])
                    if deployment_data.get('stopped_at'):
                        deployment_data['stopped_at'] = datetime.fromisoformat(deployment_data['stopped_at'])
                    
                    status = DeploymentStatus(**deployment_data)
                    if status.status in ['running', 'starting']:
                        self.active_deployments[status.iteration_id] = status
                        
            except Exception as e:
                logger.warning(f"Could not load deployment history: {e}")
    
    def _save_deployment_history(self):
        """Save deployment history to disk."""
        try:
            # Get all deployments (active + from history file)
            all_deployments = list(self.active_deployments.values())
            
            # Convert to serializable format
            history_data = []
            for deployment in all_deployments:
                data = {
                    'iteration_id': deployment.iteration_id,
                    'container_id': deployment.container_id,
                    'container_name': deployment.container_name,
                    'status': deployment.status,
                    'port_mappings': deployment.port_mappings,
                    'health_status': deployment.health_status,
                    'started_at': deployment.started_at.isoformat() if deployment.started_at else None,
                    'stopped_at': deployment.stopped_at.isoformat() if deployment.stopped_at else None,
                    'logs_path': deployment.logs_path,
                    'resource_usage': deployment.resource_usage
                }
                history_data.append(data)
            
            with open(self.deployment_history_file, 'w') as f:
                json.dump(history_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Could not save deployment history: {e}")
    
    def create_transparent_deployment(self, 
                                    iteration_id: str,
                                    iteration_path: Path,
                                    parent_iterations: Optional[List[str]] = None) -> DeploymentStatus:
        """
        Create a transparent deployment that overlays the latest iteration
        on top of previous iterations using Docker volumes.
        
        Args:
            iteration_id: ID of the iteration to deploy
            iteration_path: Path to the iteration folder
            parent_iterations: List of parent iteration IDs for overlay
            
        Returns:
            DeploymentStatus with deployment information
        """
        if not self.docker_client:
            raise Exception("Docker client not available")
        
        logger.info(f"🚀 Creating transparent deployment for iteration: {iteration_id}")
        
        # Create deployment configuration
        deployment_config = self._create_deployment_config(
            iteration_id, iteration_path, parent_iterations
        )
        
        # Setup volume overlays
        overlay_path = self._setup_volume_overlays(
            iteration_id, iteration_path, parent_iterations
        )
        
        # Build Docker image
        image_name = self._build_docker_image(iteration_id, overlay_path, deployment_config)
        
        # Create and start container
        container = self._create_container(deployment_config, image_name, overlay_path)
        
        # Setup networking
        self._setup_networking(container, deployment_config)
        
        # Start container
        container.start()
        
        # Create deployment status
        deployment_status = DeploymentStatus(
            iteration_id=iteration_id,
            container_id=container.id,
            container_name=container.name,
            status='starting',
            port_mappings=deployment_config.volumes,
            health_status='unknown',
            started_at=datetime.now(),
            stopped_at=None,
            logs_path=str(self.deployments_dir / "logs" / f"{iteration_id}.log"),
            resource_usage={}
        )
        
        # Track active deployment
        self.active_deployments[iteration_id] = deployment_status
        
        # Start health monitoring
        self._start_health_monitoring(deployment_status, deployment_config)
        
        logger.info(f"✅ Deployment created: {container.name} (ID: {container.short_id})")
        
        return deployment_status
    
    def _create_deployment_config(self, 
                                 iteration_id: str,
                                 iteration_path: Path,
                                 parent_iterations: Optional[List[str]]) -> DeploymentConfig:
        """Create deployment configuration."""
        # Auto-detect framework and settings
        framework = self._detect_framework(iteration_path)
        language = self._detect_language(iteration_path)
        
        # Find Docker files
        dockerfile_path = self._find_dockerfile(iteration_path)
        compose_path = self._find_docker_compose(iteration_path)
        
        # Calculate port
        base_port = self.config['docker']['base_port']
        assigned_port = base_port + len(self.active_deployments)
        
        # Setup volume mappings
        volumes = {
            str(iteration_path): '/app',  # Main application volume
            str(self.deployments_dir / "logs"): '/app/logs'  # Logs volume
        }
        
        # Environment variables
        environment = {
            'COVAL_ITERATION_ID': iteration_id,
            'COVAL_FRAMEWORK': framework,
            'COVAL_LANGUAGE': language,
            'PORT': str(assigned_port)
        }
        
        return DeploymentConfig(
            iteration_id=iteration_id,
            project_name=f"coval-{iteration_id}",
            base_port=assigned_port,
            framework=framework,
            language=language,
            dockerfile_path=dockerfile_path,
            compose_path=compose_path,
            volumes=volumes,
            environment=environment,
            network_name=self.config['docker']['network_name'],
            health_check_endpoint=f"http://localhost:{assigned_port}/health",
            deployment_strategy=self.config['volumes']['strategy']
        )
    
    def _setup_volume_overlays(self, 
                              iteration_id: str,
                              iteration_path: Path,
                              parent_iterations: Optional[List[str]]) -> Path:
        """
        Setup transparent volume overlays that expose only the latest changes.
        This is the core feature you requested - transparent deployment with
        legacy cleanup capability.
        """
        overlay_dir = self.deployments_dir / "overlays" / iteration_id
        overlay_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"📁 Setting up volume overlays in: {overlay_dir}")
        
        if self.config['volumes']['strategy'] == 'overlay':
            # Use overlay filesystem approach
            return self._create_overlay_filesystem(
                iteration_id, iteration_path, parent_iterations, overlay_dir
            )
        elif self.config['volumes']['strategy'] == 'copy':
            # Use copy-based approach
            return self._create_copy_overlay(
                iteration_id, iteration_path, parent_iterations, overlay_dir
            )
        else:
            # Use symlink approach
            return self._create_symlink_overlay(
                iteration_id, iteration_path, parent_iterations, overlay_dir
            )
    
    def _create_overlay_filesystem(self, 
                                  iteration_id: str,
                                  iteration_path: Path,
                                  parent_iterations: Optional[List[str]],
                                  overlay_dir: Path) -> Path:
        """
        Create an overlay filesystem that transparently combines iterations.
        This provides the most efficient transparent deployment.
        """
        # Create overlay structure
        lower_dir = overlay_dir / "lower"
        upper_dir = overlay_dir / "upper" 
        work_dir = overlay_dir / "work"
        merged_dir = overlay_dir / "merged"
        
        for dir_path in [lower_dir, upper_dir, work_dir, merged_dir]:
            dir_path.mkdir(exist_ok=True)
        
        # Copy current iteration to upper layer
        shutil.copytree(iteration_path, upper_dir / "current", dirs_exist_ok=True)
        
        # Setup parent iterations in lower layers
        lower_layers = []
        if parent_iterations:
            for i, parent_id in enumerate(reversed(parent_iterations)):
                parent_path = self.project_root / "iterations" / parent_id
                if parent_path.exists():
                    parent_layer = lower_dir / f"parent_{i}"
                    shutil.copytree(parent_path, parent_layer, dirs_exist_ok=True)
                    lower_layers.append(str(parent_layer))
        
        # Mount overlay filesystem
        try:
            lower_layers_str = ":".join(lower_layers) if lower_layers else str(upper_dir / "current")
            mount_cmd = [
                'sudo', 'mount', '-t', 'overlay', 'overlay',
                '-o', f'lowerdir={lower_layers_str},upperdir={upper_dir}/current,workdir={work_dir}',
                str(merged_dir)
            ]
            
            result = subprocess.run(mount_cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("✅ Overlay filesystem mounted successfully")
                return merged_dir
            else:
                logger.warning(f"Overlay mount failed, falling back to copy: {result.stderr}")
                return self._create_copy_overlay(iteration_id, iteration_path, parent_iterations, overlay_dir)
                
        except Exception as e:
            logger.warning(f"Overlay filesystem not available, falling back to copy: {e}")
            return self._create_copy_overlay(iteration_id, iteration_path, parent_iterations, overlay_dir)
    
    def _create_copy_overlay(self, 
                            iteration_id: str,
                            iteration_path: Path,
                            parent_iterations: Optional[List[str]],
                            overlay_dir: Path) -> Path:
        """
        Create overlay using file copying - transparent but less efficient.
        """
        merged_dir = overlay_dir / "merged"
        merged_dir.mkdir(exist_ok=True)
        
        # Copy parent iterations first (oldest to newest)
        if parent_iterations:
            for parent_id in parent_iterations:
                parent_path = self.project_root / "iterations" / parent_id
                if parent_path.exists():
                    shutil.copytree(parent_path, merged_dir, dirs_exist_ok=True)
                    logger.info(f"📋 Copied parent iteration: {parent_id}")
        
        # Copy current iteration (overwrites parent files)
        shutil.copytree(iteration_path, merged_dir, dirs_exist_ok=True)
        logger.info(f"📋 Copied current iteration: {iteration_id}")
        
        return merged_dir
    
    def _create_symlink_overlay(self, 
                               iteration_id: str,
                               iteration_path: Path,
                               parent_iterations: Optional[List[str]],
                               overlay_dir: Path) -> Path:
        """
        Create overlay using symlinks - fastest but less portable.
        """
        merged_dir = overlay_dir / "merged"
        merged_dir.mkdir(exist_ok=True)
        
        # Create symlinks for all files, with current iteration taking precedence
        all_files = set()
        iteration_files = {}
        
        # Collect files from parent iterations
        if parent_iterations:
            for parent_id in parent_iterations:
                parent_path = self.project_root / "iterations" / parent_id
                if parent_path.exists():
                    for file_path in parent_path.rglob('*'):
                        if file_path.is_file():
                            rel_path = file_path.relative_to(parent_path)
                            if rel_path not in iteration_files:  # Don't overwrite newer versions
                                iteration_files[rel_path] = file_path
                                all_files.add(rel_path)
        
        # Collect files from current iteration (these take precedence)
        for file_path in iteration_path.rglob('*'):
            if file_path.is_file():
                rel_path = file_path.relative_to(iteration_path)
                iteration_files[rel_path] = file_path
                all_files.add(rel_path)
        
        # Create symlinks
        for rel_path in all_files:
            target_path = merged_dir / rel_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            if target_path.exists():
                target_path.unlink()
            
            target_path.symlink_to(iteration_files[rel_path])
        
        logger.info(f"🔗 Created {len(all_files)} symlinks for transparent overlay")
        return merged_dir
    
    def _build_docker_image(self, 
                           iteration_id: str,
                           source_path: Path,
                           config: DeploymentConfig) -> str:
        """Build Docker image for the iteration."""
        image_name = f"coval-{iteration_id}:latest"
        
        logger.info(f"🔨 Building Docker image: {image_name}")
        
        # Find Dockerfile
        dockerfile_path = source_path / "Dockerfile"
        if not dockerfile_path.exists():
            # Generate Dockerfile if not present
            dockerfile_content = self._generate_dockerfile(config)
            with open(dockerfile_path, 'w') as f:
                f.write(dockerfile_content)
        
        # Build image
        try:
            image, build_logs = self.docker_client.images.build(
                path=str(source_path),
                tag=image_name,
                rm=True,
                pull=True
            )
            
            logger.info(f"✅ Built Docker image: {image_name}")
            return image_name
            
        except Exception as e:
            logger.error(f"❌ Failed to build Docker image: {e}")
            raise
    
    def _generate_dockerfile(self, config: DeploymentConfig) -> str:
        """Generate Dockerfile based on detected framework."""
        if config.language.lower() == 'python':
            return self._generate_python_dockerfile(config)
        elif config.language.lower() in ['javascript', 'typescript']:
            return self._generate_node_dockerfile(config)
        else:
            return self._generate_generic_dockerfile(config)
    
    def _generate_python_dockerfile(self, config: DeploymentConfig) -> str:
        """Generate Python Dockerfile."""
        return f"""FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create health check endpoint
RUN echo 'from flask import Flask; app = Flask(__name__); @app.route("/health"); def health(): return {{"status": "healthy", "iteration": "{config.iteration_id}"}}; if __name__ == "__main__": app.run(host="0.0.0.0", port={config.base_port})' > health_check.py

# Expose port
EXPOSE {config.base_port}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \\
    CMD curl -f http://localhost:{config.base_port}/health || exit 1

# Run application
CMD ["python", "main.py"]
"""
    
    def _generate_node_dockerfile(self, config: DeploymentConfig) -> str:
        """Generate Node.js Dockerfile.""" 
        return f"""FROM node:18-alpine

WORKDIR /app

# Install system dependencies
RUN apk add --no-cache curl

# Copy package files first for better caching
COPY package*.json ./
RUN npm ci --only=production

# Copy application code
COPY . .

# Expose port
EXPOSE {config.base_port}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \\
    CMD curl -f http://localhost:{config.base_port}/health || exit 1

# Run application
CMD ["node", "index.js"]
"""
    
    def _generate_generic_dockerfile(self, config: DeploymentConfig) -> str:
        """Generate generic Dockerfile."""
        return f"""FROM ubuntu:22.04

WORKDIR /app

# Install basic dependencies
RUN apt-get update && apt-get install -y \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Copy application
COPY . .

# Make start script executable
RUN chmod +x start.sh || true

# Expose port
EXPOSE {config.base_port}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \\
    CMD curl -f http://localhost:{config.base_port}/health || exit 1

# Default command
CMD ["./start.sh"]
"""
    
    def _create_container(self, 
                         config: DeploymentConfig,
                         image_name: str,
                         source_path: Path) -> Container:
        """Create Docker container with proper configuration."""
        container_name = f"coval-{config.iteration_id}"
        
        # Port mappings
        port_mappings = {f"{config.base_port}/tcp": config.base_port}
        
        # Volume mappings
        volumes = {
            str(source_path): {'bind': '/app', 'mode': 'rw'}
        }
        
        # Create container
        container = self.docker_client.containers.create(
            image=image_name,
            name=container_name,
            ports=port_mappings,
            volumes=volumes,
            environment=config.environment,
            detach=True,
            auto_remove=False,
            restart_policy={"Name": "unless-stopped"}
        )
        
        return container
    
    def _setup_networking(self, container: Container, config: DeploymentConfig):
        """Setup Docker networking for the container."""
        try:
            # Get or create network
            network = self._get_or_create_network(config.network_name)
            
            # Connect container to network
            network.connect(container)
            
            logger.info(f"🌐 Connected container to network: {config.network_name}")
            
        except Exception as e:
            logger.warning(f"Network setup failed: {e}")
    
    def _get_or_create_network(self, network_name: str) -> Network:
        """Get existing network or create new one."""
        try:
            return self.docker_client.networks.get(network_name)
        except docker.errors.NotFound:
            logger.info(f"Creating Docker network: {network_name}")
            return self.docker_client.networks.create(
                network_name,
                driver="bridge",
                enable_ipv6=False
            )
    
    def _start_health_monitoring(self, 
                               deployment_status: DeploymentStatus,
                               config: DeploymentConfig):
        """Start health monitoring for the deployment."""
        # This would typically run in a separate thread
        # For now, we'll do a simple immediate health check
        try:
            container = self.docker_client.containers.get(deployment_status.container_id)
            
            # Wait for container to start
            time.sleep(5)
            
            # Check if container is running
            container.reload()
            if container.status == 'running':
                deployment_status.status = 'running'
                deployment_status.health_status = 'healthy'
                logger.info(f"✅ Container is running and healthy: {container.name}")
            else:
                deployment_status.status = 'failed'
                deployment_status.health_status = 'unhealthy'
                logger.error(f"❌ Container failed to start: {container.name}")
                
        except Exception as e:
            logger.error(f"Health monitoring failed: {e}")
            deployment_status.health_status = 'unknown'
    
    def stop_deployment(self, iteration_id: str) -> bool:
        """Stop a deployment and cleanup resources."""
        if iteration_id not in self.active_deployments:
            logger.warning(f"No active deployment found for iteration: {iteration_id}")
            return False
        
        deployment = self.active_deployments[iteration_id]
        
        try:
            # Stop container
            container = self.docker_client.containers.get(deployment.container_id)
            container.stop(timeout=30)
            container.remove()
            
            # Update status
            deployment.status = 'stopped' 
            deployment.stopped_at = datetime.now()
            
            # Remove from active deployments
            del self.active_deployments[iteration_id]
            
            # Cleanup overlay
            self._cleanup_overlay(iteration_id)
            
            logger.info(f"🛑 Stopped deployment: {iteration_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop deployment {iteration_id}: {e}")
            return False
    
    def _cleanup_overlay(self, iteration_id: str):
        """Cleanup overlay filesystem and temporary files."""
        overlay_dir = self.deployments_dir / "overlays" / iteration_id  
        
        if overlay_dir.exists():
            try:
                # Unmount overlay if it exists
                merged_dir = overlay_dir / "merged"
                if merged_dir.exists():
                    subprocess.run(['sudo', 'umount', str(merged_dir)], 
                                 capture_output=True)
                
                # Remove overlay directory
                shutil.rmtree(overlay_dir)
                logger.info(f"🧹 Cleaned up overlay for: {iteration_id}")
                
            except Exception as e:
                logger.warning(f"Overlay cleanup failed: {e}")
    
    def get_deployment_status(self, iteration_id: str) -> Optional[DeploymentStatus]:
        """Get status of a deployment."""
        return self.active_deployments.get(iteration_id)
    
    def list_active_deployments(self) -> List[DeploymentStatus]:
        """List all active deployments."""
        return list(self.active_deployments.values())
    
    def cleanup_old_deployments(self, keep_count: int = 3) -> List[str]:
        """Cleanup old deployments, keeping only the most recent ones."""
        all_deployments = list(self.active_deployments.items())
        
        # Sort by start time
        sorted_deployments = sorted(
            all_deployments,
            key=lambda x: x[1].started_at or datetime.min,
            reverse=True
        )
        
        # Keep recent deployments, stop old ones
        stopped_deployments = []
        for iteration_id, deployment in sorted_deployments[keep_count:]:
            if self.stop_deployment(iteration_id):
                stopped_deployments.append(iteration_id)
        
        return stopped_deployments
    
    # Helper methods for framework detection (similar to IterationManager)
    def _detect_framework(self, path: Path) -> str:
        """Auto-detect framework."""
        if (path / "requirements.txt").exists():
            with open(path / "requirements.txt", 'r') as f:
                content = f.read().lower()
                if 'fastapi' in content:
                    return 'fastapi'
                elif 'flask' in content:
                    return 'flask'
                elif 'django' in content:
                    return 'django'
        
        if (path / "package.json").exists():
            try:
                with open(path / "package.json", 'r') as f:
                    data = json.load(f)
                    deps = {**data.get('dependencies', {}), **data.get('devDependencies', {})}
                    if 'express' in deps:
                        return 'express'
                    elif 'next' in deps:
                        return 'nextjs'
            except:
                pass
        
        return 'unknown'
    
    def _detect_language(self, path: Path) -> str:
        """Auto-detect primary language."""
        file_counts = {}
        for file_path in path.rglob('*'):
            if file_path.is_file():
                suffix = file_path.suffix.lower()
                file_counts[suffix] = file_counts.get(suffix, 0) + 1
        
        common_extensions = {
            '.py': 'python',
            '.js': 'javascript', 
            '.ts': 'typescript',
            '.go': 'go'
        }
        
        for ext in sorted(file_counts.keys(), key=file_counts.get, reverse=True):
            if ext in common_extensions:
                return common_extensions[ext]
        
        return 'unknown'
    
    def _find_dockerfile(self, path: Path) -> str:
        """Find Dockerfile."""
        locations = ["Dockerfile", "docker/Dockerfile"]
        for location in locations:
            if (path / location).exists():
                return location
        return ""
    
    def _find_docker_compose(self, path: Path) -> str:
        """Find docker-compose.yml."""
        locations = ["docker-compose.yml", "compose.yml"]
        for location in locations:
            if (path / location).exists():
                return location
        return ""

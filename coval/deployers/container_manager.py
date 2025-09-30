#!/usr/bin/env python3
"""
COVAL Container Manager

Handles Docker container lifecycle management with proper cleanup and error handling.
Fixes the container naming conflicts and cleanup issues from the monolithic deployment manager.
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import docker
from docker.models.containers import Container
from docker.models.networks import Network
from docker.errors import DockerException, NotFound, APIError

logger = logging.getLogger(__name__)


@dataclass
class ContainerConfig:
    """Configuration for Docker container creation."""
    name: str
    image: str
    ports: Dict[str, int]  # container_port -> host_port
    volumes: Dict[str, Dict[str, str]]  # host_path -> bind_config
    environment: Dict[str, str]
    network: Optional[str] = None
    restart_policy: Dict[str, str] = None
    auto_remove: bool = False
    detach: bool = True


@dataclass
class ContainerStatus:
    """Status information for a container."""
    container_id: Optional[str]
    name: str
    status: str  # 'creating', 'running', 'stopped', 'failed', 'removed'
    ports: Dict[str, int]
    created_at: Optional[datetime]
    started_at: Optional[datetime]
    stopped_at: Optional[datetime]
    exit_code: Optional[int] = None
    error_message: Optional[str] = None


class ContainerManager:
    """
    Manages Docker container lifecycle with robust cleanup and error handling.
    
    Features:
    - Proper container cleanup to prevent naming conflicts
    - Robust error handling with detailed logging
    - Force removal of stuck/zombie containers
    - Container status tracking and monitoring
    - Network management
    """
    
    def __init__(self):
        """Initialize the ContainerManager with Docker client."""
        try:
            self.docker_client = docker.from_env()
            # Test Docker connection
            self.docker_client.ping()
            logger.debug("✓ Docker client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            raise DockerException(f"Docker connection failed: {e}")
        
        # Track managed containers
        self.managed_containers: Dict[str, ContainerStatus] = {}
    
    def create_container(self, config: ContainerConfig) -> ContainerStatus:
        """
        Create a Docker container with proper cleanup of existing containers.
        
        Args:
            config: Container configuration
            
        Returns:
            ContainerStatus: Status of the created container
        """
        logger.debug(f"Creating container: {config.name}")
        
        # First, ensure any existing container with the same name is properly cleaned up
        self._force_cleanup_container(config.name)
        
        container_status = ContainerStatus(
            container_id=None,
            name=config.name,
            status='creating',
            ports=config.ports,
            created_at=datetime.now(),
            started_at=None,
            stopped_at=None
        )
        
        try:
            # Prepare restart policy
            restart_policy = config.restart_policy or {"Name": "unless-stopped"}
            
            # Create the container
            container = self.docker_client.containers.create(
                image=config.image,
                name=config.name,
                ports=config.ports,
                volumes=config.volumes,
                environment=config.environment,
                detach=config.detach,
                auto_remove=config.auto_remove,
                restart_policy=restart_policy
            )
            
            # Update status
            container_status.container_id = container.id
            container_status.status = 'created'
            container_status.created_at = datetime.now()
            
            # Connect to network if specified
            if config.network:
                self._connect_to_network(container, config.network)
            
            # Track the container
            self.managed_containers[config.name] = container_status
            
            logger.info(f"✓ Container created successfully: {config.name} ({container.short_id})")
            return container_status
            
        except APIError as e:
            error_msg = f"Docker API error creating container {config.name}: {e}"
            logger.error(error_msg)
            container_status.status = 'failed'
            container_status.error_message = error_msg
            return container_status
        except Exception as e:
            error_msg = f"Unexpected error creating container {config.name}: {e}"
            logger.error(error_msg)
            container_status.status = 'failed' 
            container_status.error_message = error_msg
            return container_status
    
    def start_container(self, container_name: str) -> bool:
        """
        Start a container by name.
        
        Args:
            container_name: Name of the container to start
            
        Returns:
            bool: True if started successfully, False otherwise
        """
        logger.debug(f"Starting container: {container_name}")
        
        try:
            container = self.docker_client.containers.get(container_name)
            container.start()
            
            # Update status
            if container_name in self.managed_containers:
                self.managed_containers[container_name].status = 'running'
                self.managed_containers[container_name].started_at = datetime.now()
            
            logger.info(f"✓ Container started successfully: {container_name}")
            return True
            
        except NotFound:
            logger.error(f"Container not found: {container_name}")
            return False
        except APIError as e:
            logger.error(f"Failed to start container {container_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error starting container {container_name}: {e}")
            return False
    
    def stop_container(self, container_name: str, timeout: int = 30) -> bool:
        """
        Stop a container by name with proper cleanup.
        
        Args:
            container_name: Name of the container to stop
            timeout: Timeout in seconds for graceful stop
            
        Returns:
            bool: True if stopped successfully, False otherwise
        """
        logger.debug(f"Stopping container: {container_name}")
        
        try:
            container = self.docker_client.containers.get(container_name)
            
            # Stop the container
            container.stop(timeout=timeout)
            
            # Update status
            if container_name in self.managed_containers:
                self.managed_containers[container_name].status = 'stopped'
                self.managed_containers[container_name].stopped_at = datetime.now()
            
            logger.info(f"✓ Container stopped successfully: {container_name}")
            return True
            
        except NotFound:
            logger.warning(f"Container not found when stopping: {container_name}")
            return True  # Already stopped/removed
        except APIError as e:
            logger.error(f"Failed to stop container {container_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error stopping container {container_name}: {e}")
            return False
    
    def remove_container(self, container_name: str, force: bool = False) -> bool:
        """
        Remove a container by name with proper cleanup.
        
        Args:
            container_name: Name of the container to remove
            force: Force removal even if running
            
        Returns:
            bool: True if removed successfully, False otherwise
        """
        logger.debug(f"Removing container: {container_name} (force={force})")
        
        try:
            container = self.docker_client.containers.get(container_name)
            
            # Remove the container
            container.remove(force=force)
            
            # Update status and remove from tracking
            if container_name in self.managed_containers:
                self.managed_containers[container_name].status = 'removed'
                del self.managed_containers[container_name]
            
            logger.info(f"✓ Container removed successfully: {container_name}")
            return True
            
        except NotFound:
            logger.debug(f"Container not found when removing: {container_name}")
            # Clean up from tracking if it exists
            if container_name in self.managed_containers:
                del self.managed_containers[container_name]
            return True  # Already removed
        except APIError as e:
            logger.error(f"Failed to remove container {container_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error removing container {container_name}: {e}")
            return False
    
    def stop_and_remove_container(self, container_name: str, timeout: int = 30) -> bool:
        """
        Stop and remove a container with proper cleanup.
        
        Args:
            container_name: Name of the container to stop and remove
            timeout: Timeout in seconds for graceful stop
            
        Returns:
            bool: True if stopped and removed successfully, False otherwise
        """
        logger.debug(f"Stopping and removing container: {container_name}")
        
        # First attempt graceful stop and remove
        if self.stop_container(container_name, timeout):
            return self.remove_container(container_name)
        else:
            # If graceful stop failed, force remove
            logger.warning(f"Graceful stop failed, force removing container: {container_name}")
            return self.remove_container(container_name, force=True)
    
    def _force_cleanup_container(self, container_name: str):
        """
        Force cleanup of any existing container with the given name.
        This prevents naming conflicts when creating new containers.
        
        Args:
            container_name: Name of the container to cleanup
        """
        try:
            existing_container = self.docker_client.containers.get(container_name)
            logger.warning(f"Found existing container with name {container_name}, cleaning up...")
            
            # Try to stop gracefully first
            try:
                existing_container.stop(timeout=10)
                logger.debug(f"Gracefully stopped existing container: {container_name}")
            except Exception as e:
                logger.debug(f"Graceful stop failed for {container_name}: {e}")
            
            # Force remove
            existing_container.remove(force=True)
            logger.info(f"✓ Cleaned up existing container: {container_name}")
            
        except NotFound:
            # No existing container, this is good
            logger.debug(f"No existing container found with name: {container_name}")
        except Exception as e:
            logger.warning(f"Failed to cleanup existing container {container_name}: {e}")
    
    def get_container_status(self, container_name: str) -> Optional[ContainerStatus]:
        """
        Get the status of a managed container.
        
        Args:
            container_name: Name of the container
            
        Returns:
            ContainerStatus or None if not found
        """
        # Check our tracking first
        if container_name in self.managed_containers:
            status = self.managed_containers[container_name]
            
            # Update with live Docker status if container exists
            try:
                container = self.docker_client.containers.get(container_name)
                status.status = container.status
                if hasattr(container.attrs, 'State'):
                    state = container.attrs.get('State', {})
                    if 'ExitCode' in state:
                        status.exit_code = state['ExitCode']
            except NotFound:
                status.status = 'removed'
            except Exception as e:
                logger.warning(f"Failed to get live status for {container_name}: {e}")
            
            return status
        
        # Not in our tracking, check Docker directly
        try:
            container = self.docker_client.containers.get(container_name)
            return ContainerStatus(
                container_id=container.id,
                name=container_name,
                status=container.status,
                ports={},  # Would need to parse from container.attrs
                created_at=None,  # Would need to parse from container.attrs
                started_at=None,
                stopped_at=None
            )
        except NotFound:
            return None
        except Exception as e:
            logger.warning(f"Failed to get container status for {container_name}: {e}")
            return None
    
    def list_managed_containers(self) -> List[ContainerStatus]:
        """Get list of all managed containers."""
        return list(self.managed_containers.values())
    
    def _connect_to_network(self, container: Container, network_name: str):
        """Connect container to specified network."""
        try:
            # Get or create network
            try:
                network = self.docker_client.networks.get(network_name)
            except NotFound:
                network = self.docker_client.networks.create(network_name, driver="bridge")
                logger.debug(f"Created network: {network_name}")
            
            # Connect container to network
            network.connect(container)
            logger.debug(f"Connected container {container.name} to network {network_name}")
            
        except Exception as e:
            logger.warning(f"Failed to connect container to network {network_name}: {e}")
    
    def cleanup_all_managed_containers(self) -> Dict[str, bool]:
        """
        Cleanup all managed containers.
        
        Returns:
            Dict mapping container names to cleanup success status
        """
        results = {}
        
        for container_name in list(self.managed_containers.keys()):
            results[container_name] = self.stop_and_remove_container(container_name)
        
        return results

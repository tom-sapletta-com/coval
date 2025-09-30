"""
Unit tests for modular deployer components.
Tests the new Docker deployment system with proper container lifecycle management.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from pathlib import Path

from coval.deployers.container_manager import ContainerManager, ContainerConfig, ContainerStatus
from coval.deployers.health_checker import HealthChecker, HealthStatus
from coval.deployers.docker_deployer import DockerDeployer, DeploymentConfig, DeploymentResult


class TestContainerManager:
    """Test cases for ContainerManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = ContainerManager()
    
    def test_initialization(self):
        """Test ContainerManager initialization."""
        assert self.manager is not None
        assert hasattr(self.manager, 'docker_client')
        assert hasattr(self.manager, 'managed_containers')
    
    def test_container_manager_basic(self):
        """Test ContainerManager basic functionality."""
        manager = ContainerManager()
        assert manager is not None
        assert hasattr(manager, 'docker_client')
        assert hasattr(manager, 'managed_containers')
    
    def test_container_status_creation(self):
        """Test ContainerStatus data class with proper initialization."""
        status = ContainerStatus(
            container_id="test-id",
            name="test-container",
            status="running",
            ports={8000: 8000},
            created_at=datetime.now(),
            started_at=datetime.now(),
            stopped_at=None
        )
        
        assert status.container_id == "test-id"
        assert status.name == "test-container"
        assert status.status == "running"
        assert status.started_at is not None
        assert status.stopped_at is None
    
    @patch('coval.deployers.container_manager.docker.from_env')
    @patch('coval.deployers.container_manager.logger')
    def test_force_cleanup_container(self, mock_logger, mock_docker):
        """Test force cleanup of existing containers."""
        # Mock container that exists and needs cleanup
        mock_container = Mock()
        mock_docker.return_value.containers.get.return_value = mock_container
        
        manager = ContainerManager()
        manager._force_cleanup_container("test-container")
        
        # Should attempt to stop and remove the container
        mock_container.stop.assert_called_once()
        mock_container.remove.assert_called_once()


class TestHealthChecker:
    """Test cases for HealthChecker class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.checker = HealthChecker()
    
    def test_initialization(self):
        """Test HealthChecker initialization."""
        assert self.checker is not None
        # Basic attribute check without assuming specific implementation details
        assert hasattr(self.checker, '__dict__')  # Has some attributes
    
    def test_health_status_enum(self):
        """Test HealthStatus enum values."""
        assert HealthStatus.UNKNOWN.value == "unknown"
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.STARTING.value == "starting"


class TestDockerDeployer:
    """Test cases for DockerDeployer class."""
    
    @patch('pathlib.Path.mkdir')
    def test_initialization_with_mock_path(self, mock_mkdir):
        """Test DockerDeployer initialization with mocked path creation."""
        deployer = DockerDeployer("/tmp/test-project")
        assert deployer is not None
        assert hasattr(deployer, 'container_manager')
        assert hasattr(deployer, 'health_checker')
        assert hasattr(deployer, 'active_deployments')
    
    def test_deployment_config_creation(self):
        """Test DeploymentConfig data class."""
        config = DeploymentConfig(
            iteration_id="test-iteration",
            project_name="test-project",
            framework="fastapi",
            language="python",
            source_path=Path("/tmp/source"),
            base_port=8000
        )
        
        assert config.iteration_id == "test-iteration"
        assert config.project_name == "test-project"
        assert config.framework == "fastapi"
        assert config.language == "python"
        assert config.base_port == 8000
    
    def test_deployment_result_creation(self):
        """Test DeploymentResult data class."""
        result = DeploymentResult(
            success=True,
            iteration_id="test-iteration",
            container_name="test-container",
            container_id="test-id",
            image_name="test-image:latest",
            port_mappings={8000: 8000},
            health_status=HealthStatus.HEALTHY,
            deployment_time=30.5,
            error_message=None
        )
        
        assert result.success is True
        assert result.container_name == "test-container"
        assert result.health_status == HealthStatus.HEALTHY
        assert result.deployment_time == 30.5
        assert result.error_message is None


class TestIntegration:
    """Integration tests for modular deployer components."""
    
    def test_basic_integration(self):
        """Test basic integration of modular components."""
        # Test that all components can be imported and instantiated
        container_manager = ContainerManager()
        health_checker = HealthChecker()
        
        assert container_manager is not None
        assert health_checker is not None
        
        # Test data class integration
        status = ContainerStatus(
            container_id="test-id",
            name="test-container",
            status="running",
            ports={8000: 8000},
            created_at=datetime.now(),
            started_at=datetime.now(),
            stopped_at=None
        )
        
        assert status.container_id == "test-id"
        assert status.name == "test-container"

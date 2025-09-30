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
    
    def test_container_config_creation(self):
        """Test ContainerConfig data class."""
        config = ContainerConfig(
            name="test-container",
            image="test-image:latest",
            ports={8000: 8000},
            environment={"TEST": "value"}
        )
        
        assert config.name == "test-container"
        assert config.image == "test-image:latest"
        assert config.ports == {8000: 8000}
        assert config.environment["TEST"] == "value"
    
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
    def test_force_cleanup_container(self, mock_docker):
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
        assert hasattr(self.checker, 'monitoring_threads')
    
    def test_health_status_enum(self):
        """Test HealthStatus enum values."""
        assert HealthStatus.UNKNOWN.value == "unknown"
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.STARTING.value == "starting"
    
    @patch('coval.deployers.health_checker.socket.socket')
    def test_port_connectivity_check(self, mock_socket):
        """Test port connectivity checking."""
        # Mock successful connection
        mock_socket.return_value.connect_ex.return_value = 0
        
        result = self.checker._check_port_connectivity("localhost", 8000, timeout=1)
        assert result is True
        
        # Mock failed connection
        mock_socket.return_value.connect_ex.return_value = 1
        
        result = self.checker._check_port_connectivity("localhost", 8000, timeout=1)
        assert result is False
    
    @patch('coval.deployers.health_checker.requests.get')
    def test_http_endpoint_check(self, mock_get):
        """Test HTTP endpoint health checking."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = self.checker._check_http_endpoint("http://localhost:8000/health")
        assert result is True
        
        # Mock failed response
        mock_response.status_code = 500
        result = self.checker._check_http_endpoint("http://localhost:8000/health")
        assert result is False


class TestDockerDeployer:
    """Test cases for DockerDeployer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.deployer = DockerDeployer("/tmp/test-project")
    
    def test_initialization(self):
        """Test DockerDeployer initialization."""
        assert self.deployer is not None
        assert hasattr(self.deployer, 'container_manager')
        assert hasattr(self.deployer, 'health_checker')
        assert hasattr(self.deployer, 'active_deployments')
    
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
            container_name="test-container",
            container_id="test-id",
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
    
    @patch('coval.deployers.docker_deployer.DockerDeployer._build_image')
    @patch('coval.deployers.docker_deployer.DockerDeployer._create_container')
    def test_deploy_workflow(self, mock_create, mock_build):
        """Test basic deployment workflow."""
        # Mock successful image build and container creation
        mock_build.return_value = True
        mock_create.return_value = Mock()
        
        config = DeploymentConfig(
            iteration_id="test-iteration",
            project_name="test-project",
            framework="fastapi",
            language="python",
            source_path=Path("/tmp/source"),
            base_port=8000
        )
        
        # Should not raise exception
        result = self.deployer.deploy(config)
        assert isinstance(result, DeploymentResult)


class TestIntegration:
    """Integration tests for modular deployer components."""
    
    @patch('coval.deployers.container_manager.docker.from_env')
    @patch('coval.deployers.health_checker.requests.get')
    def test_full_deployment_lifecycle(self, mock_get, mock_docker):
        """Test complete deployment lifecycle with all components."""
        # Mock Docker client and container
        mock_container = Mock()
        mock_container.id = "test-container-id"
        mock_container.status = "running"
        mock_docker.return_value.containers.create.return_value = mock_container
        mock_docker.return_value.images.build.return_value = (Mock(), [])
        
        # Mock health check response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        # Create deployer and deploy
        deployer = DockerDeployer("/tmp/test-project")
        config = DeploymentConfig(
            iteration_id="test-integration",
            project_name="test-project",
            framework="fastapi",
            language="python",
            source_path=Path("/tmp/source"),
            base_port=8000
        )
        
        # This tests the integration between all modular components
        result = deployer.deploy(config)
        assert isinstance(result, DeploymentResult)

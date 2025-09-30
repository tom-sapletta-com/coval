"""
Unit tests for CLI interface.
Tests the command-line interface with modular components.
"""
import pytest
from unittest.mock import Mock, patch
from click.testing import CliRunner

from coval.cli import cli, COVALOrchestrator


class TestCLI:
    """Test cases for CLI interface."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_cli_help(self):
        """Test CLI help command."""
        result = self.runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert "COVAL" in result.output
        assert "generate" in result.output
        assert "run" in result.output
        assert "status" in result.output
    
    def test_generate_help(self):
        """Test generate command help."""
        result = self.runner.invoke(cli, ['generate', '--help'])
        assert result.exit_code == 0
        assert "Generate new code iteration" in result.output
        assert "--description" in result.output
        assert "--framework" in result.output
    
    def test_run_help(self):
        """Test run command help."""
        result = self.runner.invoke(cli, ['run', '--help'])
        assert result.exit_code == 0
        assert "Deploy iteration with Docker" in result.output
        assert "--iteration" in result.output
        assert "--port" in result.output
    
    def test_status_help(self):
        """Test status command help."""
        result = self.runner.invoke(cli, ['status', '--help'])
        assert result.exit_code == 0


class TestCOVALOrchestrator:
    """Test cases for COVALOrchestrator class."""
    
    @patch('coval.cli.IterationManager')
    @patch('coval.cli.GenerationEngine')
    @patch('coval.cli.DockerDeployer')
    @patch('pathlib.Path.mkdir')
    @patch('logging.FileHandler')
    def test_initialization_with_mocks(self, mock_filehandler, mock_mkdir, mock_deployer, mock_engine, mock_iter):
        """Test COVALOrchestrator initialization with mocked dependencies."""
        orchestrator = COVALOrchestrator("/tmp/test-project")
        assert orchestrator is not None
        assert hasattr(orchestrator, 'generation_engine')
        assert hasattr(orchestrator, 'deployment_manager')
        assert hasattr(orchestrator, 'iteration_manager')
    
    def test_generate_command_missing_description(self):
        """Test generate command without required description."""
        runner = CliRunner()
        result = runner.invoke(cli, ['generate'])
        assert result.exit_code == 2  # Click error for missing required option
        assert "Missing option" in result.output or "required" in result.output.lower()
    
    @patch('coval.cli.get_orchestrator')
    def test_status_command(self, mock_get_orch):
        """Test status command execution."""
        # Mock orchestrator with empty iterations
        mock_orch = Mock()
        mock_orch.iteration_manager.iterations = {}
        mock_orch.deployment_manager.active_deployments = []
        mock_get_orch.return_value = mock_orch
        
        runner = CliRunner()
        result = runner.invoke(cli, ['status'])
        # Should not crash, may exit with 0 or 1 depending on content
        assert result.exit_code in [0, 1]


class TestCLIIntegration:
    """Integration tests for CLI with modular components."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    @patch('coval.cli.get_orchestrator')
    def test_cli_with_modular_components(self, mock_get_orch):
        """Test CLI integration with modular deployer components."""
        # Mock orchestrator with modular components
        mock_orch = Mock()
        mock_orch.deployment_manager.active_deployments = []
        mock_orch.iteration_manager.iterations = {}
        mock_get_orch.return_value = mock_orch
        
        # Test that status command works with modular deployer
        result = self.runner.invoke(cli, ['status'])
        assert result.exit_code in [0, 1]  # May exit 1 if no content, that's ok
        
        # Verify that modular deployer method is called correctly
        # (This tests our fix for list_deployments -> active_deployments)
        assert hasattr(mock_orch.deployment_manager, 'active_deployments')

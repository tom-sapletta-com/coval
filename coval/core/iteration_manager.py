#!/usr/bin/env python3
"""
COVAL Iteration Manager

Manages iterative code generation, execution, and deployment in separate folders
with Docker Compose integration and transparent volume mounting.
"""

import os
import shutil
import json
import yaml
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class IterationInfo:
    """Information about a code iteration."""
    iteration_id: str
    timestamp: datetime
    description: str
    parent_iteration: Optional[str]
    generation_type: str  # 'generate', 'repair', 'modify'
    status: str  # 'generated', 'running', 'tested', 'deployed', 'failed'
    cost_estimate: float
    success_rate: float
    files_changed: List[str]
    docker_status: str
    performance_metrics: Dict[str, Any]


@dataclass
class ProjectStructure:
    """Represents the structure of a project iteration."""
    name: str
    framework: str
    language: str
    dependencies: List[str]
    dockerfile_path: str
    compose_path: str
    entry_point: str
    test_files: List[str]


class IterationManager:
    """
    Manages iterative code generation with Docker deployment.
    
    Features:
    - Creates separate folders for each iteration
    - Manages Docker Compose deployments with volume mounting
    - Tracks iteration history and performance
    - Handles legacy cleanup and cost optimization
    - Provides transparent deployment of latest changes
    """
    
    def __init__(self, project_root: str, config_path: Optional[str] = None):
        self.project_root = Path(project_root)
        self.iterations_dir = self.project_root / "iterations"
        self.deployments_dir = self.project_root / "deployments"
        self.config_path = config_path or str(self.project_root / "coval.config.yaml")
        
        # Ensure directories exist
        self.iterations_dir.mkdir(parents=True, exist_ok=True)
        self.deployments_dir.mkdir(parents=True, exist_ok=True)
        
        # Load configuration
        self.config = self._load_config()
        
        # Track iterations
        self.iterations: Dict[str, IterationInfo] = {}
        self._load_iteration_history()
        
        # Setup logging
        self._setup_logging()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load COVAL configuration."""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        
        # Default configuration
        default_config = {
            'project': {
                'name': 'coval-project',
                'framework': 'auto-detect',
                'max_iterations': 50,
                'cleanup_threshold': 10
            },
            'docker': {
                'base_port': 8000,
                'network_name': 'coval-network',
                'volume_strategy': 'overlay',
                'auto_cleanup': True
            },
            'generation': {
                'prefer_modification_threshold': 0.3,
                'generation_timeout': 300,
                'max_retries': 3
            },
            'deployment': {
                'health_check_timeout': 60,
                'deployment_strategy': 'blue-green',
                'rollback_on_failure': True
            }
        }
        
        # Save default config
        with open(self.config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)
        
        return default_config
    
    def _setup_logging(self):
        """Setup logging for iteration management."""
        log_dir = self.project_root / "logs"
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f"iterations_{datetime.now().strftime('%Y%m%d')}.log"
        
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    def _load_iteration_history(self):
        """Load iteration history from disk."""
        history_file = self.project_root / "iteration_history.json"
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    data = json.load(f)
                    for item in data:
                        # Convert timestamp string back to datetime
                        item['timestamp'] = datetime.fromisoformat(item['timestamp'])
                        iteration = IterationInfo(**item)
                        self.iterations[iteration.iteration_id] = iteration
            except Exception as e:
                logger.warning(f"Could not load iteration history: {e}")
    
    def _save_iteration_history(self):
        """Save iteration history to disk."""
        history_file = self.project_root / "iteration_history.json"
        try:
            data = []
            for iteration in self.iterations.values():
                item = asdict(iteration)
                # Convert datetime to string for JSON serialization
                item['timestamp'] = iteration.timestamp.isoformat()
                data.append(item)
            
            with open(history_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save iteration history: {e}")
    
    def create_iteration(self, 
                        description: str, 
                        generation_type: str = 'generate',
                        parent_iteration: Optional[str] = None) -> str:
        """
        Create a new iteration folder.
        
        Args:
            description: Description of this iteration
            generation_type: Type of generation ('generate', 'repair', 'modify')
            parent_iteration: ID of parent iteration to base this on
            
        Returns:
            iteration_id: Unique ID for this iteration
        """
        timestamp = datetime.now()
        iteration_id = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{generation_type}"
        
        iteration_path = self.iterations_dir / iteration_id
        iteration_path.mkdir(parents=True, exist_ok=True)
        
        # Create iteration structure
        (iteration_path / "src").mkdir(exist_ok=True)
        (iteration_path / "tests").mkdir(exist_ok=True)
        (iteration_path / "docker").mkdir(exist_ok=True)
        (iteration_path / "logs").mkdir(exist_ok=True)
        (iteration_path / "config").mkdir(exist_ok=True)
        
        # Copy from parent iteration if specified
        if parent_iteration and parent_iteration in self.iterations:
            parent_path = self.iterations_dir / parent_iteration
            if parent_path.exists():
                self._copy_iteration_base(parent_path, iteration_path)
                logger.info(f"Copied base from parent iteration: {parent_iteration}")
        
        # Create iteration info
        iteration_info = IterationInfo(
            iteration_id=iteration_id,
            timestamp=timestamp,
            description=description,
            parent_iteration=parent_iteration,
            generation_type=generation_type,
            status='generated',
            cost_estimate=0.0,
            success_rate=0.0,
            files_changed=[],
            docker_status='not_deployed',
            performance_metrics={}
        )
        
        self.iterations[iteration_id] = iteration_info
        self._save_iteration_history()
        
        logger.info(f"Created iteration {iteration_id}: {description}")
        return iteration_id
    
    def _copy_iteration_base(self, source_path: Path, target_path: Path):
        """Copy base files from source iteration to target iteration."""
        # Copy source code
        if (source_path / "src").exists():
            shutil.copytree(source_path / "src", target_path / "src", dirs_exist_ok=True)
        
        # Copy configuration files
        for config_file in ["requirements.txt", "package.json", "Dockerfile", "docker-compose.yml"]:
            source_file = source_path / config_file
            if source_file.exists():
                shutil.copy2(source_file, target_path / config_file)
        
        # Copy docker configuration
        if (source_path / "docker").exists():
            shutil.copytree(source_path / "docker", target_path / "docker", dirs_exist_ok=True)
    
    def get_latest_iteration(self) -> Optional[str]:
        """Get the ID of the latest iteration."""
        if not self.iterations:
            return None
        
        return max(self.iterations.keys(), key=lambda x: self.iterations[x].timestamp)
    
    def get_active_iterations(self) -> List[str]:
        """Get list of iterations that are currently deployed."""
        return [
            iteration_id for iteration_id, info in self.iterations.items()
            if info.docker_status in ['running', 'deployed']
        ]
    
    def get_iteration_path(self, iteration_id: str) -> Path:
        """Get the filesystem path for an iteration."""
        return self.iterations_dir / iteration_id
    
    def update_iteration_status(self, iteration_id: str, status: str, **kwargs):
        """Update the status and metrics of an iteration."""
        if iteration_id in self.iterations:
            self.iterations[iteration_id].status = status
            
            # Update other fields if provided
            for key, value in kwargs.items():
                if hasattr(self.iterations[iteration_id], key):
                    setattr(self.iterations[iteration_id], key, value)
            
            self._save_iteration_history()
            logger.info(f"Updated iteration {iteration_id} status to: {status}")
    
    def cleanup_old_iterations(self, keep_count: Optional[int] = None) -> List[str]:
        """
        Remove old iterations based on cleanup policy.
        
        Args:
            keep_count: Number of iterations to keep (default from config)
            
        Returns:
            List of removed iteration IDs
        """
        keep_count = keep_count or self.config['project']['cleanup_threshold']
        
        # Sort iterations by timestamp (newest first)
        sorted_iterations = sorted(
            self.iterations.items(),
            key=lambda x: x[1].timestamp,
            reverse=True
        )
        
        # Keep active iterations and recent ones
        to_keep = set()
        active_iterations = self.get_active_iterations()
        to_keep.update(active_iterations)
        
        # Keep the most recent iterations
        for iteration_id, _ in sorted_iterations[:keep_count]:
            to_keep.add(iteration_id)
        
        # Remove old iterations
        removed = []
        for iteration_id, info in sorted_iterations[keep_count:]:
            if iteration_id not in to_keep and info.docker_status not in ['running', 'deployed']:
                iteration_path = self.get_iteration_path(iteration_id)
                if iteration_path.exists():
                    shutil.rmtree(iteration_path)
                    removed.append(iteration_id)
                    logger.info(f"Removed old iteration: {iteration_id}")
        
        # Update iteration tracking
        for iteration_id in removed:
            del self.iterations[iteration_id]
        
        self._save_iteration_history()
        return removed
    
    def analyze_project_structure(self, iteration_id: str) -> ProjectStructure:
        """Analyze the structure of a project iteration."""
        iteration_path = self.get_iteration_path(iteration_id)
        
        # Auto-detect framework and language
        framework = self._detect_framework(iteration_path)
        language = self._detect_language(iteration_path)
        
        # Find dependencies
        dependencies = self._find_dependencies(iteration_path)
        
        # Find Docker files
        dockerfile_path = self._find_dockerfile(iteration_path)
        compose_path = self._find_docker_compose(iteration_path)
        
        # Find entry point
        entry_point = self._find_entry_point(iteration_path)
        
        # Find test files
        test_files = self._find_test_files(iteration_path)
        
        return ProjectStructure(
            name=f"coval-{iteration_id}",
            framework=framework,
            language=language,
            dependencies=dependencies,
            dockerfile_path=dockerfile_path,
            compose_path=compose_path,
            entry_point=entry_point,
            test_files=test_files
        )
    
    def _detect_framework(self, path: Path) -> str:
        """Auto-detect the framework used in the project."""
        # Check for common framework indicators
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
            with open(path / "package.json", 'r') as f:
                data = json.load(f)
                deps = {**data.get('dependencies', {}), **data.get('devDependencies', {})}
                if 'express' in deps:
                    return 'express'
                elif 'next' in deps:
                    return 'nextjs'
                elif 'react' in deps:
                    return 'react'
        
        return 'unknown'
    
    def _detect_language(self, path: Path) -> str:
        """Auto-detect the primary language."""
        file_counts = {}
        
        for file_path in path.rglob('*'):
            if file_path.is_file():
                suffix = file_path.suffix.lower()
                file_counts[suffix] = file_counts.get(suffix, 0) + 1
        
        # Return the most common language
        common_extensions = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.go': 'go',
            '.rs': 'rust',
            '.java': 'java',
            '.php': 'php',
            '.rb': 'ruby'
        }
        
        for ext in sorted(file_counts.keys(), key=file_counts.get, reverse=True):
            if ext in common_extensions:
                return common_extensions[ext]
        
        return 'unknown'
    
    def _find_dependencies(self, path: Path) -> List[str]:
        """Find project dependencies."""
        deps = []
        
        # Python
        req_file = path / "requirements.txt"
        if req_file.exists():
            with open(req_file, 'r') as f:
                deps.extend([line.strip() for line in f if line.strip() and not line.startswith('#')])
        
        # Node.js
        package_file = path / "package.json"
        if package_file.exists():
            with open(package_file, 'r') as f:
                data = json.load(f)
                deps.extend(data.get('dependencies', {}).keys())
        
        return deps
    
    def _find_dockerfile(self, path: Path) -> str:
        """Find Dockerfile in the iteration."""
        dockerfile_locations = ["Dockerfile", "docker/Dockerfile", "src/Dockerfile"]
        
        for location in dockerfile_locations:
            dockerfile = path / location
            if dockerfile.exists():
                return str(dockerfile.relative_to(path))
        
        return ""
    
    def _find_docker_compose(self, path: Path) -> str:
        """Find docker-compose.yml in the iteration."""
        compose_locations = ["docker-compose.yml", "docker/docker-compose.yml", "compose.yml"]
        
        for location in compose_locations:
            compose_file = path / location
            if compose_file.exists():
                return str(compose_file.relative_to(path))
        
        return ""
    
    def _find_entry_point(self, path: Path) -> str:
        """Find the main entry point of the application."""
        entry_points = ["main.py", "app.py", "server.py", "index.js", "server.js", "app.js"]
        
        for entry in entry_points:
            entry_file = path / "src" / entry
            if entry_file.exists():
                return f"src/{entry}"
            
            entry_file = path / entry
            if entry_file.exists():
                return entry
        
        return ""
    
    def _find_test_files(self, path: Path) -> List[str]:
        """Find test files in the iteration."""
        test_files = []
        
        # Look for test files
        for test_file in path.rglob('test_*.py'):
            test_files.append(str(test_file.relative_to(path)))
        
        for test_file in path.rglob('*_test.py'):
            test_files.append(str(test_file.relative_to(path)))
        
        for test_file in path.rglob('*.test.js'):
            test_files.append(str(test_file.relative_to(path)))
        
        return test_files
    
    def get_iteration_metrics(self, iteration_id: str) -> Dict[str, Any]:
        """Get comprehensive metrics for an iteration."""
        if iteration_id not in self.iterations:
            return {}
        
        iteration = self.iterations[iteration_id]
        iteration_path = self.get_iteration_path(iteration_id)
        
        # Calculate code metrics
        code_metrics = self._calculate_code_metrics(iteration_path)
        
        return {
            'iteration_info': asdict(iteration),
            'code_metrics': code_metrics,
            'path': str(iteration_path),
            'size_mb': sum(f.stat().st_size for f in iteration_path.rglob('*') if f.is_file()) / 1024 / 1024
        }
    
    def _calculate_code_metrics(self, path: Path) -> Dict[str, Any]:
        """Calculate code quality and complexity metrics."""
        metrics = {
            'total_files': 0,
            'total_lines': 0,
            'code_files': 0,
            'test_files': 0,
            'config_files': 0,
            'languages': {}
        }
        
        for file_path in path.rglob('*'):
            if file_path.is_file():
                metrics['total_files'] += 1
                
                # Count lines
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = len(f.readlines())
                        metrics['total_lines'] += lines
                except:
                    continue
                
                # Categorize files
                suffix = file_path.suffix.lower()
                name = file_path.name.lower()
                
                if 'test' in name:
                    metrics['test_files'] += 1
                elif suffix in ['.py', '.js', '.ts', '.go', '.rs', '.java']:
                    metrics['code_files'] += 1
                elif suffix in ['.json', '.yaml', '.yml', '.toml', '.ini']:
                    metrics['config_files'] += 1
                
                # Track languages
                if suffix in ['.py', '.js', '.ts', '.go', '.rs', '.java', '.php', '.rb']:
                    metrics['languages'][suffix] = metrics['languages'].get(suffix, 0) + 1
        
        return metrics

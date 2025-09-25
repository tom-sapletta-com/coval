#!/usr/bin/env python3
"""
COVAL CLI - Command Line Interface

Comprehensive CLI for COVAL operations: generate, run, repair, and iterate.
Provides user-friendly commands that orchestrate all COVAL components.
"""

import os
import sys
import json
import click
import logging
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

# Import COVAL components
from .core.iteration_manager import IterationManager
from .core.cost_calculator import CostCalculator, CostMetrics
from .engines.generation_engine import GenerationEngine, GenerationRequest
from .engines.repair_engine import RepairEngine, LLMModel
from .docker.deployment_manager import DeploymentManager

console = Console()
logger = logging.getLogger(__name__)


class COVALOrchestrator:
    """
    Main COVAL orchestrator that coordinates all components.
    
    This is the central class that manages the full workflow:
    generate -> deploy -> monitor -> repair -> iterate
    """
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).absolute()
        
        # Initialize components
        self.iteration_manager = IterationManager(str(self.project_root))
        self.cost_calculator = CostCalculator()
        self.generation_engine = GenerationEngine()
        self.deployment_manager = DeploymentManager(str(self.project_root))
        
        # Current state
        self.current_iteration = None
        self.repair_engine = None  # Initialized when needed
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging for CLI operations."""
        log_dir = self.project_root / "logs"
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "coval.log"),
                logging.StreamHandler()
            ]
        )


# Global orchestrator instance
orchestrator = None


def get_orchestrator(project_root: str = ".") -> COVALOrchestrator:
    """Get or create the global COVAL orchestrator."""
    global orchestrator
    if orchestrator is None or str(orchestrator.project_root) != str(Path(project_root).absolute()):
        orchestrator = COVALOrchestrator(project_root)
    return orchestrator


@click.group()
@click.option('--project-root', default='.', help='Project root directory')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.pass_context
def cli(ctx, project_root, verbose):
    """
    🤖 COVAL - Intelligent Code Generation, Execution, and Repair System
    
    Generate, run, and repair code with iterative Docker deployments.
    """
    ctx.ensure_object(dict)
    ctx.obj['project_root'] = project_root
    ctx.obj['verbose'] = verbose
    
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize orchestrator
    get_orchestrator(project_root)


@cli.command()
@click.option('--description', '-d', required=True, help='Description of what to generate')
@click.option('--framework', '-f', default='fastapi', help='Framework to use (fastapi, flask, express, etc.)')
@click.option('--language', '-l', default='python', help='Programming language')
@click.option('--features', multiple=True, help='Features to include')
@click.option('--model', default='qwen', help='LLM model to use', 
              type=click.Choice(['qwen', 'deepseek', 'codellama13b', 'deepseek-r1', 'granite', 'mistral']))
@click.option('--parent', help='Parent iteration ID to base this on')
@click.option('--deploy', is_flag=True, help='Deploy immediately after generation')
@click.pass_context
def generate(ctx, description, framework, language, features, model, parent, deploy):
    """
    🚀 Generate new code iteration
    
    Creates a new iteration with generated code based on your description.
    """
    orch = get_orchestrator(ctx.obj['project_root'])
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        # Create new iteration
        task = progress.add_task("Creating iteration...", total=None)
        iteration_id = orch.iteration_manager.create_iteration(
            description=description,
            generation_type='generate',
            parent_iteration=parent
        )
        
        progress.update(task, description=f"✅ Created iteration: {iteration_id}")
        
        # Generate code
        progress.update(task, description="🤖 Generating code...")
        
        request = GenerationRequest(
            description=description,
            framework=framework,
            language=language,
            features=list(features),
            constraints=[],
            existing_code=None
        )
        
        iteration_path = orch.iteration_manager.get_iteration_path(iteration_id)
        result = orch.generation_engine.generate_code(request, iteration_path)
        
        if result.success:
            progress.update(task, description="✅ Code generation completed")
            
            # Update iteration status
            orch.iteration_manager.update_iteration_status(
                iteration_id, 
                'generated',
                confidence_score=result.confidence_score,
                files_changed=list(result.generated_files.keys())
            )
            
            # Display results
            _display_generation_results(result, iteration_id)
            
            # Deploy if requested
            if deploy:
                progress.update(task, description="🚀 Deploying iteration...")
                _deploy_iteration(orch, iteration_id, progress, task)
            
        else:
            progress.update(task, description="❌ Code generation failed")
            console.print(f"[red]Generation failed: {result.error_message}[/red]")
            sys.exit(1)


@cli.command()
@click.option('--iteration', '-i', help='Iteration ID to deploy (default: latest)')
@click.option('--port', '-p', type=int, help='Port to deploy on')
@click.option('--strategy', default='overlay', help='Deployment strategy', 
              type=click.Choice(['overlay', 'copy', 'symlink']))
@click.pass_context
def run(ctx, iteration, port, strategy):
    """
    🐳 Deploy iteration with Docker
    
    Deploys the specified iteration using transparent Docker volumes.
    """
    orch = get_orchestrator(ctx.obj['project_root'])
    
    # Get iteration to deploy
    if not iteration:
        iteration = orch.iteration_manager.get_latest_iteration()
        if not iteration:
            console.print("[red]No iterations found. Generate code first with 'coval generate'[/red]")
            sys.exit(1)
    
    if iteration not in orch.iteration_manager.iterations:
        console.print(f"[red]Iteration {iteration} not found[/red]")
        sys.exit(1)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Deploying iteration...", total=None)
        _deploy_iteration(orch, iteration, progress, task)


@cli.command()
@click.option('--error', '-e', required=True, help='Path to error log file')
@click.option('--iteration', '-i', help='Iteration ID to repair (default: latest)')
@click.option('--model', default='qwen', help='LLM model to use for repair',
              type=click.Choice(['qwen', 'deepseek', 'codellama13b', 'deepseek-r1', 'granite', 'mistral']))
@click.option('--analyze', is_flag=True, help='Only analyze, do not repair')
@click.option('--deploy', is_flag=True, help='Deploy after successful repair')
@click.pass_context
def repair(ctx, error, iteration, model, analyze, deploy):
    """
    🔧 Repair code issues intelligently
    
    Analyzes errors and repairs code using adaptive evaluation.
    """
    orch = get_orchestrator(ctx.obj['project_root'])
    
    # Get iteration to repair
    if not iteration:
        iteration = orch.iteration_manager.get_latest_iteration()
        if not iteration:
            console.print("[red]No iterations found. Generate code first.[/red]")
            sys.exit(1)
    
    error_file = Path(error)
    if not error_file.exists():
        console.print(f"[red]Error file not found: {error}[/red]")
        sys.exit(1)
    
    iteration_path = orch.iteration_manager.get_iteration_path(iteration)
    
    # Initialize repair engine
    model_enum = _get_model_enum(model)
    repair_engine = RepairEngine(model=model_enum)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        # Perform triage
        task = progress.add_task("Analyzing problem...", total=None)
        metrics = repair_engine.triage(error_file, iteration_path)
        
        progress.update(task, description="✅ Analysis completed")
        
        # Display analysis results
        _display_repair_analysis(metrics, iteration)
        
        if analyze:
            return
        
        # Perform repair
        progress.update(task, description="🔧 Attempting repair...")
        
        result = repair_engine.repair(
            error_file=error_file,
            source_dir=iteration_path,
            ticket_id=f"repair-{iteration}"
        )
        
        if result.success:
            progress.update(task, description="✅ Repair completed successfully")
            
            # Create new iteration with repaired code
            repair_iteration_id = orch.iteration_manager.create_iteration(
                description=f"Repaired {iteration}",
                generation_type='repair',
                parent_iteration=iteration
            )
            
            # Update status
            orch.iteration_manager.update_iteration_status(
                repair_iteration_id,
                'repaired',
                success_rate=result.historical_success_rate
            )
            
            console.print(f"[green]✅ Repair successful! New iteration: {repair_iteration_id}[/green]")
            
            # Deploy if requested
            if deploy:
                progress.update(task, description="🚀 Deploying repaired iteration...")
                _deploy_iteration(orch, repair_iteration_id, progress, task)
                
        else:
            progress.update(task, description="❌ Repair failed")
            console.print(f"[red]Repair failed: {result.error_details or 'Unknown error'}[/red]")
            
            if result.decision == "rebuild":
                console.print("[yellow]💡 Suggestion: Consider generating new code instead of repairing[/yellow]")


@cli.command()
@click.option('--count', '-c', default=10, help='Number of iterations to keep')
@click.option('--force', is_flag=True, help='Force cleanup without confirmation')
@click.pass_context
def cleanup(ctx, count, force):
    """
    🧹 Cleanup old iterations and deployments
    
    Removes old iterations and stops unused deployments.
    """
    orch = get_orchestrator(ctx.obj['project_root'])
    
    if not force:
        console.print(f"[yellow]This will remove old iterations, keeping only the {count} most recent.[/yellow]")
        if not click.confirm("Continue?"):
            return
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        # Cleanup iterations
        task = progress.add_task("Cleaning up iterations...", total=None)
        removed_iterations = orch.iteration_manager.cleanup_old_iterations(count)
        
        # Cleanup deployments
        progress.update(task, description="Cleaning up deployments...")
        stopped_deployments = orch.deployment_manager.cleanup_old_deployments(count // 2)
        
        progress.update(task, description="✅ Cleanup completed")
    
    console.print(f"[green]Removed {len(removed_iterations)} old iterations[/green]")
    console.print(f"[green]Stopped {len(stopped_deployments)} old deployments[/green]")


@cli.command()
@click.pass_context
def status(ctx):
    """
    📊 Show project status and metrics
    
    Displays current iterations, deployments, and statistics.
    """
    orch = get_orchestrator(ctx.obj['project_root'])
    
    # Iterations table
    iterations_table = Table(title="📁 Iterations")
    iterations_table.add_column("ID", style="cyan")
    iterations_table.add_column("Type", style="magenta")
    iterations_table.add_column("Status", style="green")
    iterations_table.add_column("Description", style="white")
    iterations_table.add_column("Created", style="dim")
    
    for iteration_id, info in orch.iteration_manager.iterations.items():
        iterations_table.add_row(
            iteration_id,
            info.generation_type,
            info.status,
            info.description[:50] + "..." if len(info.description) > 50 else info.description,
            info.timestamp.strftime("%Y-%m-%d %H:%M")
        )
    
    console.print(iterations_table)
    
    # Deployments table
    deployments = orch.deployment_manager.list_active_deployments()
    if deployments:
        deployments_table = Table(title="🐳 Active Deployments")
        deployments_table.add_column("Iteration", style="cyan")
        deployments_table.add_column("Container", style="blue")
        deployments_table.add_column("Status", style="green")
        deployments_table.add_column("Port", style="yellow")
        deployments_table.add_column("Health", style="red")
        
        for deployment in deployments:
            port = list(deployment.port_mappings.values())[0] if deployment.port_mappings else "N/A"
            deployments_table.add_row(
                deployment.iteration_id,
                deployment.container_name,
                deployment.status,
                str(port),
                deployment.health_status
            )
        
        console.print(deployments_table)
    
    # Statistics
    total_iterations = len(orch.iteration_manager.iterations)
    active_deployments = len(deployments)
    latest_iteration = orch.iteration_manager.get_latest_iteration()
    
    stats_panel = Panel(
        f"📊 Total Iterations: [cyan]{total_iterations}[/cyan]\n"
        f"🐳 Active Deployments: [green]{active_deployments}[/green]\n"
        f"🔄 Latest Iteration: [yellow]{latest_iteration or 'None'}[/yellow]",
        title="Project Statistics"
    )
    
    console.print(stats_panel)


@cli.command()
@click.option('--name', '-n', help='Project name')
@click.option('--framework', '-f', default='fastapi', help='Default framework')
@click.option('--language', '-l', default='python', help='Default language')
@click.option('--template', '-t', help='Project template to use')
@click.option('--force', is_flag=True, help='Force initialization even if directory exists')
@click.pass_context
def init(ctx, name, framework, language, template, force):
    """
    🌱 Initialize new COVAL project
    
    Creates project structure, config files, and initial setup.
    """
    orch = get_orchestrator(ctx.obj['project_root'])
    project_root = Path(ctx.obj['project_root']).absolute()
    
    # Determine project name
    if not name:
        name = project_root.name
    
    console.print(f"🌱 Initializing COVAL project: [cyan]{name}[/cyan]")
    
    # Check if already initialized
    coval_config = project_root / "coval.config.yaml"
    iterations_dir = project_root / "iterations"
    
    if (coval_config.exists() or iterations_dir.exists()) and not force:
        console.print("[yellow]⚠️  Project appears to already be initialized.[/yellow]")
        console.print("Use --force to reinitialize or choose a different directory.")
        return
    
    try:
        # Create project structure
        console.print("📁 Creating project structure...")
        
        # Essential directories
        (project_root / "iterations").mkdir(exist_ok=True)
        (project_root / "logs").mkdir(exist_ok=True)
        (project_root / "repairs").mkdir(exist_ok=True)
        (project_root / "configs").mkdir(exist_ok=True)
        (project_root / "templates").mkdir(exist_ok=True)
        
        # Copy configuration templates
        console.print("⚙️  Setting up configuration files...")
        
        package_config_dir = Path(__file__).parent / "config"
        
        # Copy COVAL config template
        if (package_config_dir / "coval.config.yaml").exists():
            import shutil
            shutil.copy2(
                package_config_dir / "coval.config.yaml",
                project_root / "coval.config.yaml"
            )
            
            # Update project name in config
            config_content = (project_root / "coval.config.yaml").read_text()
            config_content = config_content.replace(
                'name: "my-coval-project"',
                f'name: "{name}"'
            )
            config_content = config_content.replace(
                'framework: "auto-detect"',
                f'framework: "{framework}"'
            )
            config_content = config_content.replace(
                'language: "auto-detect"',
                f'language: "{language}"'
            )
            (project_root / "coval.config.yaml").write_text(config_content)
        
        # Copy LLM config
        if (package_config_dir / "llm.config.yaml").exists():
            shutil.copy2(
                package_config_dir / "llm.config.yaml", 
                project_root / "configs" / "llm.config.yaml"
            )
        
        # Create .gitignore
        console.print("📝 Creating .gitignore...")
        gitignore = project_root / ".gitignore"
        gitignore.write_text('''
# COVAL
iterations/*/
logs/*.log
repairs/*/
.coval_cache/
*.coval.tmp

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual environments
venv/
env/
ENV/

# IDEs
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Docker
.dockerignore
'''.strip())
        
        # Create README template
        console.print("📖 Creating project README...")
        readme = project_root / "README.md"
        readme.write_text(f'''# {name}

A COVAL project for intelligent code generation, execution, and repair.

## Quick Start

```bash
# Generate new code
coval generate -d "Your project description"

# Deploy iteration
coval run

# Check status
coval status

# Repair issues
coval repair -e error.log
```

## Project Structure

- `iterations/` - Generated code iterations
- `logs/` - System and deployment logs
- `repairs/` - Repair history and analysis
- `configs/` - LLM and system configurations
- `coval.config.yaml` - Main project configuration

## Configuration

- **Framework**: {framework}
- **Language**: {language}
- **COVAL Version**: 2.0

## Next Steps

1. Review `coval.config.yaml` for project settings
2. Customize `configs/llm.config.yaml` for LLM preferences  
3. Start generating code with `coval generate`

Generated by COVAL v2.0 🤖
''')
        
        # Create initial project template if specified
        if template:
            console.print(f"🎨 Setting up {template} template...")
            _create_project_template(project_root, template, framework, language)
        
        # Initialize first iteration if requested
        console.print("🚀 Creating initial iteration...")
        initial_iteration = orch.iteration_manager.create_iteration(
            description=f"Initial {name} project setup",
            generation_type="init"
        )
        
        # Success message
        success_panel = Panel(
            f"🎉 COVAL project initialized successfully!\n\n"
            f"📁 Project: [cyan]{name}[/cyan]\n"
            f"🏗️  Framework: [yellow]{framework}[/yellow]\n"
            f"🔤 Language: [blue]{language}[/blue]\n"
            f"📋 Initial iteration: [green]{initial_iteration}[/green]\n\n"
            f"Next steps:\n"
            f"• Review coval.config.yaml\n"
            f"• Run: coval generate -d \"Your project idea\"\n"
            f"• Check: coval status",
            title="✨ Project Initialized",
            border_style="green"
        )
        
        console.print(success_panel)
        
    except Exception as e:
        console.print(f"[red]❌ Initialization failed: {e}[/red]")
        raise


@cli.command()
@click.option('--iteration', '-i', help='Iteration ID to stop (default: all)')
@click.pass_context
def stop(ctx, iteration):
    """
    🛑 Stop running deployments
    
    Stops Docker containers and cleans up resources.
    """
    orch = get_orchestrator(ctx.obj['project_root'])
    
    if iteration:
        # Stop specific iteration
        if orch.deployment_manager.stop_deployment(iteration):
            console.print(f"[green]✅ Stopped deployment: {iteration}[/green]")
        else:
            console.print(f"[red]❌ Failed to stop deployment: {iteration}[/red]")
    else:
        # Stop all deployments
        deployments = orch.deployment_manager.list_active_deployments()
        stopped_count = 0
        
        for deployment in deployments:
            if orch.deployment_manager.stop_deployment(deployment.iteration_id):
                stopped_count += 1
        
        console.print(f"[green]✅ Stopped {stopped_count} deployments[/green]")


# Helper functions

def _create_project_template(project_root: Path, template: str, framework: str, language: str):
    """Create initial project template files."""
    
    template_dir = project_root / "templates" / template
    template_dir.mkdir(parents=True, exist_ok=True)
    
    if template == "fastapi" and language == "python":
        # Create basic FastAPI template
        main_py = template_dir / "main.py"
        main_py.write_text('''
from fastapi import FastAPI

app = FastAPI(title="COVAL Generated API", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "Hello from COVAL FastAPI!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''.strip())
        
        requirements = template_dir / "requirements.txt"
        requirements.write_text('''
fastapi==0.104.1
uvicorn==0.24.0
'''.strip())
        
    elif template == "flask" and language == "python":
        # Create basic Flask template
        app_py = template_dir / "app.py"
        app_py.write_text('''
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def hello():
    return jsonify({"message": "Hello from COVAL Flask!"})

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
'''.strip())
        
        requirements = template_dir / "requirements.txt"
        requirements.write_text('''
Flask==2.3.3
'''.strip())
    
    elif template == "express" and language == "javascript":
        # Create basic Express template
        server_js = template_dir / "server.js"
        server_js.write_text('''
const express = require('express');
const app = express();
const port = process.env.PORT || 3000;

app.use(express.json());

app.get('/', (req, res) => {
    res.json({ message: 'Hello from COVAL Express!' });
});

app.get('/health', (req, res) => {
    res.json({ status: 'healthy' });
});

app.listen(port, () => {
    console.log(`Server running at http://localhost:${port}`);
});
'''.strip())
        
        package_json = template_dir / "package.json"
        package_json.write_text('''{
    "name": "coval-express-app",
    "version": "1.0.0",
    "description": "COVAL generated Express.js application",
    "main": "server.js",
    "scripts": {
        "start": "node server.js",
        "dev": "nodemon server.js"
    },
    "dependencies": {
        "express": "^4.18.2"
    },
    "devDependencies": {
        "nodemon": "^3.0.1"
    }
}''')


def _deploy_iteration(orch: COVALOrchestrator, iteration_id: str, progress, task):
    """Deploy an iteration with progress tracking."""
    try:
        iteration_path = orch.iteration_manager.get_iteration_path(iteration_id)
        
        # Get parent iterations for overlay
        parent_iterations = []
        iteration_info = orch.iteration_manager.iterations.get(iteration_id)
        if iteration_info and iteration_info.parent_iteration:
            parent_iterations = [iteration_info.parent_iteration]
        
        # Create deployment
        deployment_status = orch.deployment_manager.create_transparent_deployment(
            iteration_id=iteration_id,
            iteration_path=iteration_path,
            parent_iterations=parent_iterations
        )
        
        # Update iteration status
        orch.iteration_manager.update_iteration_status(
            iteration_id,
            'deployed',
            docker_status='running'
        )
        
        port = list(deployment_status.port_mappings.values())[0] if deployment_status.port_mappings else 8000
        
        progress.update(task, description=f"✅ Deployed at http://localhost:{port}")
        
        deployment_panel = Panel(
            f"🚀 Deployment successful!\n"
            f"📁 Iteration: [cyan]{iteration_id}[/cyan]\n"
            f"🐳 Container: [blue]{deployment_status.container_name}[/blue]\n"
            f"🌐 URL: [green]http://localhost:{port}[/green]\n"
            f"📊 Status: [yellow]{deployment_status.status}[/yellow]",
            title="Deployment Info"
        )
        
        console.print(deployment_panel)
        
    except Exception as e:
        progress.update(task, description="❌ Deployment failed")
        console.print(f"[red]Deployment failed: {e}[/red]")


def _display_generation_results(result, iteration_id: str):
    """Display code generation results."""
    files_count = len(result.generated_files)
    tests_count = len(result.tests)
    
    result_panel = Panel(
        f"🤖 Code generation completed!\n"
        f"📁 Iteration: [cyan]{iteration_id}[/cyan]\n"
        f"📄 Files generated: [green]{files_count}[/green]\n"
        f"🧪 Test files: [blue]{tests_count}[/blue]\n"
        f"🔧 Model used: [yellow]{result.model_used}[/yellow]\n"
        f"📊 Confidence: [magenta]{result.confidence_score:.1%}[/magenta]\n"
        f"⏱️  Time: [dim]{result.execution_time:.2f}s[/dim]",
        title="Generation Results"
    )
    
    console.print(result_panel)
    
    if result.generated_files:
        files_table = Table(title="📄 Generated Files")
        files_table.add_column("Filename", style="cyan")
        files_table.add_column("Size", style="dim")
        
        for filename in result.generated_files.keys():
            size = len(result.generated_files[filename])
            files_table.add_row(filename, f"{size} chars")
        
        console.print(files_table)


def _display_repair_analysis(metrics, iteration_id: str):
    """Display repair analysis results."""
    analysis_panel = Panel(
        f"🔍 Repair Analysis for [cyan]{iteration_id}[/cyan]\n\n"
        f"📊 Technical Debt: [red]{metrics.technical_debt:.1f}[/red]\n"
        f"🧪 Test Coverage: [green]{metrics.test_coverage:.1%}[/green]\n"
        f"📋 Available Context: [blue]{metrics.available_context:.1%}[/blue]\n"
        f"🤖 Model Capability: [magenta]{metrics.model_capability:.1%}[/magenta]\n"
        f"📈 Historical Success: [yellow]{metrics.historical_success_rate:.1%}[/yellow]\n"
        f"🏷️  Problem Category: [cyan]{metrics.problem_category}[/cyan]",
        title="Repair Analysis"
    )
    
    console.print(analysis_panel)


def _get_model_enum(model_name: str) -> LLMModel:
    """Convert model name to enum."""
    model_mapping = {
        'qwen': LLMModel.QWEN_CODER,
        'deepseek': LLMModel.DEEPSEEK_CODER,
        'codellama13b': LLMModel.CODELLAMA_13B,
        'deepseek-r1': LLMModel.DEEPSEEK_R1,
        'granite': LLMModel.GRANITE_CODE,
        'mistral': LLMModel.MISTRAL
    }
    return model_mapping.get(model_name, LLMModel.QWEN_CODER)


# Entry points for console scripts
def main():
    """Main CLI entry point."""
    cli()


def generate_command():
    """Generate command entry point."""
    cli(['generate'])


def run_command():
    """Run command entry point."""
    cli(['run'])


def repair_command():
    """Repair command entry point."""
    cli(['repair'])


def iterate_command():
    """Iterate command entry point (alias for generate with parent)."""
    cli(['generate'])


if __name__ == '__main__':
    main()

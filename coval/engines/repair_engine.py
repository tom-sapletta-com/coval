#!/usr/bin/env python3
"""
COVAL Repair Engine

Integrates the existing repair.py functionality into the COVAL package structure.
Provides intelligent code repair with adaptive evaluation and multiple LLM models.
"""

import os
import json
import yaml
import math
import logging
import subprocess
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class LLMModel(Enum):
    """Available LLM models for repair."""
    QWEN_CODER = "qwen2.5-coder:7b"
    DEEPSEEK_CODER = "deepseek-coder:6.7b"
    CODELLAMA_13B = "codellama:13b"
    DEEPSEEK_R1 = "deepseek-r1:7b"
    GRANITE_CODE = "granite-code:8b"
    MISTRAL = "mistral:7b"


@dataclass
class RepairMetrics:
    """Metrics for repair decision making."""
    technical_debt: float
    test_coverage: float
    available_context: float
    model_capability: float
    historical_success_rate: float
    problem_category: str
    alpha: float = 0.4
    beta: float = 0.3
    gamma_prime: float = 0.5
    delta: float = 0.2
    eta: float = 0.15


@dataclass
class RepairResult:
    """Result of a repair operation."""
    success: bool
    patch_path: Optional[str]
    iterations_needed: int
    execution_time: float
    decision: str
    error_details: Optional[str]
    model_used: str
    historical_success_rate: float
    problem_category: str


class RepairEngine:
    """
    Intelligent code repair engine with adaptive evaluation.
    
    Features:
    - Multiple LLM model support with dynamic capability calculation
    - Adaptive evaluation based on historical success rates
    - Problem categorization and specialized handling
    - Automatic model downloading and management
    - Integration with COVAL iteration system
    """
    
    def __init__(self, 
                 model: LLMModel = LLMModel.QWEN_CODER,
                 config_path: Optional[str] = None,
                 max_iterations: int = 5):
        self.model = model
        self.config_path = config_path or "llm.config.yaml"
        self.max_iterations = max_iterations
        
        # Load configuration
        self.config = self._load_config()
        self.model_config = self._get_model_config()
        
        # Repair history for adaptive evaluation
        self.history_file = Path("repairs/repair_history.json")
        self.history_file.parent.mkdir(exist_ok=True)
        
        # Setup logging
        self._setup_logging()
        
        # Ensure model is available
        self._ensure_model_available()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load repair configuration."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    logger.info(f"✅ Loaded configuration from: {self.config_path}")
                    return config
            except Exception as e:
                logger.warning(f"Failed to load config: {e}")
        
        # Return default configuration
        return {
            'global': {
                'timeout': 60,
                'max_iterations': 5,
                'adaptive_evaluation': {
                    'enabled': True,
                    'history_weight': 0.3,
                    'decay_factor': 0.9,
                    'min_samples': 5
                },
                'capability_calculation': {
                    'token_bonus_multiplier': 0.0001,
                    'temperature_penalty': 0.2,
                    'context_bonus_multiplier': 0.0001,
                    'max_capability': 0.95
                }
            },
            'models': {
                'qwen2.5-coder': {
                    'model_name': 'qwen2.5-coder:7b',
                    'max_tokens': 16384,
                    'temperature': 0.2,
                    'base_capability': 0.85,
                    'context_window': 32768,
                    'retry_attempts': 3
                }
            }
        }
    
    def _get_model_config(self) -> Dict[str, Any]:
        """Get configuration for the current model."""
        model_key = self._get_model_key()
        return self.config.get('models', {}).get(model_key, {})
    
    def _get_model_key(self) -> str:
        """Get configuration key for current model."""
        model_mapping = {
            LLMModel.QWEN_CODER: 'qwen2.5-coder',
            LLMModel.DEEPSEEK_CODER: 'deepseek-coder',
            LLMModel.CODELLAMA_13B: 'codellama',
            LLMModel.DEEPSEEK_R1: 'deepseek-r1',
            LLMModel.GRANITE_CODE: 'granite-code',
            LLMModel.MISTRAL: 'mistral'
        }
        return model_mapping.get(self.model, 'qwen2.5-coder')
    
    def _setup_logging(self):
        """Setup logging for repair engine."""
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    def _ensure_model_available(self) -> bool:
        """Ensure the LLM model is available locally."""
        model_name = self.model.value
        logger.info(f"🔍 Checking model availability: {model_name}")
        
        try:
            result = subprocess.run(
                ["ollama", "list"], 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            if result.returncode == 0 and model_name in result.stdout:
                logger.info(f"✅ Model {model_name} is available")
                return True
            
            logger.info(f"📥 Pulling model: {model_name}")
            pull_result = subprocess.run(
                ["ollama", "pull", model_name],
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if pull_result.returncode == 0:
                logger.info(f"✅ Successfully pulled model: {model_name}")
                return True
            else:
                logger.error(f"❌ Failed to pull model: {pull_result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"⏱️ Timeout pulling model: {model_name}")
            return False
        except FileNotFoundError:
            logger.error("❌ Ollama not installed or not in PATH")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            return False
    
    def _get_model_capability(self, problem_category: str = "general") -> float:
        """Calculate dynamic model capability based on configuration and history."""
        base_capability = self.model_config.get('base_capability', 0.5)
        max_tokens = self.model_config.get('max_tokens', 8192)
        temperature = self.model_config.get('temperature', 0.2)
        context_window = self.model_config.get('context_window', 8192)
        
        # Get calculation parameters
        calc_config = self.config.get('global', {}).get('capability_calculation', {})
        
        # Calculate dynamic bonuses/penalties
        token_bonus = max(0, max_tokens - 8192) * calc_config.get('token_bonus_multiplier', 0.0001)
        temp_penalty = temperature * calc_config.get('temperature_penalty', 0.2)
        context_bonus = max(0, context_window - 8192) * calc_config.get('context_bonus_multiplier', 0.0001)
        
        # Historical success bonus
        historical_bonus = self._get_historical_success_rate(problem_category) * 0.1
        
        # Calculate final capability
        final_capability = base_capability + token_bonus - temp_penalty + context_bonus + historical_bonus
        
        # Cap at maximum
        max_cap = calc_config.get('max_capability', 0.95)
        return min(final_capability, max_cap)
    
    def _get_historical_success_rate(self, problem_category: str) -> float:
        """Get historical success rate for a specific problem category."""
        if not self.history_file.exists():
            return 0.0
        
        try:
            with open(self.history_file, 'r') as f:
                history = json.load(f)
            
            category_attempts = [
                attempt for attempt in history
                if attempt.get('problem_category') == problem_category
            ]
            
            if len(category_attempts) < self.config.get('global', {}).get('adaptive_evaluation', {}).get('min_samples', 5):
                return 0.0
            
            # Calculate weighted success rate with decay factor
            decay_factor = self.config.get('global', {}).get('adaptive_evaluation', {}).get('decay_factor', 0.9)
            weighted_success = 0.0
            total_weight = 0.0
            
            for i, attempt in enumerate(reversed(category_attempts)):
                weight = decay_factor ** i
                success = 1.0 if attempt.get('success', False) else 0.0
                weighted_success += success * weight
                total_weight += weight
            
            return weighted_success / total_weight if total_weight > 0 else 0.0
            
        except Exception as e:
            logger.warning(f"Could not load repair history: {e}")
            return 0.0
    
    def _categorize_problem(self, error_content: str) -> str:
        """Categorize the problem based on error content."""
        error_lower = error_content.lower()
        
        # Define categories with keywords
        categories = {
            'import_error': ['import', 'module', 'modulenotfounderror', 'importerror'],
            'syntax_error': ['syntax', 'syntaxerror', 'invalid syntax', 'unexpected token'],
            'type_error': ['type', 'typeerror', 'attribute', 'attributeerror'],
            'runtime_error': ['runtime', 'runtimeerror', 'exception', 'error:'],
            'docker_error': ['docker', 'container', 'dockerfile', 'compose'],
            'dependency_error': ['dependency', 'package', 'requirement', 'pip', 'npm'],
            'config_error': ['config', 'configuration', 'settings', 'environment'],
            'network_error': ['network', 'connection', 'timeout', 'socket']
        }
        
        # Find matching category
        for category, keywords in categories.items():
            if any(keyword in error_lower for keyword in keywords):
                return category
        
        return 'other'
    
    def triage(self, 
               error_file: Path, 
               source_dir: Path, 
               test_file: Optional[Path] = None) -> RepairMetrics:
        """
        Perform triage analysis of the repair situation.
        
        Args:
            error_file: Path to error log file
            source_dir: Path to source code directory
            test_file: Optional path to test file
            
        Returns:
            RepairMetrics with analysis results
        """
        logger.info("🔍 Starting triage analysis...")
        
        # Read error content
        try:
            with open(error_file, 'r', encoding='utf-8') as f:
                error_content = f.read()
        except Exception as e:
            logger.error(f"Could not read error file: {e}")
            error_content = ""
        
        # Categorize problem
        problem_category = self._categorize_problem(error_content)
        
        # Calculate metrics
        technical_debt = self._calculate_technical_debt(source_dir)
        test_coverage = self._calculate_test_coverage(source_dir, test_file)
        available_context = self._calculate_available_context(error_content, source_dir)
        model_capability = self._get_model_capability(problem_category)
        historical_success_rate = self._get_historical_success_rate(problem_category)
        
        metrics = RepairMetrics(
            technical_debt=technical_debt,
            test_coverage=test_coverage,
            available_context=available_context,
            model_capability=model_capability,
            historical_success_rate=historical_success_rate,
            problem_category=problem_category
        )
        
        # Log metrics
        logger.info("📊 Triage metrics:")
        logger.info(f"  - Technical debt: {technical_debt:.2f}")
        logger.info(f"  - Test coverage: {test_coverage:.2%}")
        logger.info(f"  - Available context: {available_context:.2%}")
        logger.info(f"  - Model capability: {model_capability:.2%}")
        logger.info(f"  - Historical success rate: {historical_success_rate:.2%}")
        logger.info(f"  - Problem category: {problem_category}")
        
        return metrics
    
    def _calculate_technical_debt(self, source_dir: Path) -> float:
        """Calculate technical debt score."""
        debt_score = 0.0
        
        # Check for common debt indicators
        for file_path in source_dir.rglob('*.py'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # TODO comments indicate debt
                debt_score += content.lower().count('todo') * 0.5
                debt_score += content.lower().count('fixme') * 1.0
                debt_score += content.lower().count('hack') * 1.5
                
                # Long functions indicate complexity
                function_matches = re.findall(r'def \w+\([^)]*\):', content)
                if len(function_matches) > 0:
                    avg_function_length = len(content.split('\n')) / len(function_matches)
                    if avg_function_length > 50:
                        debt_score += 2.0
                        
            except Exception:
                continue
        
        return min(debt_score, 100.0)  # Cap at 100
    
    def _calculate_test_coverage(self, source_dir: Path, test_file: Optional[Path]) -> float:
        """Calculate test coverage estimate."""
        if not test_file or not test_file.exists():
            return 0.0
        
        try:
            # Count source files
            source_files = list(source_dir.rglob('*.py'))
            if not source_files:
                return 0.0
            
            # Count test files
            test_files = list(source_dir.rglob('test_*.py'))
            test_files.extend(source_dir.rglob('*_test.py'))
            
            # Simple estimation based on file ratio
            coverage_estimate = min(len(test_files) / len(source_files), 1.0)
            
            return coverage_estimate
            
        except Exception:
            return 0.0
    
    def _calculate_available_context(self, error_content: str, source_dir: Path) -> float:
        """Calculate available context for repair."""
        context_score = 0.0
        
        # Error content provides context
        if error_content:
            context_score += 0.3
            
            # Stack trace provides more context
            if 'traceback' in error_content.lower() or 'stack trace' in error_content.lower():
                context_score += 0.2
        
        # Source code availability
        source_files = list(source_dir.rglob('*.py'))
        if source_files:
            context_score += 0.3
            
            # More files = more context (with diminishing returns)
            file_bonus = min(len(source_files) / 10, 0.2)
            context_score += file_bonus
        
        return min(context_score, 1.0)
    
    def repair(self,
               error_file: Path,
               source_dir: Path,
               test_file: Optional[Path] = None,
               ticket_id: Optional[str] = None) -> RepairResult:
        """
        Perform intelligent code repair.
        
        Args:
            error_file: Path to error log file
            source_dir: Path to source code directory  
            test_file: Optional path to test file
            ticket_id: Optional ticket ID for tracking
            
        Returns:
            RepairResult with repair outcome
        """
        start_time = datetime.now()
        
        # Perform triage
        metrics = self.triage(error_file, source_dir, test_file)
        
        # Make repair decision
        decision, success_prob, analysis = self._make_repair_decision(metrics)
        
        if decision == "rebuild":
            logger.warning("🔄 Rebuild recommended instead of repair")
            return RepairResult(
                success=False,
                patch_path=None,
                iterations_needed=0,
                execution_time=(datetime.now() - start_time).total_seconds(),
                decision="rebuild",
                error_details="Cost analysis suggests rebuild is more efficient",
                model_used=self.model.value,
                historical_success_rate=metrics.historical_success_rate,
                problem_category=metrics.problem_category
            )
        
        # Attempt repair
        logger.info(f"🔧 Starting repair with {self.model.value}")
        logger.info(f"📊 Success probability: {success_prob:.2%}")
        
        # Create repair directory
        repair_id = ticket_id or f"repair-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        repair_dir = Path("repairs") / repair_id
        repair_dir.mkdir(parents=True, exist_ok=True)
        
        # Perform repair iterations
        success = False
        patch_path = None
        iterations = 0
        
        for iteration in range(self.max_iterations):
            iterations += 1
            logger.info(f"🔄 Repair iteration {iteration + 1}/{self.max_iterations}")
            
            # Simulate repair process (in real implementation, this would call LLM)
            if self._attempt_repair_iteration(error_file, source_dir, repair_dir, iteration):
                success = True
                patch_path = str(repair_dir / f"patch_{iteration}.diff")
                break
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Record repair attempt for historical tracking
        self._record_repair_attempt(
            success=success,
            problem_category=metrics.problem_category,
            model_used=self.model.value,
            execution_time=execution_time,
            iterations_needed=iterations
        )
        
        return RepairResult(
            success=success,
            patch_path=patch_path,
            iterations_needed=iterations,
            execution_time=execution_time,
            decision="repair",
            error_details=None,
            model_used=self.model.value,
            historical_success_rate=metrics.historical_success_rate,
            problem_category=metrics.problem_category
        )
    
    def _make_repair_decision(self, metrics: RepairMetrics) -> Tuple[str, float, Dict[str, Any]]:
        """Make repair vs rebuild decision."""
        # Calculate success probability using logistic function
        success_prob = self._calculate_success_probability(metrics)
        
        # Calculate costs
        repair_cost = self._calculate_repair_cost(metrics, success_prob)
        rebuild_cost = self._calculate_rebuild_cost(metrics)
        
        # Make decision
        cost_ratio = repair_cost / rebuild_cost if rebuild_cost > 0 else float('inf')
        
        if cost_ratio > 2.0 or success_prob < 0.3:
            decision = "rebuild"
        else:
            decision = "repair"
        
        analysis = {
            'repair_cost': repair_cost,
            'rebuild_cost': rebuild_cost,
            'cost_ratio': cost_ratio,
            'success_probability': success_prob
        }
        
        return decision, success_prob, analysis
    
    def _calculate_success_probability(self, metrics: RepairMetrics) -> float:
        """Calculate success probability using logistic function."""
        d_norm = min(metrics.technical_debt / 100, 1.0)
        x = (
            metrics.alpha * metrics.available_context +
            metrics.beta * metrics.test_coverage +
            metrics.gamma_prime * metrics.model_capability +
            metrics.eta * metrics.historical_success_rate -
            metrics.delta * d_norm
        )
        probability = 1 / (1 + math.exp(-x))
        return probability
    
    def _calculate_repair_cost(self, metrics: RepairMetrics, success_prob: float) -> float:
        """Calculate cost of repair attempt."""
        base_cost = 50.0
        complexity_multiplier = 1 + (metrics.technical_debt / 100)
        success_multiplier = 1 / max(success_prob, 0.1)
        
        return base_cost * complexity_multiplier * success_multiplier
    
    def _calculate_rebuild_cost(self, metrics: RepairMetrics) -> float:
        """Calculate cost of rebuilding."""
        base_rebuild_cost = 200.0
        context_multiplier = 1 - (metrics.available_context * 0.5)
        
        return base_rebuild_cost * context_multiplier
    
    def _attempt_repair_iteration(self, 
                                 error_file: Path, 
                                 source_dir: Path, 
                                 repair_dir: Path, 
                                 iteration: int) -> bool:
        """Attempt a single repair iteration."""
        # Simulate repair logic - in real implementation this would:
        # 1. Generate repair prompt based on error and source code
        # 2. Call LLM to generate fix
        # 3. Apply fix to source code
        # 4. Validate fix
        # 5. Return success/failure
        
        # For now, simulate with decreasing probability based on model capability
        import random
        success_threshold = self.model_config.get('base_capability', 0.7) - (iteration * 0.1)
        return random.random() < success_threshold
    
    def _record_repair_attempt(self, 
                              success: bool, 
                              problem_category: str, 
                              model_used: str,
                              execution_time: float, 
                              iterations_needed: int):
        """Record repair attempt for historical tracking."""
        attempt = {
            'timestamp': datetime.now().isoformat(),
            'success': success,
            'problem_category': problem_category,
            'model_used': model_used,
            'execution_time': execution_time,
            'iterations_needed': iterations_needed
        }
        
        # Load existing history
        history = []
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    history = json.load(f)
            except Exception:
                pass
        
        # Add new attempt
        history.append(attempt)
        
        # Keep only recent attempts (last 1000)
        history = history[-1000:]
        
        # Save updated history
        try:
            with open(self.history_file, 'w') as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save repair history: {e}")
    
    def get_repair_statistics(self) -> Dict[str, Any]:
        """Get repair statistics from history."""
        if not self.history_file.exists():
            return {}
        
        try:
            with open(self.history_file, 'r') as f:
                history = json.load(f)
            
            if not history:
                return {}
            
            # Calculate overall stats
            total_attempts = len(history)
            successful_attempts = sum(1 for attempt in history if attempt.get('success', False))
            overall_success_rate = successful_attempts / total_attempts if total_attempts > 0 else 0.0
            
            # Calculate stats by category
            category_stats = {}
            for attempt in history:
                category = attempt.get('problem_category', 'unknown')
                if category not in category_stats:
                    category_stats[category] = {'total': 0, 'successful': 0}
                
                category_stats[category]['total'] += 1
                if attempt.get('success', False):
                    category_stats[category]['successful'] += 1
            
            # Calculate success rates by category
            for category, stats in category_stats.items():
                stats['success_rate'] = stats['successful'] / stats['total'] if stats['total'] > 0 else 0.0
            
            return {
                'total_attempts': total_attempts,
                'successful_attempts': successful_attempts,
                'overall_success_rate': overall_success_rate,
                'category_stats': category_stats,
                'average_execution_time': sum(attempt.get('execution_time', 0) for attempt in history) / total_attempts if total_attempts > 0 else 0.0
            }
            
        except Exception as e:
            logger.warning(f"Could not load repair statistics: {e}")
            return {}

#!/usr/bin/env python3
"""
COVAL Cost Calculator

Calculates costs and optimal strategies for code modification vs generation.
Helps decide whether to repair existing code or generate new iterations.
"""

import math
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class CostMetrics:
    """Metrics used for cost calculation."""
    lines_of_code: int
    complexity_score: float
    technical_debt: float
    test_coverage: float
    dependencies_count: int
    modification_scope: float  # 0.0 to 1.0, how much needs to change
    historical_success_rate: float
    iteration_count: int
    framework_maturity: float
    team_familiarity: float


@dataclass
class CostEstimate:
    """Cost estimation result."""
    modify_cost: float
    generate_cost: float
    recommended_action: str  # 'modify', 'generate', 'hybrid'
    confidence: float
    reasoning: List[str]
    risk_factors: List[str]
    estimated_time_hours: float
    success_probability: float


class CostCalculator:
    """
    Calculates the optimal strategy for code changes.
    
    Considers factors like:
    - Code complexity and technical debt
    - Scope of required changes
    - Historical success rates
    - Framework and team factors
    - Time and resource constraints
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._default_config()
        
        # Cost factors from configuration
        self.modify_base_cost = self.config['costs']['modify_base_cost']
        self.generate_base_cost = self.config['costs']['generate_base_cost']
        self.complexity_multiplier = self.config['costs']['complexity_multiplier']
        self.debt_penalty = self.config['costs']['debt_penalty']
        self.scope_multiplier = self.config['costs']['scope_multiplier']
        
        # Thresholds
        self.modify_threshold = self.config['thresholds']['prefer_modify_below']
        self.generate_threshold = self.config['thresholds']['prefer_generate_above']
        
    def _default_config(self) -> Dict[str, Any]:
        """Default cost calculation configuration."""
        return {
            'costs': {
                'modify_base_cost': 10.0,  # Base cost for modification
                'generate_base_cost': 25.0,  # Base cost for generation
                'complexity_multiplier': 2.0,
                'debt_penalty': 1.5,
                'scope_multiplier': 3.0,
                'dependency_factor': 0.5,
                'test_bonus': 0.8,  # Good tests reduce costs
            },
            'thresholds': {
                'prefer_modify_below': 0.3,  # If scope < 30%, prefer modify
                'prefer_generate_above': 0.7,  # If scope > 70%, prefer generate
                'high_debt_threshold': 50.0,
                'low_coverage_threshold': 0.4,
            },
            'weights': {
                'complexity': 0.25,
                'debt': 0.20,
                'scope': 0.30,
                'history': 0.15,
                'coverage': 0.10,
            }
        }
    
    def calculate_cost(self, metrics: CostMetrics) -> CostEstimate:
        """
        Calculate the optimal cost strategy.
        
        Args:
            metrics: Code and project metrics
            
        Returns:
            CostEstimate with recommendations
        """
        logger.info(f"Calculating costs for {metrics.lines_of_code} LOC project")
        
        # Calculate modification cost
        modify_cost = self._calculate_modify_cost(metrics)
        
        # Calculate generation cost
        generate_cost = self._calculate_generate_cost(metrics)
        
        # Determine recommendation
        cost_ratio = modify_cost / generate_cost if generate_cost > 0 else float('inf')
        recommendation = self._determine_recommendation(metrics, cost_ratio)
        
        # Calculate confidence and success probability
        confidence = self._calculate_confidence(metrics, cost_ratio)
        success_prob = self._calculate_success_probability(metrics, recommendation)
        
        # Generate reasoning and risk factors
        reasoning = self._generate_reasoning(metrics, modify_cost, generate_cost, recommendation)
        risk_factors = self._identify_risk_factors(metrics)
        
        # Estimate time
        estimated_time = self._estimate_time_hours(metrics, recommendation)
        
        return CostEstimate(
            modify_cost=modify_cost,
            generate_cost=generate_cost,
            recommended_action=recommendation,
            confidence=confidence,
            reasoning=reasoning,
            risk_factors=risk_factors,
            estimated_time_hours=estimated_time,
            success_probability=success_prob
        )
    
    def _calculate_modify_cost(self, metrics: CostMetrics) -> float:
        """Calculate the cost of modifying existing code."""
        base_cost = self.modify_base_cost
        
        # Scale by lines of code (with diminishing returns)
        loc_factor = math.log(max(metrics.lines_of_code, 1)) / math.log(1000)
        
        # Complexity penalty
        complexity_penalty = metrics.complexity_score * self.complexity_multiplier
        
        # Technical debt penalty
        debt_penalty = metrics.technical_debt * self.debt_penalty
        
        # Scope multiplier - more changes = higher cost
        scope_cost = metrics.modification_scope * self.scope_multiplier * base_cost
        
        # Dependencies penalty
        dep_penalty = math.sqrt(metrics.dependencies_count) * self.config['costs']['dependency_factor']
        
        # Test coverage bonus (good tests make modification safer/cheaper)
        test_bonus = (1 - metrics.test_coverage) * self.config['costs']['test_bonus']
        
        # Historical success bonus/penalty
        history_factor = 1.0 + (0.5 - metrics.historical_success_rate)
        
        total_cost = (
            base_cost + 
            loc_factor * 5 +
            complexity_penalty +
            debt_penalty +
            scope_cost +
            dep_penalty +
            test_bonus
        ) * history_factor
        
        return max(total_cost, 1.0)  # Minimum cost of 1.0
    
    def _calculate_generate_cost(self, metrics: CostMetrics) -> float:
        """Calculate the cost of generating new code."""
        base_cost = self.generate_base_cost
        
        # Scale by target size (estimated from existing code)
        size_factor = math.sqrt(metrics.lines_of_code) / 10
        
        # Framework maturity bonus (mature frameworks are easier to generate for)
        framework_bonus = (1 - metrics.framework_maturity) * 10
        
        # Team familiarity bonus
        familiarity_bonus = (1 - metrics.team_familiarity) * 8
        
        # Dependencies cost (need to recreate integrations)
        dep_cost = metrics.dependencies_count * 2
        
        # Iteration penalty (more iterations = higher cost due to context switching)
        iteration_penalty = metrics.iteration_count * 2
        
        # Test recreation cost
        test_recreation_cost = metrics.test_coverage * metrics.lines_of_code * 0.01
        
        total_cost = (
            base_cost +
            size_factor +
            framework_bonus +
            familiarity_bonus +
            dep_cost +
            iteration_penalty +
            test_recreation_cost
        )
        
        return max(total_cost, 5.0)  # Minimum cost of 5.0
    
    def _determine_recommendation(self, metrics: CostMetrics, cost_ratio: float) -> str:
        """Determine the recommended action based on metrics and cost ratio."""
        # Strong indicators for modification
        if (metrics.modification_scope < self.modify_threshold and 
            metrics.technical_debt < self.config['thresholds']['high_debt_threshold'] and
            metrics.test_coverage > self.config['thresholds']['low_coverage_threshold']):
            return 'modify'
        
        # Strong indicators for generation
        if (metrics.modification_scope > self.generate_threshold or
            metrics.technical_debt > self.config['thresholds']['high_debt_threshold'] * 1.5 or
            metrics.historical_success_rate < 0.3):
            return 'generate'
        
        # Cost-based decision
        if cost_ratio < 0.7:
            return 'modify'
        elif cost_ratio > 1.4:
            return 'generate'
        else:
            return 'hybrid'  # Consider hybrid approach
    
    def _calculate_confidence(self, metrics: CostMetrics, cost_ratio: float) -> float:
        """Calculate confidence in the recommendation."""
        confidence_factors = []
        
        # Strong cost difference increases confidence
        if cost_ratio < 0.5 or cost_ratio > 2.0:
            confidence_factors.append(0.9)
        elif 0.7 < cost_ratio < 1.3:
            confidence_factors.append(0.4)  # Close costs = low confidence
        else:
            confidence_factors.append(0.7)
        
        # Good test coverage increases confidence
        if metrics.test_coverage > 0.8:
            confidence_factors.append(0.8)
        elif metrics.test_coverage < 0.3:
            confidence_factors.append(0.3)
        else:
            confidence_factors.append(0.6)
        
        # Historical success rate
        confidence_factors.append(metrics.historical_success_rate)
        
        # Clear scope boundaries
        if metrics.modification_scope < 0.2 or metrics.modification_scope > 0.8:
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.5)
        
        return sum(confidence_factors) / len(confidence_factors)
    
    def _calculate_success_probability(self, metrics: CostMetrics, recommendation: str) -> float:
        """Calculate the probability of success for the recommendation."""
        base_prob = 0.7  # Base probability
        
        # Adjust based on recommendation type
        if recommendation == 'modify':
            # Modification success factors
            factors = [
                metrics.test_coverage,  # Good tests help
                1 - metrics.modification_scope,  # Smaller scope = higher success
                1 - (metrics.technical_debt / 100),  # Less debt = higher success
                metrics.historical_success_rate,  # Historical performance
            ]
        elif recommendation == 'generate':
            # Generation success factors
            factors = [
                metrics.framework_maturity,  # Mature frameworks
                metrics.team_familiarity,  # Team experience
                1 - (metrics.complexity_score / 10),  # Less complexity
                0.8,  # Fresh start bonus
            ]
        else:  # hybrid
            factors = [0.6, 0.6, 0.6]  # Moderate across the board
        
        # Weight and combine factors
        weighted_score = sum(f * 0.25 for f in factors)
        success_prob = base_prob * (0.5 + weighted_score)
        
        return min(max(success_prob, 0.1), 0.95)  # Clamp between 10% and 95%
    
    def _generate_reasoning(self, metrics: CostMetrics, modify_cost: float, 
                          generate_cost: float, recommendation: str) -> List[str]:
        """Generate human-readable reasoning for the recommendation."""
        reasoning = []
        
        cost_ratio = modify_cost / generate_cost if generate_cost > 0 else float('inf')
        
        # Cost comparison
        if cost_ratio < 0.8:
            reasoning.append(f"Modification is significantly cheaper ({modify_cost:.1f} vs {generate_cost:.1f})")
        elif cost_ratio > 1.2:
            reasoning.append(f"Generation is significantly cheaper ({generate_cost:.1f} vs {modify_cost:.1f})")
        else:
            reasoning.append(f"Costs are similar (modify: {modify_cost:.1f}, generate: {generate_cost:.1f})")
        
        # Scope analysis
        scope_pct = metrics.modification_scope * 100
        if scope_pct < 30:
            reasoning.append(f"Small scope of changes ({scope_pct:.0f}%) favors modification")
        elif scope_pct > 70:
            reasoning.append(f"Large scope of changes ({scope_pct:.0f}%) favors generation")
        else:
            reasoning.append(f"Medium scope of changes ({scope_pct:.0f}%)")
        
        # Technical debt
        if metrics.technical_debt > 50:
            reasoning.append(f"High technical debt ({metrics.technical_debt:.1f}) suggests fresh start")
        elif metrics.technical_debt < 20:
            reasoning.append(f"Low technical debt ({metrics.technical_debt:.1f}) supports modification")
        
        # Test coverage
        coverage_pct = metrics.test_coverage * 100
        if coverage_pct > 80:
            reasoning.append(f"Excellent test coverage ({coverage_pct:.0f}%) reduces modification risk")
        elif coverage_pct < 40:
            reasoning.append(f"Poor test coverage ({coverage_pct:.0f}%) increases modification risk")
        
        # Historical performance
        history_pct = metrics.historical_success_rate * 100
        if history_pct > 80:
            reasoning.append(f"Strong historical success rate ({history_pct:.0f}%)")
        elif history_pct < 50:
            reasoning.append(f"Weak historical success rate ({history_pct:.0f}%) suggests trying new approach")
        
        return reasoning
    
    def _identify_risk_factors(self, metrics: CostMetrics) -> List[str]:
        """Identify potential risk factors."""
        risks = []
        
        if metrics.technical_debt > 60:
            risks.append("Very high technical debt may cause unexpected issues")
        
        if metrics.test_coverage < 0.3:
            risks.append("Low test coverage increases chance of regressions")
        
        if metrics.complexity_score > 8:
            risks.append("High complexity makes changes unpredictable")
        
        if metrics.dependencies_count > 20:
            risks.append("Many dependencies increase integration risks")
        
        if metrics.modification_scope > 0.8:
            risks.append("Large scope changes are inherently risky")
        
        if metrics.historical_success_rate < 0.4:
            risks.append("Poor historical performance indicates systemic issues")
        
        if metrics.iteration_count > 10:
            risks.append("Many iterations suggest fundamental problems")
        
        if metrics.framework_maturity < 0.5:
            risks.append("Immature framework increases generation complexity")
        
        return risks
    
    def _estimate_time_hours(self, metrics: CostMetrics, recommendation: str) -> float:
        """Estimate time in hours for the recommended approach."""
        base_hours = {
            'modify': 4.0,
            'generate': 12.0,
            'hybrid': 8.0
        }
        
        hours = base_hours[recommendation]
        
        # Scale by size
        size_factor = math.log(max(metrics.lines_of_code, 100)) / math.log(1000)
        hours *= (0.5 + size_factor)
        
        # Complexity adjustment
        hours *= (1 + metrics.complexity_score / 10)
        
        # Scope adjustment (for modifications)
        if recommendation == 'modify':
            hours *= (0.5 + metrics.modification_scope)
        
        # Test coverage adjustment
        if metrics.test_coverage < 0.5:
            hours *= 1.3  # Need more testing time
        
        # Historical success adjustment
        if metrics.historical_success_rate < 0.5:
            hours *= 1.4  # More debugging/iteration time
        
        return round(hours, 1)
    
    def compare_iterations(self, iteration_metrics: List[Tuple[str, CostMetrics]]) -> Dict[str, Any]:
        """
        Compare multiple iterations and recommend the best strategy.
        
        Args:
            iteration_metrics: List of (iteration_id, metrics) tuples
            
        Returns:
            Comparison analysis with recommendations
        """
        analyses = {}
        
        for iteration_id, metrics in iteration_metrics:
            analyses[iteration_id] = self.calculate_cost(metrics)
        
        # Find best options
        best_modify = min(
            (id, analysis) for id, analysis in analyses.items() 
            if analysis.recommended_action == 'modify'
        ) if any(a.recommended_action == 'modify' for a in analyses.values()) else None
        
        best_generate = min(
            (id, analysis) for id, analysis in analyses.items()
            if analysis.recommended_action == 'generate'
        ) if any(a.recommended_action == 'generate' for a in analyses.values()) else None
        
        # Overall recommendation
        if best_modify and best_generate:
            if best_modify[1].modify_cost < best_generate[1].generate_cost:
                overall_rec = f"Modify iteration {best_modify[0]}"
            else:
                overall_rec = f"Generate new iteration"
        elif best_modify:
            overall_rec = f"Modify iteration {best_modify[0]}"
        elif best_generate:
            overall_rec = "Generate new iteration"
        else:
            overall_rec = "Consider hybrid approach"
        
        return {
            'analyses': analyses,
            'best_modify': best_modify,
            'best_generate': best_generate,
            'overall_recommendation': overall_rec,
            'total_iterations': len(iteration_metrics)
        }
    
    def get_optimization_suggestions(self, metrics: CostMetrics) -> List[str]:
        """Get suggestions for optimizing the codebase to reduce future costs."""
        suggestions = []
        
        if metrics.technical_debt > 40:
            suggestions.append("Refactor high-debt areas to reduce future modification costs")
        
        if metrics.test_coverage < 0.6:
            suggestions.append("Improve test coverage to reduce modification risks and costs")
        
        if metrics.complexity_score > 6:
            suggestions.append("Simplify complex components to reduce change impact")
        
        if metrics.dependencies_count > 15:
            suggestions.append("Consider consolidating or removing unnecessary dependencies")
        
        if metrics.historical_success_rate < 0.6:
            suggestions.append("Analyze past failures to improve future success rates")
        
        return suggestions

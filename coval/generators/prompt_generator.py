#!/usr/bin/env python3
"""
COVAL Prompt Generator

Handles creation of comprehensive prompts for LLM code generation.
Extracted from generation_engine.py for better modularity and testability.
"""

import logging
from typing import List, Dict, Optional
from ..models.generation_models import GenerationRequest

logger = logging.getLogger(__name__)


class PromptGenerator:
    """
    Generates comprehensive prompts for LLM code generation.
    
    Features:
    - Framework-specific prompt templates
    - Feature and constraint integration
    - Best practices and security considerations
    - Structured output formatting
    """
    
    def __init__(self):
        """Initialize the prompt generator."""
        self.setup_templates()
    
    def setup_templates(self):
        """Setup prompt templates for different frameworks."""
        self.framework_templates = {
            'fastapi': {
                'description': 'FastAPI REST API application',
                'default_features': ['authentication', 'database', 'validation', 'documentation'],
                'best_practices': [
                    'Use Pydantic models for request/response validation',
                    'Implement proper error handling with HTTP status codes',
                    'Add OpenAPI/Swagger documentation',
                    'Use dependency injection for database connections',
                    'Implement JWT token authentication'
                ]
            },
            'flask': {
                'description': 'Flask web application',
                'default_features': ['routing', 'templating', 'database', 'authentication'],
                'best_practices': [
                    'Use Flask-SQLAlchemy for database operations',
                    'Implement proper error handling',
                    'Use Flask-Login for session management',
                    'Add CSRF protection',
                    'Implement proper logging'
                ]
            },
            'express': {
                'description': 'Express.js web application',
                'default_features': ['routing', 'middleware', 'database', 'authentication'],
                'best_practices': [
                    'Use Express middleware for request processing',
                    'Implement proper error handling',
                    'Use JWT for authentication',
                    'Add input validation',
                    'Implement rate limiting'
                ]
            }
        }
    
    def create_generation_prompt(self, request: GenerationRequest) -> str:
        """
        Create a comprehensive prompt for code generation.
        
        Args:
            request: Generation request with requirements
            
        Returns:
            Formatted prompt string for LLM
        """
        logger.debug(f"Creating prompt for {request.framework} {request.language} application")
        
        prompt_parts = [
            self._create_header(request),
            self._create_requirements_section(request),
            self._create_features_section(request),
            self._create_constraints_section(request),
            self._create_best_practices_section(request),
            self._create_output_format_section(),
            self._create_examples_section(request),
            self._create_footer()
        ]
        
        # Filter out empty sections
        prompt_parts = [part for part in prompt_parts if part.strip()]
        
        return "\n\n".join(prompt_parts)
    
    def _create_header(self, request: GenerationRequest) -> str:
        """Create the prompt header."""
        framework_info = self.framework_templates.get(request.framework.lower(), {})
        framework_desc = framework_info.get('description', f'{request.framework} application')
        
        return f"""Generate a complete {framework_desc} in {request.language}.

Description: {request.description}

Requirements:
- Framework: {request.framework}
- Language: {request.language}
- Production-ready code with proper error handling
- Clean, maintainable, and well-documented code
- Follow industry best practices and security standards"""
    
    def _create_requirements_section(self, request: GenerationRequest) -> str:
        """Create the requirements section."""
        sections = []
        
        if request.existing_code:
            sections.append(f"Existing Code Context:\n{request.existing_code}")
        
        if request.test_requirements:
            sections.append(f"Testing Requirements:\n{request.test_requirements}")
        
        if request.performance_requirements:
            sections.append(f"Performance Requirements:\n{request.performance_requirements}")
        
        if request.style_guide:
            sections.append(f"Style Guide:\n{request.style_guide}")
        
        return "\n\n".join(sections) if sections else ""
    
    def _create_features_section(self, request: GenerationRequest) -> str:
        """Create the features section."""
        if not request.features:
            return ""
        
        features_text = "Required Features:\n"
        for feature in request.features:
            features_text += f"- {feature}\n"
        
        # Add default features for framework if not already specified
        framework_info = self.framework_templates.get(request.framework.lower(), {})
        default_features = framework_info.get('default_features', [])
        
        additional_features = [f for f in default_features if f not in request.features]
        if additional_features:
            features_text += "\nRecommended Additional Features:\n"
            for feature in additional_features:
                features_text += f"- {feature}\n"
        
        return features_text
    
    def _create_constraints_section(self, request: GenerationRequest) -> str:
        """Create the constraints section."""
        if not request.constraints:
            return ""
        
        constraints_text = "Constraints:\n"
        for constraint in request.constraints:
            constraints_text += f"- {constraint}\n"
        
        return constraints_text
    
    def _create_best_practices_section(self, request: GenerationRequest) -> str:
        """Create the best practices section."""
        framework_info = self.framework_templates.get(request.framework.lower(), {})
        best_practices = framework_info.get('best_practices', [])
        
        if not best_practices:
            return ""
        
        practices_text = "Best Practices to Implement:\n"
        for practice in best_practices:
            practices_text += f"- {practice}\n"
        
        # Add language-specific best practices
        if request.language.lower() == 'python':
            practices_text += "\nPython-Specific Best Practices:\n"
            practices_text += "- Follow PEP 8 style guidelines\n"
            practices_text += "- Use type hints for better code clarity\n"
            practices_text += "- Implement proper logging\n"
            practices_text += "- Use virtual environments\n"
        elif request.language.lower() in ['javascript', 'typescript']:
            practices_text += "\nJavaScript/TypeScript Best Practices:\n"
            practices_text += "- Use ES6+ features appropriately\n"
            practices_text += "- Implement proper error handling\n"
            practices_text += "- Use async/await for asynchronous operations\n"
            practices_text += "- Follow ESLint recommendations\n"
        
        return practices_text
    
    def _create_output_format_section(self) -> str:
        """Create the output format section."""
        return """Output Format:
Please structure your response using markdown with clear file separations:

### FILENAME: path/to/file.ext
```language
[file content]
```

For each file, include:
1. Main application files
2. Configuration files
3. Dependencies file (requirements.txt, package.json, etc.)
4. Dockerfile for containerization
5. Documentation/README
6. Basic tests

Ensure each file is complete and functional."""
    
    def _create_examples_section(self, request: GenerationRequest) -> str:
        """Create examples section if applicable."""
        if request.framework.lower() == 'fastapi':
            return """Example File Structure:
- main.py (FastAPI application with routes)
- models.py (Pydantic models)
- database.py (Database configuration)
- auth.py (Authentication logic)
- requirements.txt (Dependencies)
- Dockerfile (Container configuration)
- README.md (Documentation)"""
        elif request.framework.lower() == 'flask':
            return """Example File Structure:
- app.py (Flask application)
- models.py (Database models)
- routes.py (Route definitions)
- config.py (Configuration)
- requirements.txt (Dependencies)
- Dockerfile (Container configuration)
- README.md (Documentation)"""
        elif request.framework.lower() == 'express':
            return """Example File Structure:
- index.js (Express application)
- routes/ (Route modules)
- models/ (Data models)
- middleware/ (Custom middleware)
- package.json (Dependencies)
- Dockerfile (Container configuration)
- README.md (Documentation)"""
        
        return ""
    
    def _create_footer(self) -> str:
        """Create the prompt footer."""
        return """Important Notes:
- Ensure all code is production-ready and secure
- Include comprehensive error handling
- Add appropriate logging and monitoring
- Make the application easily deployable
- Include clear setup instructions
- Write clean, maintainable code with comments where necessary"""
    
    def create_repair_prompt(self, original_code: str, error_message: str, context: str = "") -> str:
        """
        Create a prompt for code repair.
        
        Args:
            original_code: The code that needs fixing
            error_message: Error message or issue description
            context: Additional context about the problem
            
        Returns:
            Formatted repair prompt
        """
        prompt_parts = [
            "Fix the following code issue:",
            f"\nError/Issue: {error_message}",
        ]
        
        if context:
            prompt_parts.append(f"\nContext: {context}")
        
        prompt_parts.extend([
            f"\nOriginal Code:\n```\n{original_code}\n```",
            "\nPlease provide the corrected code with:",
            "- Clear explanation of what was wrong",
            "- The fixed code",
            "- Any additional improvements or suggestions",
            "\nEnsure the fix addresses the root cause and maintains code quality."
        ])
        
        return "\n".join(prompt_parts)
    
    def create_optimization_prompt(self, code: str, optimization_type: str = "performance") -> str:
        """
        Create a prompt for code optimization.
        
        Args:
            code: Code to optimize
            optimization_type: Type of optimization (performance, readability, security)
            
        Returns:
            Formatted optimization prompt
        """
        return f"""Optimize the following code for {optimization_type}:

```
{code}
```

Please provide:
1. Analysis of current issues or inefficiencies
2. Optimized version of the code
3. Explanation of improvements made
4. Any additional recommendations

Focus on:
- {optimization_type.title()} improvements
- Code maintainability
- Best practices compliance
- Security considerations (if applicable)"""

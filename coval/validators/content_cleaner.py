#!/usr/bin/env python3
"""
COVAL Content Cleaner

Handles cleaning and validation of generated content.
Extracted from generation_engine.py for better modularity and testability.
"""

import re
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ContentCleaner:
    """
    Cleans and validates generated content from LLM responses.
    
    Features:
    - Removes problematic patterns while preserving valid code
    - Safety checks to prevent over-aggressive cleaning
    - Fallback to original content if cleaning is too aggressive
    """
    
    def __init__(self):
        """Initialize the content cleaner."""
        self.setup_cleaning_patterns()
    
    def setup_cleaning_patterns(self):
        """Setup regex patterns for content cleaning."""
        # Problematic patterns to remove
        self.problematic_patterns = [
            # Merge conflict markers (complete blocks only)
            r'<<<<<<< HEAD.*?=======.*?>>>>>>> \w+',
            # Markdown code block wrappers (only if they wrap entire content)
            r'^\s*```(?:python|javascript|typescript|js|py|json|yaml|dockerfile)?\s*\n(.*)\n```\s*$',
            # Multiple consecutive empty lines
            r'\n{3,}',
            # Trailing whitespace
            r'[ \t]+$'
        ]
    
    def clean_generated_content(self, content: str) -> str:
        """
        Clean generated content from problematic patterns while preserving valid code.
        
        Args:
            content: Raw content to clean
            
        Returns:
            Cleaned content with safety checks applied
        """
        if not content or not content.strip():
            return ""
        
        original_content = content
        original_length = len(content)
        
        logger.debug(f"Cleaning content of length {original_length}")
        
        # Apply cleaning patterns
        for pattern in self.problematic_patterns:
            # Special handling for markdown wrapper pattern
            if pattern.startswith(r'^\s*```'):
                # Only remove markdown wrapper if it wraps the entire content
                match = re.match(pattern, content.strip(), re.DOTALL)
                if match:
                    content = match.group(1)
                    logger.debug("Removed markdown code block wrapper")
            else:
                # Apply other patterns normally
                old_content = content
                content = re.sub(pattern, '', content, flags=re.DOTALL | re.MULTILINE)
                if old_content != content:
                    logger.debug(f"Applied cleaning pattern: {pattern[:30]}...")
        
        # Clean up multiple newlines
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # Strip leading/trailing whitespace
        content = content.strip()
        
        # Safety checks
        cleaned_length = len(content)
        
        # Check if we removed too much content (more than 80%)
        if original_length > 0:
            removal_percentage = (original_length - cleaned_length) / original_length
            logger.debug(f"Content size change: {original_length} -> {cleaned_length} ({removal_percentage:.2%} removed)")
            
            if removal_percentage > 0.8:
                logger.warning(f"Cleaning removed {removal_percentage:.1%} of content, reverting to original")
                return original_content.strip()
        
        # If cleaning resulted in empty content but original was not empty, revert
        if not content and original_content.strip():
            logger.warning("Cleaning resulted in empty content, reverting to original")
            return original_content.strip()
        
        return content
    
    def validate_file_content(self, filename: str, content: str) -> bool:
        """
        Validate that file content is reasonable for the given filename.
        
        Args:
            filename: Name of the file
            content: File content to validate
            
        Returns:
            True if content seems valid for the file type
        """
        if not content or not content.strip():
            return False
        
        # Get file extension
        ext = filename.split('.')[-1].lower() if '.' in filename else ''
        
        # Basic validation based on file type
        if ext == 'py':
            return self.validate_python_content(content)
        elif ext in ['js', 'ts']:
            return self.validate_javascript_content(content)
        elif ext == 'json':
            return self.validate_json_content(content)
        elif filename.lower() == 'dockerfile':
            return self.validate_dockerfile_content(content)
        elif filename.lower() == 'requirements.txt':
            return self.validate_requirements_content(content)
        
        # For unknown file types, just check it's not empty
        return bool(content.strip())
    
    def validate_python_content(self, content: str) -> bool:
        """Validate Python file content."""
        # Check for basic Python patterns
        python_indicators = [
            r'import\s+\w+',
            r'from\s+\w+.*import',
            r'def\s+\w+\(',
            r'class\s+\w+',
            r'if\s+__name__\s*==\s*[\'"]__main__[\'"]'
        ]
        
        return any(re.search(pattern, content) for pattern in python_indicators)
    
    def validate_javascript_content(self, content: str) -> bool:
        """Validate JavaScript/TypeScript file content."""
        js_indicators = [
            r'function\s+\w+',
            r'const\s+\w+\s*=',
            r'let\s+\w+\s*=',
            r'var\s+\w+\s*=',
            r'export\s+',
            r'import\s+.*from',
            r'require\s*\('
        ]
        
        return any(re.search(pattern, content) for pattern in js_indicators)
    
    def validate_json_content(self, content: str) -> bool:
        """Validate JSON file content."""
        try:
            import json
            json.loads(content)
            return True
        except json.JSONDecodeError:
            return False
    
    def validate_dockerfile_content(self, content: str) -> bool:
        """Validate Dockerfile content."""
        dockerfile_indicators = [
            r'FROM\s+\w+',
            r'RUN\s+',
            r'COPY\s+',
            r'WORKDIR\s+',
            r'EXPOSE\s+\d+',
            r'CMD\s+',
            r'ENTRYPOINT\s+'
        ]
        
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in dockerfile_indicators)
    
    def validate_requirements_content(self, content: str) -> bool:
        """Validate requirements.txt content."""
        lines = content.strip().split('\n')
        
        # Check if lines look like package requirements
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Should look like package names with optional versions
            if not re.match(r'^[a-zA-Z0-9_-]+([>=<!~=]+[0-9.]+)?$', line):
                return False
        
        return True
    
    def extract_dependencies(self, files: Dict[str, str]) -> List[str]:
        """
        Extract dependencies from generated files.
        
        Args:
            files: Dictionary of filename -> content
            
        Returns:
            List of detected dependencies
        """
        dependencies = []
        
        for filename, content in files.items():
            if filename.endswith('.py'):
                deps = self.extract_python_dependencies(content)
                dependencies.extend(deps)
            elif filename == 'requirements.txt':
                deps = self.extract_requirements_dependencies(content)
                dependencies.extend(deps)
            elif filename == 'package.json':
                deps = self.extract_package_json_dependencies(content)
                dependencies.extend(deps)
        
        # Remove duplicates and return
        return list(set(dependencies))
    
    def extract_python_dependencies(self, content: str) -> List[str]:
        """Extract Python dependencies from import statements."""
        dependencies = []
        
        # Find import statements
        import_patterns = [
            r'from\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+import',
            r'import\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        ]
        
        for pattern in import_patterns:
            matches = re.findall(pattern, content)
            dependencies.extend(matches)
        
        # Filter out standard library modules
        stdlib_modules = {'os', 'sys', 'json', 'time', 'datetime', 'pathlib', 're', 'logging'}
        dependencies = [dep for dep in dependencies if dep not in stdlib_modules]
        
        return dependencies
    
    def extract_requirements_dependencies(self, content: str) -> List[str]:
        """Extract dependencies from requirements.txt content."""
        dependencies = []
        
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                # Extract package name (before any version specifiers)
                package_name = re.split(r'[>=<!~=]', line)[0].strip()
                if package_name:
                    dependencies.append(package_name)
        
        return dependencies
    
    def extract_package_json_dependencies(self, content: str) -> List[str]:
        """Extract dependencies from package.json content."""
        try:
            import json
            data = json.loads(content)
            dependencies = []
            
            # Extract from dependencies and devDependencies
            for section in ['dependencies', 'devDependencies']:
                if section in data:
                    dependencies.extend(data[section].keys())
            
            return dependencies
        except json.JSONDecodeError:
            return []

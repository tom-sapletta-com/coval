#!/usr/bin/env python3
"""
COVAL Response Parser

Handles parsing of LLM responses into structured files and documentation.
Extracted from generation_engine.py for better modularity and testability.
"""

import re
import json
import logging
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)


class ResponseParser:
    """
    Parses LLM responses using multiple strategies to extract files, documentation, and tests.
    
    Supports multiple formats:
    - Original format with ===== separators
    - Markdown with filename headers  
    - JSON format responses
    - Fallback pattern matching
    """
    
    def __init__(self):
        """Initialize the response parser."""
        self.setup_patterns()
    
    def setup_patterns(self):
        """Setup regex patterns for different parsing strategies."""
        # Enhanced patterns to match various markdown filename formats
        self.filename_patterns = [
            # ### FILENAME: app/main.py format (most common)
            r'###\s*FILENAME:\s*([^\n]+)\s*\n```(?:python|javascript|typescript|js|py|json|yaml|dockerfile)?\s*\n(.*?)\n```',
            # ## FILENAME: format
            r'##\s*FILENAME:\s*([^\n]+)\s*\n```(?:python|javascript|typescript|js|py|json|yaml|dockerfile)?\s*\n(.*?)\n```',
            # # FILENAME: format  
            r'#\s*FILENAME:\s*([^\n]+)\s*\n```(?:python|javascript|typescript|js|py|json|yaml|dockerfile)?\s*\n(.*?)\n```',
            # **FILENAME:** format
            r'\*\*FILENAME:\*\*\s*([^\n]+)\s*\n```(?:python|javascript|typescript|js|py|json|yaml|dockerfile)?\s*\n(.*?)\n```',
            # File: format
            r'(?:File:|Filename:|File name:)\s*([^\n]+)\s*\n```(?:python|javascript|typescript|js|py|json|yaml|dockerfile)?\s*\n(.*?)\n```'
        ]
        
        # Generic code block pattern
        self.code_pattern = r'```(?:python|javascript|typescript|js|py|json|yaml|dockerfile)?\s*\n(.*?)\n```'
        
        # Python code patterns for fallback
        self.python_patterns = [
            r'(from\s+\w+.*?import.*?)(?=\n\n|\n[A-Z]|\Z)',
            r'(import\s+\w+.*?)(?=\n\n|\n[A-Z]|\Z)',  
            r'(class\s+\w+.*?(?=\nclass|\Z))',
            r'(def\s+\w+.*?(?=\ndef|\nclass|\Z))',
            r'(app\s*=.*?(?=\n\n|\nif|\Z))'
        ]
    
    def parse_generation_response(self, response: str) -> Tuple[Dict[str, str], str, Dict[str, str]]:
        """
        Parse the LLM response to extract files, documentation, and tests.
        
        Args:
            response: Raw LLM response text
            
        Returns:
            Tuple of (files, documentation, tests) dictionaries
        """
        files = {}
        tests = {}
        documentation = ""
        
        logger.debug(f"Parsing LLM response of length {len(response)}")
        logger.debug(f"Response preview: {response[:500]}...")
        
        # Try multiple parsing strategies - ORDER MATTERS!
        
        # Strategy 1: Original format with "=====" separators
        if "=====" in response and ("FILENAME:" in response or "FILE:" in response):
            logger.debug("Using original format parser (===== separators)")
            files, documentation, tests = self.parse_original_format(response)
        
        # Strategy 2: Markdown with filename headers (check this BEFORE JSON)
        elif ("### FILENAME:" in response or "## FILENAME:" in response or 
              "# FILENAME:" in response or "**FILENAME:" in response) and "```" in response:
            logger.debug("Using markdown format parser (filename headers)")
            files, documentation, tests = self.parse_markdown_format(response)
        
        # Strategy 3: Markdown code blocks (general)
        elif "```" in response:
            logger.debug("Using markdown code block parser")
            files, documentation, tests = self.parse_markdown_format(response)
        
        # Strategy 4: JSON format (check AFTER markdown to avoid false positives)
        elif "```json" in response or ('"files"' in response and '"content"' in response):
            logger.debug("Attempting JSON format parser")
            files, documentation, tests = self.parse_json_format(response)
        
        # Strategy 5: Fallback - create basic files from any code found
        else:
            logger.warning("No recognized format, using fallback parser")
            files, documentation, tests = self.parse_fallback_format(response)
        
        logger.debug(f"Parsed {len(files)} files, {len(tests)} test files")
        
        # DEBUG: Log what files were found
        for filename in files.keys():
            logger.debug(f"Found file: {filename} ({len(files[filename])} chars)")
        
        return files, documentation, tests
    
    def parse_original_format(self, response: str) -> Tuple[Dict[str, str], str, Dict[str, str]]:
        """Parse response using original ===== separator format."""
        files = {}
        tests = {}
        documentation = ""
        
        sections = response.split("=====")
        current_section = None
        current_content = []
        
        for section in sections:
            section = section.strip()
            
            if section.startswith("FILENAME:") or section.startswith("FILE:"):
                # Save previous section
                if current_section and current_content:
                    content = "\n".join(current_content).strip()
                    if content:  # Only save if content exists
                        if current_section.startswith(("FILENAME:", "FILE:")):
                            filename = current_section.replace("FILENAME:", "").replace("FILE:", "").strip()
                            files[filename] = content
                        elif current_section.startswith("TESTS:"):
                            filename = current_section.replace("TESTS:", "").strip()
                            tests[filename] = content
                
                current_section = section
                current_content = []
            elif section.startswith("TESTS:"):
                # Save previous file
                if current_section and current_content:
                    content = "\n".join(current_content).strip()
                    if content and current_section.startswith(("FILENAME:", "FILE:")):
                        filename = current_section.replace("FILENAME:", "").replace("FILE:", "").strip()
                        files[filename] = content
                
                current_section = section
                current_content = []
            elif section.startswith("DOCUMENTATION"):
                current_section = "DOCUMENTATION"
                current_content = []
            else:
                if current_section:
                    current_content.append(section)
        
        # Handle last section
        if current_section and current_content:
            content = "\n".join(current_content).strip()
            if content:
                if current_section.startswith(("FILENAME:", "FILE:")):
                    filename = current_section.replace("FILENAME:", "").replace("FILE:", "").strip()
                    files[filename] = content
                elif current_section.startswith("TESTS:"):
                    filename = current_section.replace("TESTS:", "").strip()
                    tests[filename] = content
                elif current_section == "DOCUMENTATION":
                    documentation = content
        
        return files, documentation, tests
    
    def parse_json_format(self, response: str) -> Tuple[Dict[str, str], str, Dict[str, str]]:
        """Parse JSON format responses."""
        files = {}
        tests = {}
        documentation = ""
        
        # Find JSON blocks
        json_pattern = r'```json\s*(\{.*?\})\s*```'
        json_matches = re.findall(json_pattern, response, re.DOTALL)
        
        # Also try finding JSON without markdown wrapping
        if not json_matches:
            json_pattern = r'(\{[^{}]*"files"[^{}]*\{.*?\}[^{}]*\})'
            json_matches = re.findall(json_pattern, response, re.DOTALL)
        
        for json_str in json_matches:
            try:
                data = json.loads(json_str)
                if "files" in data:
                    for filename, content in data["files"].items():
                        if content:
                            files[filename] = str(content)
                
                if "tests" in data:
                    for filename, content in data["tests"].items():
                        if content:
                            tests[filename] = str(content)
                            
                if "documentation" in data:
                    documentation = str(data["documentation"])
                    
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON: {e}")
                continue
        
        return files, documentation, tests
    
    def parse_markdown_format(self, response: str) -> Tuple[Dict[str, str], str, Dict[str, str]]:
        """Parse markdown code block format."""
        files = {}
        tests = {}
        documentation = ""
        
        # Try each pattern
        for pattern in self.filename_patterns:
            file_matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)
            for filename, content in file_matches:
                filename = filename.strip().strip('`').strip()
                if content and filename:
                    files[filename] = content
        
        # If no explicit files found with patterns, try generic code block extraction
        if not files:
            logger.debug("No filename patterns found, trying generic code block extraction")
            code_matches = re.findall(self.code_pattern, response, re.DOTALL)
            
            for i, content in enumerate(code_matches):
                if content:
                    # Try to infer filename from content
                    filename = self.infer_filename_from_content(content, i)
                    
                    if "def test_" in content or "import pytest" in content:
                        tests[filename] = content
                    else:
                        files[filename] = content
        
        # Extract documentation from the beginning of response
        documentation = self.extract_documentation(response)
        
        return files, documentation, tests
    
    def parse_fallback_format(self, response: str) -> Tuple[Dict[str, str], str, Dict[str, str]]:
        """Fallback parser for unrecognized formats."""
        files = {}
        tests = {}
        documentation = response[:500]  # Use first part as documentation
        
        # Look for any Python-like code patterns
        code_found = []
        for pattern in self.python_patterns:
            matches = re.findall(pattern, response, re.DOTALL)
            code_found.extend(matches)
        
        if code_found:
            # Combine all found code into a main file
            combined_code = '\n\n'.join(code_found)
            if combined_code:
                files["main.py"] = combined_code
        
        # If still no code found, create a basic FastAPI app
        if not files:
            logger.warning("No code patterns found, creating basic FastAPI template")
            basic_app = '''from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
'''
            files["main.py"] = basic_app
            
            # Add requirements
            files["requirements.txt"] = "fastapi==0.110.0\nuvicorn==0.27.0"
        
        return files, documentation, tests
    
    def infer_filename_from_content(self, content: str, index: int = 0) -> str:
        """Infer filename from code content."""
        if "from fastapi import" in content or "FastAPI" in content:
            return f"main.py" if index == 0 else f"app_{index}.py"
        elif "def test_" in content or "import pytest" in content:
            return f"test_main.py" if index == 0 else f"test_{index}.py"
        elif "package.json" in content or '"name"' in content:
            return "package.json"
        elif "FROM " in content and "WORKDIR" in content:
            return "Dockerfile"
        elif "requirements.txt" in content or "fastapi" in content:
            return "requirements.txt"
        else:
            return f"app_{index}.py"
    
    def extract_documentation(self, response: str) -> str:
        """Extract documentation from the beginning of response."""
        doc_lines = []
        lines = response.split('\n')
        for line in lines:
            if line.strip().startswith('#') or line.strip().startswith('```'):
                break
            if line.strip():
                doc_lines.append(line.strip())
        
        if doc_lines:
            return '\n'.join(doc_lines[:5])  # First 5 lines as documentation
        
        return ""

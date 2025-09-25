#!/usr/bin/env python3
"""
COVAL - Code Validation and Learning
Intelligent code generation, execution, and repair system with iterative Docker deployments.
"""

from setuptools import setup, find_packages
import os

# Read README file
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "COVAL - Intelligent Code Generation, Execution, and Repair System"

# Read requirements
def read_requirements():
    req_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if os.path.exists(req_path):
        with open(req_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return [
        'pyyaml>=6.0',
        'requests>=2.28.0',
        'docker>=6.0.0',
        'click>=8.0.0',
        'rich>=13.0.0',
        'jsonschema>=4.0.0',
        'gitpython>=3.1.0',
        'python-dotenv>=1.0.0',
        'typing-extensions>=4.0.0'
    ]

setup(
    name="coval",
    version="2.0.0",
    author="Tom Sapletta",
    author_email="tom@sapletta.com",
    description="Intelligent code generation, execution, and repair system with iterative Docker deployments",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/tom-sapletta-com/coval",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Code Generators",
        "Topic :: Software Development :: Testing",
        "Topic :: System :: Systems Administration",
    ],
    python_requires=">=3.11",
    install_requires=read_requirements(),
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
            'black>=23.0.0',
            'flake8>=6.0.0',
            'mypy>=1.0.0',
        ],
        'docs': [
            'sphinx>=6.0.0',
            'sphinx-rtd-theme>=1.0.0',
        ]
    },
    entry_points={
        'console_scripts': [
            'coval=coval.cli:main',
            'coval-generate=coval.cli:generate_command',
            'coval-run=coval.cli:run_command',
            'coval-repair=coval.cli:repair_command',
            'coval-iterate=coval.cli:iterate_command',
        ],
    },
    include_package_data=True,
    package_data={
        'coval': [
            'config/*.yaml',
            'templates/*.j2',
            'docker/*.yml',
            'docker/*.dockerfile',
        ],
    },
    zip_safe=False,
)

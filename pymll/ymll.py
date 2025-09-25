#!/usr/bin/env python3
"""
YMLL v3 - Intelligent Code Generation and Self-Healing System
Supports multiple languages and frameworks with automatic validation
"""

import json
import yaml
import subprocess
import shutil
import re
import time
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================
# KONFIGURACJA MODELI I FRAMEWORKÓW
# ============================================

class LLMModel(Enum):
    """Dostępne modele LLM zoptymalizowane pod kątem kodu"""
    DEEPSEEK_CODER = "deepseek-coder:6.7b"  # Najlepszy do kodu
    CODELLAMA_7B = "codellama:7b"  # Dobry bilans
    CODELLAMA_13B = "codellama:13b"  # Więcej kontekstu
    QWEN_CODER = "qwen2.5-coder:7b"  # Najnowszy, świetny JSON
    GRANITE_CODE = "granite-code:8b"  # IBM, dobry do enterprise
    MISTRAL = "mistral:7b"  # Fallback


@dataclass
class FrameworkConfig:
    """Konfiguracja dla konkretnego frameworka"""
    name: str
    language: str
    extension: str
    entrypoint: str
    dependencies_file: str
    dockerfile_template: str
    port: int
    test_command: str
    build_command: Optional[str] = None


class FrameworkRegistry:
    """Rejestr wszystkich obsługiwanych frameworków"""

    FRAMEWORKS = {
        # JavaScript/TypeScript
        "express": FrameworkConfig(
            name="express",
            language="javascript",
            extension="js",
            entrypoint="server.js",
            dependencies_file="package.json",
            dockerfile_template="node",
            port=3003,
            test_command="npm test"
        ),
        "nextjs": FrameworkConfig(
            name="nextjs",
            language="typescript",
            extension="tsx",
            entrypoint="app/page.tsx",
            dependencies_file="package.json",
            dockerfile_template="node",
            port=3003,
            test_command="npm test",
            build_command="npm run build"
        ),
        "nestjs": FrameworkConfig(
            name="nestjs",
            language="typescript",
            extension="ts",
            entrypoint="src/main.ts",
            dependencies_file="package.json",
            dockerfile_template="node",
            port=3003,
            test_command="npm test"
        ),

        # Python
        "fastapi": FrameworkConfig(
            name="fastapi",
            language="python",
            extension="py",
            entrypoint="main.py",
            dependencies_file="requirements.txt",
            dockerfile_template="python",
            port=8000,
            test_command="pytest"
        ),
        "django": FrameworkConfig(
            name="django",
            language="python",
            extension="py",
            entrypoint="manage.py",
            dependencies_file="requirements.txt",
            dockerfile_template="python",
            port=8000,
            test_command="python manage.py test"
        ),
        "flask": FrameworkConfig(
            name="flask",
            language="python",
            extension="py",
            entrypoint="app.py",
            dependencies_file="requirements.txt",
            dockerfile_template="python",
            port=5000,
            test_command="pytest"
        ),

        # Go
        "gin": FrameworkConfig(
            name="gin",
            language="go",
            extension="go",
            entrypoint="main.go",
            dependencies_file="go.mod",
            dockerfile_template="go",
            port=8080,
            test_command="go test ./...",
            build_command="go build -o app"
        ),
        "fiber": FrameworkConfig(
            name="fiber",
            language="go",
            extension="go",
            entrypoint="main.go",
            dependencies_file="go.mod",
            dockerfile_template="go",
            port=3003,
            test_command="go test ./..."
        ),

        # Rust
        "actix": FrameworkConfig(
            name="actix",
            language="rust",
            extension="rs",
            entrypoint="src/main.rs",
            dependencies_file="Cargo.toml",
            dockerfile_template="rust",
            port=8080,
            test_command="cargo test",
            build_command="cargo build --release"
        ),

        # Java
        "spring": FrameworkConfig(
            name="spring",
            language="java",
            extension="java",
            entrypoint="Application.java",
            dependencies_file="pom.xml",
            dockerfile_template="java",
            port=8080,
            test_command="mvn test",
            build_command="mvn package"
        ),

        # C#
        "aspnet": FrameworkConfig(
            name="aspnet",
            language="csharp",
            extension="cs",
            entrypoint="Program.cs",
            dependencies_file="project.csproj",
            dockerfile_template="dotnet",
            port=5000,
            test_command="dotnet test",
            build_command="dotnet build"
        ),

        # Ruby
        "rails": FrameworkConfig(
            name="rails",
            language="ruby",
            extension="rb",
            entrypoint="config/application.rb",
            dependencies_file="Gemfile",
            dockerfile_template="ruby",
            port=3003,
            test_command="rails test"
        ),

        # PHP
        "laravel": FrameworkConfig(
            name="laravel",
            language="php",
            extension="php",
            entrypoint="public/index.php",
            dependencies_file="composer.json",
            dockerfile_template="php",
            port=8000,
            test_command="php artisan test"
        )
    }


# ============================================
# GŁÓWNA KLASA SYSTEMU
# ============================================

class YMLLSystem:
    """Główny system YMLL v3"""

    def __init__(self,
                 project_name: str = "GenerycznyApp",
                 model: LLMModel = LLMModel.QWEN_CODER,
                 iterations_dir: str = "./iterations"):

        self.project_name = project_name
        self.model = model
        self.iterations_dir = Path(iterations_dir)
        self.config_file = Path("ymll.config.yaml")
        self.docker_compose_file = Path("docker-compose.yml")
        self.registry_file = Path("registry.yaml")
        self.max_iterations = 5

        # Utwórz katalogi
        self.iterations_dir.mkdir(exist_ok=True)
        Path("common").mkdir(exist_ok=True)
        Path("templates").mkdir(exist_ok=True)
        Path("logs").mkdir(exist_ok=True)

    def init_project(self):
        """Inicjalizacja projektu"""
        logger.info("🎯 Inicjalizacja projektu YMLL v3...")

        # Tworzenie konfiguracji
        config = {
            "project": {
                "name": self.project_name,
                "version": "3.0",
                "description": "Multi-framework code generation with self-healing"
            },
            "llm": {
                "model": self.model.value,
                "temperature": 0.2,  # Niższe dla lepszego kodu
                "max_tokens": 16384,
                "retry_attempts": 3
            },
            "layers": {
                "frontend": {
                    "frameworks": ["express", "nextjs", "react", "vue"],
                    "port_range": [3003, 3099]
                },
                "backend": {
                    "frameworks": ["fastapi", "django", "express", "spring"],
                    "port_range": [3100, 3199]
                },
                "api": {
                    "frameworks": ["fastapi", "gin", "express", "actix"],
                    "port_range": [3200, 3299]
                },
                "workers": {
                    "frameworks": ["python", "go", "rust"],
                    "port_range": [3300, 3399]
                }
            },
            "validation": {
                "strict_mode": True,
                "auto_fix": True,
                "test_on_generation": True
            }
        }

        with open(self.config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)

        self._create_dockerfile_templates()
        self._create_common_components()

        logger.info("✅ Projekt zainicjalizowany")

    def _create_dockerfile_templates(self):
        """Tworzenie szablonów Dockerfile dla różnych języków"""

        templates = {
            "node": """FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install --only=production
COPY . .
EXPOSE {port}
CMD ["node", "{entrypoint}"]
""",
            "python": """FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE {port}
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "{port}"]
""",
            "go": """FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN go build -o main .

FROM alpine:latest
RUN apk --no-cache add ca-certificates
WORKDIR /root/
COPY --from=builder /app/main .
EXPOSE {port}
CMD ["./main"]
""",
            "rust": """FROM rust:1.75 AS builder
WORKDIR /app
COPY Cargo.toml Cargo.lock ./
COPY src ./src
RUN cargo build --release

FROM debian:bookworm-slim
COPY --from=builder /app/target/release/app /usr/local/bin/app
EXPOSE {port}
CMD ["app"]
""",
            "java": """FROM maven:3.9-openjdk-21 AS builder
WORKDIR /app
COPY pom.xml .
COPY src ./src
RUN mvn clean package -DskipTests

FROM openjdk:21-slim
COPY --from=builder /app/target/*.jar app.jar
EXPOSE {port}
CMD ["java", "-jar", "app.jar"]
"""
        }

        for name, content in templates.items():
            template_path = Path(f"templates/Dockerfile.{name}")
            template_path.write_text(content)

    def _create_common_components(self):
        """Tworzenie wspólnych komponentów"""

        # Wspólne utility functions
        Path("common/utils.py").write_text("""
\"\"\"Common utility functions\"\"\"
import json
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

def load_json(filepath: str) -> Dict[str, Any]:
    \"\"\"Load and validate JSON file\"\"\"
    try:
        with open(filepath) as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load JSON from {filepath}: {e}")
        return {}

def validate_schema(data: Dict, schema: Dict) -> bool:
    \"\"\"Validate data against schema\"\"\"
    # Implement JSON schema validation
    return True

def health_check(url: str, timeout: int = 5) -> bool:
    \"\"\"Check if service is healthy\"\"\"
    import requests
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code == 200
    except:
        return False
""")

    def generate_iteration(self, description: str, frameworks: Optional[Dict[str, str]] = None):
        """Generowanie nowej iteracji z określonymi frameworkami"""

        logger.info(f"🚀 Generowanie iteracji: {description}")

        # Określ numer iteracji
        existing = sorted([d for d in self.iterations_dir.iterdir() if d.is_dir()])
        iter_num = len(existing) + 1

        # Nazwa iteracji
        safe_desc = re.sub(r'[^a-z0-9]', '', description.lower())[:20]
        iter_name = f"{iter_num:02d}_{safe_desc}"
        iter_path = self.iterations_dir / iter_name

        # Utwórz strukturę
        for layer in ["frontend", "backend", "api", "workers"]:
            (iter_path / layer).mkdir(parents=True, exist_ok=True)

        # Generuj prompt
        prompt = self._generate_smart_prompt(description, frameworks)

        # Wywołaj LLM
        llm_response = self._call_llm(prompt, iter_path)

        # Parsuj i generuj komponenty
        components = self._parse_and_generate(llm_response, iter_path)

        # Walidacja
        if self._validate_iteration(iter_path):
            logger.info(f"✅ Iteracja {iter_name} wygenerowana pomyślnie")
            self._update_docker_compose(iter_path)
        else:
            logger.error(f"❌ Walidacja iteracji {iter_name} nie powiodła się")

        return iter_path

    def _generate_smart_prompt(self, description: str, frameworks: Optional[Dict[str, str]] = None) -> str:
        """Generowanie inteligentnego promptu dla LLM"""

        # Domyślne frameworki jeśli nie podano
        if not frameworks:
            frameworks = {
                "frontend": "nextjs",
                "backend": "fastapi",
                "api": "fastapi",
                "workers": "python"
            }

        # Pobierz konfiguracje frameworków
        configs = {}
        for layer, fw_name in frameworks.items():
            if fw_name in FrameworkRegistry.FRAMEWORKS:
                configs[layer] = FrameworkRegistry.FRAMEWORKS[fw_name]

        prompt = f"""Create a complete implementation for project: {self.project_name}

TASK: {description}

FRAMEWORKS TO USE:
- Frontend: {frameworks.get('frontend', 'express')}
- Backend: {frameworks.get('backend', 'fastapi')}
- API: {frameworks.get('api', 'fastapi')}
- Workers: {frameworks.get('workers', 'python')}

RESPONSE FORMAT (STRICT JSON):
{{
  "version": "1.0",
  "components": [
    {{
      "name": "frontend",
      "layer": "frontend",
      "framework": "{frameworks.get('frontend', 'express')}",
      "files": {{
        "server.js": "// Complete working code here",
        "package.json": "{{\\"name\\":\\"frontend\\",\\"version\\":\\"1.0.0\\",\\"dependencies\\":{{}}}}"
      }}
    }},
    {{
      "name": "backend",
      "layer": "backend",
      "framework": "{frameworks.get('backend', 'fastapi')}",
      "files": {{
        "main.py": "from fastapi import FastAPI\\napp = FastAPI()\\n@app.get('/')\\ndef root():\\n    return {{\\"status\\": \\"ok\\"}}",
        "requirements.txt": "fastapi==0.110.0\\nuvicorn==0.29.0"
      }}
    }}
  ]
}}

IMPORTANT:
- Generate COMPLETE, WORKING code
- Use proper dependency versions
- Include all required files
- Code must be production-ready
- Response MUST be valid JSON only
"""
        return prompt

    def _call_llm(self, prompt: str, iter_path: Path) -> str:
        """Wywołanie modelu LLM"""

        logger.info(f"📞 Wywołanie modelu: {self.model.value}")

        try:
            # Zapisz prompt
            (iter_path / "prompt.txt").write_text(prompt)

            # Wywołaj Ollama
            result = subprocess.run(
                ["ollama", "run", self.model.value],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=60
            )

            response = result.stdout

            # Zapisz surową odpowiedź
            (iter_path / "llm_response_raw.txt").write_text(response)

            return response

        except subprocess.TimeoutExpired:
            logger.error("❌ Timeout podczas wywołania LLM")
            return self._get_fallback_response()
        except Exception as e:
            logger.error(f"❌ Błąd wywołania LLM: {e}")
            return self._get_fallback_response()

    def _parse_and_generate(self, llm_response: str, iter_path: Path) -> Dict:
        """Parsowanie odpowiedzi LLM i generowanie plików"""

        logger.info("🔍 Rozpoczynam parsowanie odpowiedzi LLM...")
        logger.debug(f"Długość odpowiedzi LLM: {len(llm_response)} znaków")
        logger.debug(f"Pierwsze 200 znaków odpowiedzi: {llm_response[:200]}")
        
        # Próbuj wyciągnąć JSON na różne sposoby
        data = None
        extraction_method = None

        # Ulepszone wzorce regex dla różnych formatów
        json_patterns = [
            # Markdown code block z json
            (r'```json\s*\n(.*?)\n```', "markdown_json_block"),
            # Markdown code block bez specyfikacji języka
            (r'```\s*\n(\{.*?\})\s*\n```', "markdown_generic_block"),
            # JSON z otaczającym tekstem
            (r'\{[^{}]*"components"[^{}]*\[[^\]]*\][^{}]*\}', "simple_components_pattern"),
            # Bardziej złożony JSON z zagnieżdżonymi obiektami
            (r'\{(?:[^{}]|\{[^{}]*\})*"components"(?:[^{}]|\{[^{}]*\})*\}', "complex_components_pattern"),
            # Najbardziej elastyczny wzorzec - wszystko od { do }
            (r'(\{.*\})', "full_json_capture"),
        ]

        logger.info(f"🔍 Testuję {len(json_patterns)} wzorców JSON...")

        for i, (pattern, method_name) in enumerate(json_patterns, 1):
            logger.debug(f"Wzorzec {i}/{len(json_patterns)} ({method_name}): {pattern[:50]}...")
            
            try:
                matches = re.findall(pattern, llm_response, re.DOTALL | re.MULTILINE)
                logger.debug(f"Znaleziono {len(matches)} dopasowań dla wzorca {method_name}")
                
                if matches:
                    for j, match in enumerate(matches):
                        logger.debug(f"Przetwarzam dopasowanie {j+1}/{len(matches)}...")
                        
                        try:
                            # Wyciągnij tekst JSON
                            json_str = match if isinstance(match, str) else str(match)
                            
                            # Dodatkowe czyszczenie dla markdown bloków
                            if "markdown" in method_name:
                                # Usuń ewentualne dodatkowe znaczniki markdown
                                json_str = re.sub(r'^```.*\n', '', json_str)
                                json_str = re.sub(r'\n```$', '', json_str)
                            
                            logger.debug(f"JSON przed czyszczeniem (pierwsze 100 znaków): {json_str[:100]}")
                            
                            # Napraw JSON z literalnymi znakami kontrolnymi
                            json_str = self._sanitize_json_string(json_str)
                            
                            # Usuń potencjalne białe znaki na początku i końcu
                            json_str = json_str.strip()
                            
                            logger.debug(f"JSON po czyszczeniu (pierwsze 100 znaków): {json_str[:100]}")
                            
                            # Spróbuj sparsować JSON
                            parsed_data = json.loads(json_str)
                            
                            # Waliduj czy ma wymaganą strukturę
                            if isinstance(parsed_data, dict) and "components" in parsed_data:
                                components = parsed_data["components"]
                                if isinstance(components, list) and len(components) > 0:
                                    logger.info(f"✅ Pomyślnie sparsowano JSON metodą '{method_name}'")
                                    logger.info(f"📊 Znaleziono {len(components)} komponentów")
                                    
                                    # Loguj komponenty
                                    for comp in components:
                                        comp_name = comp.get('name', 'unnamed')
                                        comp_layer = comp.get('layer', 'unknown')
                                        comp_framework = comp.get('framework', 'unknown')
                                        files_count = len(comp.get('files', {}))
                                        logger.info(f"  - {comp_name} ({comp_layer}/{comp_framework}): {files_count} plików")
                                    
                                    data = parsed_data
                                    extraction_method = method_name
                                    break
                                else:
                                    logger.warning(f"JSON ma pustą lub nieprawidłową listę komponentów")
                            else:
                                logger.warning(f"JSON nie ma wymaganej struktury 'components'")
                                
                        except json.JSONDecodeError as e:
                            logger.debug(f"Błąd parsowania JSON (dopasowanie {j+1}): {str(e)}")
                            logger.debug(f"Problematyczny fragment: {json_str[:200] if len(json_str) > 200 else json_str}")
                            continue
                        except Exception as e:
                            logger.debug(f"Nieoczekiwany błąd podczas parsowania (dopasowanie {j+1}): {str(e)}")
                            continue
                    
                    if data:
                        break
                        
            except Exception as e:
                logger.debug(f"Błąd wzorca {method_name}: {str(e)}")
                continue

        # Jeśli nie udało się sparsować, użyj fallback
        if not data:
            logger.warning("⚠️ Nie znaleziono prawidłowego JSON w odpowiedzi LLM")
            logger.warning("📋 Używam domyślnych szablonów jako fallback")
            
            # Zapisz surową odpowiedź do analizy
            debug_file = iter_path / "llm_response_debug.txt"
            debug_content = f"""=== DEBUG INFORMACJE ===
Długość odpowiedzi: {len(llm_response)}

=== PEŁNA ODPOWIEDŹ LLM ===
{llm_response}

=== TESTOWANE WZORCE ===
"""
            for i, (pattern, method_name) in enumerate(json_patterns, 1):
                debug_content += f"{i}. {method_name}: {pattern}\n"
            
            debug_file.write_text(debug_content)
            logger.info(f"💾 Zapisano informacje debugowania do: {debug_file}")
            
            data = self._get_fallback_data()
            extraction_method = "fallback"
        else:
            logger.info(f"🎯 Użyto metody parsowania: {extraction_method}")

        # Zapisz sparsowany JSON
        components_file = iter_path / "components.json"
        components_file.write_text(json.dumps(data, indent=2))
        logger.info(f"💾 Zapisano komponenty do: {components_file}")

        # Dodaj metadane o parsowaniu
        metadata = {
            "parsing_method": extraction_method,
            "timestamp": time.time(),
            "components_count": len(data.get("components", [])),
            "success": extraction_method != "fallback"
        }
        
        metadata_file = iter_path / "parsing_metadata.json"
        metadata_file.write_text(json.dumps(metadata, indent=2))
        logger.debug(f"💾 Zapisano metadane parsowania do: {metadata_file}")

        # Generuj pliki
        logger.info("🔨 Rozpoczynam generowanie plików komponentów...")
        for i, component in enumerate(data.get("components", []), 1):
            logger.info(f"🔨 Generuję komponent {i}/{len(data.get('components', []))}: {component.get('name', 'unnamed')}")
            self._generate_component_files(component, iter_path)

        logger.info("✅ Parsowanie i generowanie plików zakończone pomyślnie")
        return data

    def _sanitize_json_string(self, json_str: str) -> str:
        """Sanityzuje string JSON, naprawiając problemy z literalnymi znakami kontrolnymi"""
        
        logger.debug("🧹 Rozpoczynam sanityzację JSON string...")
        logger.debug(f"Długość wejściowa: {len(json_str)} znaków")
        
        def escape_json_string_content(match):
            """Escapuje zawartość stringów JSON, naprawiając literalne znaki kontrolne"""
            opening_quote = match.group(1)  # "
            content = match.group(2)        # zawartość między cudzysłowami
            closing_quote = match.group(3)  # "
            
            # Zamień literalne znaki kontrolne na właściwe escapowanie JSON
            content = content.replace('\n', '\\n')   # literal newline -> escaped
            content = content.replace('\r', '\\r')   # literal carriage return
            content = content.replace('\t', '\\t')   # literal tab
            
            # Napraw potencjalne podwójne escapowanie
            content = content.replace('\\\\n', '\\n')
            content = content.replace('\\\\r', '\\r')
            content = content.replace('\\\\t', '\\t')
            
            return f'{opening_quote}{content}{closing_quote}'
        
        # Wzorzec dla wartości stringów JSON: "...zawartość..." 
        # Używamy DOTALL aby obsłużyć wieloliniowe stringi
        string_pattern = r'(")([^"]*?)(")'  
        
        try:
            # Zastosuj escapowanie do wszystkich stringów JSON
            sanitized = re.sub(string_pattern, escape_json_string_content, json_str, flags=re.DOTALL)
            logger.debug("✅ Sanityzacja stringów JSON zakończona")
            
            # Dodatkowe czyszczenie
            # Usuń trailing commas (JSON nie pozwala na końcowe przecinki)
            sanitized = re.sub(r',\s*}', '}', sanitized)
            sanitized = re.sub(r',\s*]', ']', sanitized)
            
            logger.debug(f"Długość wyjściowa: {len(sanitized)} znaków")
            
            # Sprawdź czy sanityzacja nie zepsuła podstawowej struktury JSON
            if sanitized.count('{') != json_str.count('{') or sanitized.count('}') != json_str.count('}'):
                logger.warning("⚠️ Sanityzacja mogła zepsuć strukturę JSON - używam oryginału")
                return json_str
            
            return sanitized
            
        except Exception as e:
            logger.warning(f"⚠️ Błąd podczas sanityzacji JSON: {e}")
            logger.debug(f"Próbuję z oryginalnym stringiem")
            return json_str

    def _generate_component_files(self, component: Dict, iter_path: Path):
        """Generowanie plików dla komponentu"""

        layer = component.get("layer", "")
        files = component.get("files", {})
        framework = component.get("framework", "")

        # Normalizacja nazw warstw (np. "worker" -> "workers")
        layer_mapping = {
            "worker": "workers",
            "Worker": "workers",
            "WORKER": "workers"
        }
        layer = layer_mapping.get(layer, layer)

        if not layer or not files:
            return

        layer_path = iter_path / layer
        layer_path.mkdir(parents=True, exist_ok=True)

        for filename, content in files.items():
            filepath = layer_path / filename

            # Utwórz podkatalogi jeśli plik jest w podkatalogu (np. pages/index.js)
            if "/" in filename:
                filepath.parent.mkdir(parents=True, exist_ok=True)

            # Sanityzacja zawartości
            if filename.endswith(('.json', '.yaml', '.yml')):
                content = self._sanitize_config_file(content, filename)

            # Specjalna obsługa Next.js package.json
            if filename == "package.json" and framework == "nextjs":
                content = self._fix_nextjs_package_json(content)

            filepath.write_text(content)
            logger.info(f"  ✅ Utworzono: {filepath}")

        # Generuj Dockerfile
        self._generate_dockerfile(layer_path, layer, framework)

    def _fix_nextjs_package_json(self, content: str) -> str:
        """Naprawia package.json dla Next.js"""
        try:
            data = json.loads(content)
            # Dodaj wymagane skrypty
            if "scripts" not in data:
                data["scripts"] = {}
            if "dev" not in data["scripts"]:
                data["scripts"]["dev"] = "next dev"
            if "build" not in data["scripts"]:
                data["scripts"]["build"] = "next build"
            if "start" not in data["scripts"]:
                data["scripts"]["start"] = "next start"
            # Upewnij się że są zależności
            if "dependencies" not in data:
                data["dependencies"] = {}
            if "next" not in data["dependencies"]:
                data["dependencies"]["next"] = "^13.5.0"
            if "react" not in data["dependencies"]:
                data["dependencies"]["react"] = "^18.2.0"
            if "react-dom" not in data["dependencies"]:
                data["dependencies"]["react-dom"] = "^18.2.0"
            return json.dumps(data, indent=2)
        except:
            return content

    def _sanitize_config_file(self, content: str, filename: str) -> str:
        """Sanityzacja plików konfiguracyjnych"""

        if filename.endswith('.json'):
            try:
                # Parse i re-serialize dla poprawnego formatowania
                data = json.loads(content)
                return json.dumps(data, indent=2)
            except:
                return content

        elif filename.endswith(('.yaml', '.yml')):
            try:
                data = yaml.safe_load(content)
                return yaml.dump(data, default_flow_style=False)
            except:
                return content

        return content

    def _generate_dockerfile(self, layer_path: Path, layer: str, framework: str):
        """Generowanie Dockerfile dla warstwy"""

        # Mapowanie portów dla warstw
        port_map = {
            "frontend": 3003,
            "backend": 3100,
            "api": 3200,
            "workers": None
        }

        port = port_map.get(layer, 3003)

        # Znajdź odpowiedni template
        if framework in FrameworkRegistry.FRAMEWORKS:
            fw_config = FrameworkRegistry.FRAMEWORKS[framework]
            template_type = fw_config.dockerfile_template

            # Specjalne przypadki dla różnych frameworków
            if framework == "fastapi" or (layer in ["backend", "api"] and (layer_path / "main.py").exists()):
                dockerfile = f"""FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE {port}
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "{port}"]"""
            elif framework == "gin":
                dockerfile = f"""FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download || echo "No go.mod found"
COPY . .
RUN go build -o main .

FROM alpine:latest
RUN apk --no-cache add ca-certificates
WORKDIR /root/
COPY --from=builder /app/main .
EXPOSE {port}
CMD ["./main"]"""
            elif framework == "nextjs":
                dockerfile = f"""FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build || echo "No build script"
EXPOSE {port}
CMD ["npm", "start"]"""
            elif framework == "express" or layer == "frontend":
                dockerfile = f"""FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install --only=production
COPY . .
EXPOSE {port}
CMD ["node", "server.js"]"""
            else:
                # Użyj domyślnego template
                template_file = Path(f"templates/Dockerfile.{template_type}")
                if template_file.exists():
                    template = template_file.read_text()
                    dockerfile = template.format(
                        port=port if port else 3003,
                        entrypoint=fw_config.entrypoint
                    )
                else:
                    # Podstawowy fallback
                    dockerfile = f"""FROM node:20-alpine
WORKDIR /app
COPY . .
RUN npm install || pip install -r requirements.txt || go mod download || true
EXPOSE {port if port else 3003}
CMD ["node", "server.js"]"""
        else:
            # Generyczny Dockerfile bazowany na plikach
            if any((layer_path / f).exists() for f in ["package.json", "server.js", "index.js"]):
                dockerfile = f"""FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install --only=production
COPY . .
EXPOSE {port}
CMD ["node", "server.js"]"""
            elif any((layer_path / f).exists() for f in ["requirements.txt", "main.py", "app.py"]):
                # Python/FastAPI
                dockerfile = f"""FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE {port}
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "{port}"]"""
            elif layer == "workers":
                dockerfile = """FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt || echo "No requirements"
COPY . .
CMD ["python", "worker.py"]"""
            else:
                dockerfile = """FROM alpine:latest
WORKDIR /app
COPY . .
CMD ["sh", "-c", "echo 'No specific runtime detected'"]"""

        (layer_path / "Dockerfile").write_text(dockerfile)
        logger.info(f"  ✅ Utworzono Dockerfile dla {layer}")

    def _validate_iteration(self, iter_path: Path) -> bool:
        """Walidacja wygenerowanej iteracji"""

        logger.info("🔍 Walidacja iteracji...")

        # Sprawdź podstawowe pliki - tylko frontend i backend są wymagane
        checks = []

        required_layers = ["frontend", "backend"]
        optional_layers = ["api", "workers"]

        for layer in required_layers:
            layer_path = iter_path / layer
            if not layer_path.exists():
                logger.error(f"  ❌ Brak wymaganego katalogu {layer}")
                checks.append(False)
                continue

            # Sprawdź czy są jakieś pliki
            files = list(layer_path.glob("*"))
            if not files:
                logger.error(f"  ❌ Brak plików w wymaganym katalogu {layer}")
                checks.append(False)
            else:
                checks.append(True)

        # Dla opcjonalnych warstw tylko informuj
        for layer in optional_layers:
            layer_path = iter_path / layer
            if not layer_path.exists():
                logger.info(f"  ℹ️ Opcjonalny katalog {layer} nie istnieje")
            else:
                files = list(layer_path.glob("*"))
                if not files:
                    logger.info(f"  ℹ️ Opcjonalny katalog {layer} jest pusty")

        valid = all(checks) if checks else False

        if valid:
            logger.info("  ✅ Walidacja pomyślna")
        else:
            logger.error("  ❌ Walidacja niepomyślna")

        return valid

    def _update_docker_compose(self, iter_path: Path):
        """Aktualizacja docker-compose.yml"""

        compose = {
            "services": {}
        }

        ports = {"frontend": 3003, "backend": 3100, "api": 3200}

        for layer in ["frontend", "backend", "api", "workers"]:
            layer_path = iter_path / layer
            if layer_path.exists() and (layer_path / "Dockerfile").exists():
                service_config = {
                    "build": str(layer_path),
                    "restart": "unless-stopped",
                    "environment": {
                        "NODE_ENV": "production",
                        "PYTHONUNBUFFERED": "1"
                    }
                }

                if layer in ports:
                    service_config["ports"] = [f"{ports[layer]}:{ports[layer]}"]

                compose["services"][layer] = service_config

        with open(self.docker_compose_file, 'w') as f:
            yaml.dump(compose, f, default_flow_style=False)

        logger.info("✅ Docker Compose zaktualizowany")

    def run_self_healing(self, max_attempts: int = 5):
        """Uruchomienie self-healing workflow"""

        logger.info("🔄 Uruchamianie self-healing workflow...")

        # Znajdź najnowszą iterację
        iterations = sorted([d for d in self.iterations_dir.iterdir() if d.is_dir()])
        if not iterations:
            logger.error("❌ Brak iteracji do uruchomienia")
            return False

        latest_iter = iterations[-1]
        
        # Skonfiguruj logowanie do pliku w folderze iteracji
        log_file = latest_iter / "logs.txt"
        file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        
        # Dodaj handler do loggera
        logger.addHandler(file_handler)
        
        logger.info(f"🎯 Uruchamianie iteracji: {latest_iter.name}")
        logger.info(f"📄 Logi zapisywane do: {log_file}")

        for attempt in range(1, max_attempts + 1):
            logger.info(f"========== Próba {attempt}/{max_attempts} ==========")

            # Uruchom Docker Compose
            if self._run_docker_compose():
                # Testy E2E
                if self._run_e2e_tests():
                    logger.info("✅ Wszystkie testy przeszły pomyślnie!")
                    
                    # Usuń handler pliku przy sukcesie
                    logger.removeHandler(file_handler)
                    file_handler.close()
                    
                    return True
                else:
                    logger.warning("❌ Testy E2E nie przeszły")
            else:
                logger.error("❌ Docker Compose nie uruchomił się poprawnie")

            # Generuj patch jeśli to nie ostatnia próba
            if attempt < max_attempts:
                self._generate_fix_patch(latest_iter)
                latest_iter = sorted([d for d in self.iterations_dir.iterdir() if d.is_dir()])[-1]

        logger.error(f"⚠️ Self-healing zakończony po {max_attempts} próbach bez sukcesu")
        
        # Usuń handler pliku aby uniknąć duplikatów w kolejnych uruchomieniach
        logger.removeHandler(file_handler)
        file_handler.close()
        
        return False

    def _run_docker_compose(self) -> bool:
        """Uruchomienie Docker Compose"""

        try:
            # Stop existing
            subprocess.run(["docker-compose", "down"], capture_output=True)

            # Build and run
            result = subprocess.run(
                ["docker-compose", "up", "--build", "-d"],
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                logger.info("🐳 Docker Compose uruchomiony")
                time.sleep(10)  # Czekaj na start
                return True
            else:
                logger.error(f"❌ Docker Compose błąd: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"❌ Błąd Docker Compose: {e}")
            return False

    def _run_e2e_tests(self) -> bool:
        """Uruchomienie testów E2E"""

        import requests

        tests_passed = []

        # Test frontend
        try:
            resp = requests.get("http://localhost:3003", timeout=5)
            tests_passed.append(resp.status_code == 200)
            logger.info(f"  Frontend: {'✅' if resp.status_code == 200 else '❌'}")
        except:
            tests_passed.append(False)
            logger.error("  Frontend: ❌ Niedostępny")

        # Test backend (FastAPI)
        backend_urls = [
            "http://localhost:3100/api/status",
            "http://localhost:3100/docs",  # FastAPI docs
            "http://localhost:3100/"  # Root endpoint
        ]
        backend_ok = False
        for url in backend_urls:
            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    backend_ok = True
                    logger.info(f"  Backend: ✅ ({url})")
                    break
            except:
                continue

        if not backend_ok:
            logger.error("  Backend: ❌ Niedostępny")
        tests_passed.append(backend_ok)

        # Test API (FastAPI) - opcjonalne
        if Path("docker-compose.yml").exists():
            with open("docker-compose.yml") as f:
                compose_content = f.read()
                if "api:" in compose_content:
                    api_urls = [
                        "http://localhost:3200/api/v1/info",
                        "http://localhost:3200/api/v1/products",
                        "http://localhost:3200/docs",
                        "http://localhost:3200/"
                    ]
                    api_ok = False
                    for url in api_urls:
                        try:
                            resp = requests.get(url, timeout=5)
                            if resp.status_code == 200:
                                api_ok = True
                                logger.info(f"  API: ✅ ({url})")
                                break
                        except:
                            continue

                    if not api_ok:
                        logger.warning("  API: ⚠️ Niedostępny (opcjonalne)")
                    # API jest opcjonalne, więc nie dodajemy do tests_passed

        return all(tests_passed)

    def _generate_fix_patch(self, parent_iter: Path):
        """Generowanie patcha naprawczego"""

        logger.info("🔧 Generowanie patcha naprawczego...")

        # Zbierz logi błędów
        error_logs = self._collect_error_logs()

        # Generuj prompt naprawczy
        prompt = f"""Fix the following errors in the code:

ERRORS:
{error_logs}

Generate ONLY the fixed files in JSON format.
Focus on fixing the specific errors mentioned.
"""

        # Wygeneruj nową iterację z poprawkami
        self.generate_iteration(f"fix_patch_for_{parent_iter.name}")

    def _collect_error_logs(self) -> str:
        """Zbieranie logów błędów z Docker"""

        try:
            result = subprocess.run(
                ["docker-compose", "logs", "--tail=50"],
                capture_output=True,
                text=True
            )
            return result.stdout
        except:
            return "Unable to collect logs"

    def _get_fallback_response(self) -> str:
        """Fallback response gdy LLM nie działa"""

        return json.dumps(self._get_fallback_data())

    def _get_fallback_data(self) -> Dict:
        """Fallback data structure"""

        return {
            "version": "1.0",
            "components": [
                {
                    "name": "frontend",
                    "layer": "frontend",
                    "framework": "express",
                    "files": {
                        "server.js": """const express = require('express');
const app = express();
app.get('/', (req, res) => res.send('<h1>Frontend Running</h1>'));
app.listen(3003, () => console.log('Frontend on port 3003'));""",
                        "package.json": """{
  "name": "frontend",
  "version": "1.0.0",
  "main": "server.js",
  "scripts": {
    "start": "node server.js"
  },
  "dependencies": {
    "express": "^4.18.0"
  }
}"""
                    }
                },
                {
                    "name": "backend",
                    "layer": "backend",
                    "framework": "fastapi",
                    "files": {
                        "main.py": """from fastapi import FastAPI

app = FastAPI()

@app.get("/api/status")
def get_status():
    return {"status": "Backend running", "version": "1.0"}""",
                        "requirements.txt": "fastapi==0.110.0\nuvicorn==0.29.0"
                    }
                },
                {
                    "name": "api",
                    "layer": "api",
                    "framework": "fastapi",
                    "files": {
                        "main.py": """from fastapi import FastAPI

app = FastAPI()

@app.get("/api/v1/info")
def get_info():
    return {"version": "1.0", "status": "API running"}""",
                        "requirements.txt": "fastapi==0.110.0\nuvicorn==0.29.0"
                    }
                },
                {
                    "name": "workers",
                    "layer": "workers",
                    "framework": "python",
                    "files": {
                        "worker.py": """import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_task():
    logger.info("Processing task...")
    time.sleep(5)
    logger.info("Task completed")

if __name__ == "__main__":
    logger.info("Worker started")
    while True:
        process_task()
        time.sleep(10)""",
                        "requirements.txt": "requests==2.31.0"
                    }
                }
            ]
        }


# ============================================
# CLI INTERFACE
# ============================================

def main():
    """Main CLI entry point"""

    parser = argparse.ArgumentParser(description="YMLL v3 - Multi-Framework Code Generation System")
    parser.add_argument('command', choices=['init', 'generate', 'run', 'status', 'clean', 'test'],
                        help='Command to execute')
    parser.add_argument('description', nargs='?', help='Description for generate command')
    parser.add_argument('--model', type=str, default='qwen2.5-coder:7b',
                        help='LLM model to use')
    parser.add_argument('--frameworks', type=str,
                        help='Frameworks to use (format: frontend:express,backend:fastapi)')

    args = parser.parse_args()

    # Parse model
    model_map = {
        'deepseek': LLMModel.DEEPSEEK_CODER,
        'codellama': LLMModel.CODELLAMA_7B,
        'codellama-13b': LLMModel.CODELLAMA_13B,
        'qwen': LLMModel.QWEN_CODER,
        'qwen2.5-coder:7b': LLMModel.QWEN_CODER,
        'granite': LLMModel.GRANITE_CODE,
        'mistral': LLMModel.MISTRAL
    }

    model = model_map.get(args.model, LLMModel.QWEN_CODER)

    # Initialize system
    system = YMLLSystem(model=model)

    # Execute command
    if args.command == 'init':
        system.init_project()

    elif args.command == 'generate':
        if not args.description:
            logger.error("❌ Brak opisu dla generowania")
            return

        # Parse frameworks if provided
        frameworks = {}
        if args.frameworks:
            for pair in args.frameworks.split(','):
                layer, fw = pair.split(':')
                frameworks[layer] = fw

        system.generate_iteration(args.description, frameworks)

    elif args.command == 'run':
        system.run_self_healing()

    elif args.command == 'test':
        run_tests()

    elif args.command == 'status':
        iterations = list(Path("iterations").iterdir()) if Path("iterations").exists() else []
        print(f"📊 Status projektu:")
        print(f"  Iteracje: {len(iterations)}")
        if iterations:
            print(f"  Ostatnia: {sorted(iterations)[-1].name}")

        # Docker status
        result = subprocess.run(["docker-compose", "ps"], capture_output=True)
        if result.returncode == 0:
            print("  Docker: ✅ Uruchomiony")
        else:
            print("  Docker: ❌ Nie uruchomiony")

    elif args.command == 'clean':
        logger.info("🧹 Czyszczenie projektu...")
        subprocess.run(["docker-compose", "down"], capture_output=True)
        # Clean Python cache
        for cache_dir in Path(".").rglob("__pycache__"):
            shutil.rmtree(cache_dir)
        for cache_dir in Path(".").rglob("node_modules"):
            shutil.rmtree(cache_dir)
        logger.info("✅ Wyczyszczono")


# ============================================
# TESTY
# ============================================

def run_tests():
    """Uruchomienie testów jednostkowych"""

    import unittest

    class TestYMLLSystem(unittest.TestCase):
        """Testy systemu YMLL"""

        def setUp(self):
            self.system = YMLLSystem(model=LLMModel.QWEN_CODER)

        def test_init_project(self):
            """Test inicjalizacji projektu"""
            self.system.init_project()
            self.assertTrue(Path("ymll.config.yaml").exists())
            self.assertTrue(Path("templates").exists())
            self.assertTrue(Path("common").exists())

        def test_framework_registry(self):
            """Test rejestru frameworków"""
            self.assertIn("fastapi", FrameworkRegistry.FRAMEWORKS)
            self.assertIn("express", FrameworkRegistry.FRAMEWORKS)
            self.assertIn("gin", FrameworkRegistry.FRAMEWORKS)

        def test_sanitize_json(self):
            """Test sanityzacji JSON"""
            input_json = '{"name":"test","version":"1.0"}'
            output = self.system._sanitize_config_file(input_json, "test.json")
            data = json.loads(output)
            self.assertEqual(data["name"], "test")

        def test_validate_iteration(self):
            """Test walidacji iteracji"""
            # Create test iteration
            test_iter = Path("iterations/test_iter")
            test_iter.mkdir(parents=True, exist_ok=True)

            for layer in ["frontend", "backend", "api", "workers"]:
                layer_path = test_iter / layer
                layer_path.mkdir(exist_ok=True)
                (layer_path / "test.txt").write_text("test")

            valid = self.system._validate_iteration(test_iter)
            self.assertTrue(valid)

            # Cleanup
            shutil.rmtree(test_iter)

    # Run tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestYMLLSystem)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        logger.info("✅ Wszystkie testy przeszły pomyślnie")
    else:
        logger.error(f"❌ {len(result.failures)} testów nie przeszło")


if __name__ == "__main__":
    main()
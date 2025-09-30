![coval](coval.png)

# Intelligent Code Generation, Execution, and Repair 🤖 COVAL Developer Assistant  

![COVAL](https://img.shields.io/badge/COVAL-v2.0-blue.svg)
![Python](https://img.shields.io/badge/Python-3.11+-green.svg)
![Docker](https://img.shields.io/badge/Docker-Required-blue.svg)
![Ollama](https://img.shields.io/badge/Ollama-Required-orange.svg)
![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)

**COVAL** is a comprehensive Python package for intelligent code generation, execution, and deployment with multiple LLM models. It features robust content cleaning, Docker containerization, health monitoring, and automated deployment workflows for building production-ready applications.

## ✨ Key Features
- 🤖 **Multi-Model Support**: Qwen, DeepSeek, CodeLlama, Granite, and more
- 🧹 **Smart Content Cleaning**: Removes merge conflicts and invalid patterns
- 🐳 **Docker Integration**: Automated containerization and deployment  
- 🔍 **Health Monitoring**: Container health checks and status tracking
- 📊 **Debug Logging**: Comprehensive logging for troubleshooting
- 🚀 **Production Ready**: Tested deployment workflows


```
                    START
                      │
                  [TRIAGE]
                      │
              Collect Metrics
                      │
            ┌─────────┴─────────┐
            │  DECISION MODEL   │
            └─────────┬─────────┘
                      │
           C_fix > 1.5 * C_new?
                 ┌────┴────┐
                YES        NO
                 │          │
            [REBUILD]   [REPAIR]
                 │          │
           Recommend      MRE
           Rebuilding   Creation
                 │          │
                END    Fix Generation
                           │
                      Validation
                      ┌────┴────┐
                   PASS        FAIL
                     │          │
                 [SUCCESS]  Retry?
                     │      ┌──┴──┐
                    END    YES   NO
                            │     │
                      Next Iter  END
```



## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -e .

# 2. Generate new code with specific model
coval generate -d "Create a FastAPI app with user authentication" \
  -f fastapi -l python \
  --features "user registration" --features "JWT tokens" \
  --model qwen



# 3. Deploy generated code
coval run --iteration <iteration_name>

# 4. Check deployed containers
docker ps | grep coval-

# 5. Access your app
curl http://localhost:8001/health
```

## 📋 Available Models

```bash
# Recommended models (configure in llm.config.yaml)
--model qwen          # Qwen 2.5 Coder (recommended for code generation)
--model deepseek      # DeepSeek Coder (good for analysis)
--model deepseek-r1   # DeepSeek R1 (reasoning-focused)
--model codellama13b  # CodeLlama 13B (large context)
--model granite       # Granite Code (enterprise)
--model mistral       # Mistral (fallback)
```

## ✨ Key Features

### 🔄 **Iterative Code Management**
- **Intelligent Iteration System**: Each generation/repair creates a new versioned iteration
- **Cost-Based Decisions**: Automatic analysis of whether to modify existing code or generate new
- **Legacy Cleanup**: Automatic removal of old iterations with configurable retention policies
- **History Tracking**: Complete audit trail of all code changes and decisions


```
1. INPUT
   ├── Error File (stacktrace/logs)
   ├── Source Directory
   └── Test File (optional)
          ↓
2. TRIAGE
   ├── Calculate Technical Debt
   ├── Measure Test Coverage
   ├── Assess Available Context
   └── Get Model Capability
          ↓
3. DECISION
   ├── Calculate Repair Cost
   ├── Calculate Rebuild Cost
   └── Make Decision (repair/rebuild)
          ↓
4. MRE CREATION [if repair]
   ├── Copy Relevant Files
   ├── Create Dockerfile
   └── Generate README
          ↓
5. FIX GENERATION
   ├── Prepare Context
   ├── Generate Prompt
   ├── Call LLM
   └── Parse Response
          ↓
6. VALIDATION
   ├── Apply Patch
   ├── Build Container
   ├── Run Tests
   └── Check Results
          ↓
7. INTEGRATION
   ├── Save Final Patch
   ├── Generate Report
   └── Return Result
```

### 🤖 **Multi-LLM Code Generation & Repair** 
- **6 Specialized Models**: Qwen, DeepSeek-R1, CodeLlama 13B, DeepSeek, Granite, Mistral
- **Adaptive Model Selection**: Choose optimal model based on task complexity and context
- **Automatic Model Management**: Download and configure models automatically via Ollama
- **Dynamic Capability Calculation**: Real-time model performance assessment

### 🐳 **Transparent Docker Deployments**
- **Blue-Green Deployments**: Zero-downtime deployments with automatic rollback
- **Volume Overlays**: Expose only latest changes while preserving legacy code
- **Multi-Framework Support**: FastAPI, Flask, Express.js, Next.js templates
- **Health Monitoring**: Automatic health checks and failure detection

### 💡 **Intelligent Cost Analysis**
- **Cost Calculator**: Automatically decides between modifying existing code vs generating new
- **Multi-Factor Analysis**: Considers technical debt, scope, complexity, and historical success
- **Risk Assessment**: Evaluates confidence levels and potential regression risks
- **Optimization Suggestions**: Recommends best approach for each scenario



## 📋 CLI Commands

### `coval generate` - Generate New Code
```bash
# Basic generation
coval generate -d "Create a REST API for user management" --model deepseek-r1

coval generate -d "Create a REST API for user management" --model qwen  --deploy


# Specify framework and features
coval generate -d "Build a blog platform" -f fastapi -l python \
  --features "authentication" --features "database" --deploy

# Generate from parent iteration
coval generate -d "Add payment system" --parent iter-001 --model deepseek-r1
```

### `coval run` - Deploy Iterations
```bash
# Deploy latest iteration
coval run

# Deploy specific iteration
coval run -i iter-003 -p 8080

# Use different deployment strategy
coval run -i iter-002 --strategy copy
```

### `coval repair` - Fix Code Issues
```bash
# Basic repair
coval repair -e logs/error.log

# Advanced repair with specific model
coval repair -e error.log -i iter-002 --model codellama13b --deploy

# Analyze only (no repair)
coval repair -e error.log --analyze
```

### `coval status` - Project Overview
```bash
# Show all iterations and deployments
coval status

# Verbose output
coval status -v
```

### `coval cleanup` - Maintenance
```bash
# Keep only 10 most recent iterations
coval cleanup -c 10

# Force cleanup without confirmation
coval cleanup -c 5 --force
```

### `coval stop` - Stop Deployments
```bash
# Stop specific deployment
coval stop -i iter-003

# Stop all deployments
coval stop
```

## 🛠 Installation


## 🧰 Makefile Automation

The repository includes a comprehensive `Makefile` that streamlines the full development and release workflow. Use the commands below to get productive quickly:

### Environment & Dependencies

```bash
make setup          # Create virtualenv and install dev dependencies
make install        # Install runtime dependencies only
make install-docs   # Install documentation toolchain
```

### Code Quality & Testing

- **`make format`** – Format the codebase with Black.
- **`make lint`** – Run Black, Flake8, and MyPy checks.
- **`make test`** – Execute the full pytest suite with coverage.
- **`make quick-test`** – Fast iteration loop (`format` + `test-fast`).
- **`make full-check`** – Complete verification (`format`, `lint`, `test`, `security-check`).

### Build & Deployment

- **`make build`** – Produce source and wheel distributions.
- **`make docker-build`** – Build the Docker image tagged with the current version and `latest`.
- **`make deploy-local`** – Build artifacts and run the Docker container locally.

### Release Automation

- **`make publish`** – Automatically bumps the patch version, builds the project, and uploads it to PyPI.
- **`make publish-test`** – Publish artifacts to TestPyPI.
- **`make publish-docker`** – Push Docker images to the configured registry.
- **`make release-patch`**, **`make release-minor`**, **`make release-major`** – Run quality gates, bump versions, build artifacts, and publish to PyPI & Docker.

> **Note:** The `make publish` target automatically increments the patch version via `make version-patch` before uploading. This prevents accidental attempts to reuse an existing version on PyPI.

### Version Management Workflow

```bash
make version          # Display current version and active git branch
make version-patch    # Bump X.Y.Z → X.Y.(Z+1), commit, and tag
make version-minor    # Bump X.Y.Z → X.(Y+1).0, commit, and tag
make version-major    # Bump X.Y.Z → (X+1).0.0, commit, and tag
```

Each command updates `setup.py` and `coval/__init__.py`, creates a git commit, and produces an annotated tag (e.g., `v2.0.1`).

For full releases:

```bash
make release-patch    # format/lint/test → version-patch → build → publish → docker-push
make release-minor
make release-major
```

If a publication fails after a version bump, you can roll back by deleting the tag and resetting the commit:

```bash
git tag -d v<new_version>
git reset --hard HEAD^   # restore previous commit
```


### Prerequisites
```bash
# System requirements
Python 3.11+
Docker & Docker Compose
Ollama (for LLM models)

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama serve
```

### Install COVAL
```bash
# Clone repository
git clone https://github.com/your-org/coval.git
cd coval

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install package
pip install -e .

# Verify installation
coval --help
```

Or use the Makefile helper (recommended):

```bash
make setup            # Creates venv, installs runtime + dev dependencies
source venv/bin/activate
coval --help
```

## ⚙️ Configuration

### Project Configuration (`coval.config.yaml`)
```yaml
# Project settings
project:
  name: "my-coval-project"
  framework: "auto-detect"
  language: "auto-detect" 
  max_iterations: 50

# Docker deployment settings  
docker:
  base_port: 8000
  network_name: "coval-network"
  auto_cleanup: true

# Volume overlay strategy
volumes:
  strategy: "overlay"  # overlay, copy, symlink
  preserve_permissions: true

# Cost calculation settings
cost_calculation:
  modify_base_cost: 10.0
  generate_base_cost: 25.0
  complexity_multiplier: 2.0
```

### LLM Configuration (`llm.config.yaml`)
```yaml
models:
  qwen2.5-coder:
    model_name: "qwen2.5-coder:7b"
    max_tokens: 16384
    temperature: 0.2
    base_capability: 0.85
    context_window: 32768
    
  deepseek-r1:
    model_name: "deepseek-r1:7b" 
    max_tokens: 12288
    temperature: 0.1
    base_capability: 0.80
    context_window: 16384
```

### 🔄 **Automatyczne Pobieranie Modeli**
System automatycznie sprawdza dostępność modelu via `ollama list` i pobiera brakujące:
```bash
🔍 Sprawdzam dostępność modelu: deepseek-r1:7b
📥 Pobieram model: deepseek-r1:7b
✅ Pomyślnie pobrano model: deepseek-r1:7b
```

## Kluczowe funkcjonalności:

### 1. **Model Decyzyjny Repair vs Rebuild**
- Implementuje matematyczny model kosztu naprawy: `C_fix = γD * (1/S) * (1/K) * (1 + λ(1-T))`
- Oblicza prawdopodobieństwo sukcesu używając **funkcji logitowej**
- Automatycznie decyduje czy naprawiać czy przebudować

### 2. **Workflow Naprawy (MRE → Test → Patch → Walidacja)**
- **Triage**: Analiza problemu i zbieranie metryk
- **MRE**: Tworzenie Minimal Reproducible Example
- **Generowanie**: Używa LLM do tworzenia poprawek
- **Walidacja**: Automatyczne testy w Docker
- **Integracja**: Finalizacja i raportowanie

### 3. **Metryki i Analiza**
- Dług techniczny (złożoność, duplikacja, brak dokumentacji)
- Pokrycie testami
- Dostępny kontekst (stacktrace, testy, dokumentacja)
- Zdolności modelu LLM

### 4. **Struktura Folderów**
```
/repairs/
  /repair-{ticket-id}/
    /mre/           # Minimal Reproducible Example
    /proposals/     # Propozycje napraw
    /validation/    # Wyniki walidacji
    decision.md     # Decyzja repair vs rebuild
    repair_report.md # Raport końcowy
```

### 5. **Użycie CLI v2.0**

#### **Dostępne Modele:**
```bash
--model qwen         # qwen2.5-coder:7b (domyślny, 95% zdolności)
--model deepseek     # deepseek-coder:6.7b (80% zdolności)
--model codellama13b # codellama:13b (75% zdolności, duży kontekst)
--model deepseek-r1  # deepseek-r1:7b (88% zdolności, reasoning)
--model granite      # granite-code:8b (70% zdolności, enterprise)
--model mistral      # mistral:7b (60% zdolności, fallback)
```



### 6. **Inteligentne Funkcje v2.0**

- **Automatyczne pobieranie modeli** - System sprawdza `ollama list` i pobiera brakujące modele
- **Dynamiczne obliczanie zdolności** - Uwzględnia tokeny, temperaturę, kontekst i historię
- **Adaptacyjne uczenie się** - 8 kategorii problemów z historical tracking
- **Automatyczne wykrywanie języka/frameworka** - dostosowuje Dockerfile i proces walidacji
- **Iteracyjne poprawki** - do 5 prób z różnymi podejściami i konfiguracją z YAML
- **Parsowanie błędów** - wyciąga pliki wymienione w stacktrace
- **Generowanie promptów** - różne szablony dla pierwszej i kolejnych prób
- **Walidacja w kontenerach** - izolowane środowisko testowe
- **Konfigurowalne parametry** - Wszystkie ustawienia modeli w `llm.config.yaml`


## 🔧 **Troubleshooting**

### **Problemy z Ollama:**
```bash
# Ollama nie jest zainstalowane
❌ Ollama nie jest zainstalowane lub nie jest w PATH
✅ Rozwiązanie: curl -fsSL https://ollama.com/install.sh | sh

# Model nie może być pobrany
❌ Błąd pobierania modelu: connection refused
✅ Rozwiązanie: Uruchom ollama serve w osobnym terminalu

# Timeout pobierania
⏱️ Timeout przy pobieraniu modelu: deepseek-r1:7b
✅ Rozwiązanie: Zwiększ timeout lub pobierz ręcznie: ollama pull deepseek-r1:7b
```

### **Problemy z Konfiguracją:**
```bash
# Brak llm.config.yaml
❌ Nie można załadować konfiguracji
✅ Rozwiązanie: Skopiuj llm.config.yaml z repozytorium

# Nieprawidłowa konfiguracja YAML
❌ yaml.parser.ParserError
✅ Rozwiązanie: Sprawdź składnię YAML online (yamllint.com)

# Brak uprawnień do zapisu repair_history.json
❌ Permission denied: repairs/repair_history.json
✅ Rozwiązanie: mkdir -p repairs && chmod 755 repairs
```

### **Problemy z Modelami:**
```bash
# Model nie odpowiada
❌ Model timeout po 60s
✅ Rozwiązanie: Użyj mniejszego modelu (--model mistral) lub zwiększ timeout

# Niewystarczająca pamięć
❌ CUDA out of memory
✅ Rozwiązanie: Użyj CPU: CUDA_VISIBLE_DEVICES="" python3 repair.py

# Model daje złe wyniki
❌ Repair failed repeatedly
✅ Rozwiązanie: Spróbuj innego modelu z większymi zdolnościami (--model deepseek-r1)
```

### **Customizacja dla Własnych Potrzeb:**

#### **Zwiększ Zdolności Modelu:**
```yaml
models:
  custom-qwen:
    base_capability: 0.90      # ↑ Wyższa baza
    max_tokens: 32768          # ↑ Więcej tokenów = bonus
    temperature: 0.1           # ↓ Niższa temperatura = mniej penalty
    context_window: 65536      # ↑ Większy kontekst = bonus
```

#### **Dostosuj dla Środowiska Produkcyjnego:**
```yaml
global:
  timeout: 120                 # ↑ Więcej czasu dla złożonych napraw
  max_iterations: 10           # ↑ Więcej prób
  adaptive_evaluation:
    history_weight: 0.5        # ↑ Większa waga dla historii
    min_samples: 10            # ↑ Więcej danych do oceny
```

#### **Optymalizacja dla Szybkości:**
```yaml
models:
  fast-mistral:
    max_tokens: 4096           # ↓ Mniej tokenów = szybciej
    temperature: 0.4           # ↑ Wyższa = mniej precyzyjne ale szybsze
    retry_attempts: 1          # ↓ Mniej prób
```

### 7. **Raporty i Decyzje**

System generuje szczegółowe raporty zawierające:
- Analizę kosztów (repair vs rebuild)
- Prawdopodobieństwo sukcesu
- Zastosowane poprawki
- Ocenę ryzyka regresji
- Rekomendacje dalszych kroków

### 8. **Wsparcie dla wielu języków**

Automatycznie rozpoznaje i obsługuje:
- Python (FastAPI, Django, Flask)
- JavaScript/Node.js (Express, Next.js)
- Go (Gin, Fiber)
- Rust, Java, Ruby, PHP

Skrypt jest w pełni zintegrowany z podejściem YMLL i implementuje wszystkie najlepsze praktyki z REPAIR_GUIDELINES, zapewniając efektywny i powtarzalny proces naprawiania kodu z pomocą LLM.

## Funkcja logitowa

Funkcja **logitowa** to po prostu funkcja matematyczna używana głównie w statystyce i uczeniu maszynowym do przekształcania prawdopodobieństw w tzw. log-odds. Jest odwrotnością funkcji sigmoidalnej (logistycznej).

Dokładniej:

### Definicja

Jeżeli $p$ to prawdopodobieństwo zdarzenia (0 < p < 1), funkcja logitowa jest zdefiniowana jako:

$$
\text{logit}(p) = \ln\left(\frac{p}{1-p}\right)
$$

* $p/(1-p)$ to **odds** (szansa, że zdarzenie nastąpi vs że nie nastąpi)
* $\ln$ to logarytm naturalny

### Przykład

* Jeśli $p = 0.8$ (80% prawdopodobieństwa),

$$
\text{logit}(0.8) = \ln\left(\frac{0.8}{0.2}\right) = \ln(4) \approx 1.386
$$

* Jeśli $p = 0.5$, $\text{logit}(0.5) = \ln(1) = 0$

### Zastosowanie

* W **regresji logistycznej** logit przekształca prawdopodobieństwa w wartość na osi liczbowej od $-\infty$ do $+\infty$, co pozwala modelowi liniowemu prognozować log-odds, a następnie łatwo przekształcać z powrotem w prawdopodobieństwo.
* W twoim kontekście (system naprawy kodu) funkcja logitowa może służyć do obliczenia **prawdopodobieństwa sukcesu naprawy** na podstawie różnych zmiennych (jak złożoność, dostępność testów itd.).



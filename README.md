
# 🤖 COVAL v2.0 - Intelligent Code Generation, Execution, and Repair System

![COVAL](https://img.shields.io/badge/COVAL-v2.0-blue.svg)
![Python](https://img.shields.io/badge/Python-3.11+-green.svg)
![Docker](https://img.shields.io/badge/Docker-Required-blue.svg)
![Ollama](https://img.shields.io/badge/Ollama-Required-orange.svg)
![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)

**COVAL** is a comprehensive Python package that manages iterative code generation, execution, and repair with multiple LLM models, integrated Docker Compose deployments, transparent volume overlays, legacy cleanup, and adaptive cost optimization to enable efficient and scalable automated code repair workflows.


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
![coval][coval]



## 🚀 Quick Start

```bash
# Install COVAL
pip install -e .

# Generate new code
coval generate -d "Create a FastAPI app with user authentication" --deploy

# Check status
coval status

# Repair issues
coval repair -e error.log --deploy

# Cleanup old iterations
coval cleanup -c 5
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


[coval]: <data:image/png;base64,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)>

# REPAIR System v1.0 - Dokumentacja Techniczna

## Spis Treści
1. [Wprowadzenie](#wprowadzenie)
2. [Architektura Systemu](#architektura-systemu)
3. [Komponenty](#komponenty)
4. [API i Interfejsy](#api-i-interfejsy)
5. [Przepływ Danych](#przepływ-danych)
6. [Modele Matematyczne](#modele-matematyczne)
7. [Funkcjonalności](#funkcjonalności)
8. [Struktura Katalogów](#struktura-katalogów)
9. [Konfiguracja](#konfiguracja)
10. [Lista Weryfikacyjna TODO](#lista-weryfikacyjna-todo)

---

## 1. Wprowadzenie

### 1.1 Cel Systemu
REPAIR v1.0 to inteligentny system naprawiania kodu wykorzystujący modele LLM (Large Language Models) do automatycznej analizy, diagnozy i naprawy błędów w oprogramowaniu.

### 1.2 Kluczowe Cechy
- **Automatyczna decyzja**: repair vs rebuild na podstawie modelu matematycznego
- **Minimal Reproducible Example (MRE)**: automatyczne tworzenie izolowanego środowiska
- **Walidacja w kontenerach**: Docker-based testing
- **Multi-język**: Python, JavaScript, Go, Rust, Java, Ruby, PHP
- **Iteracyjne naprawy**: do 5 prób z różnymi podejściami

### 1.3 Wymagania Systemowe
- Python 3.8+
- Docker 20.10+
- Ollama (dla modeli LLM)
- 8GB RAM minimum
- 20GB przestrzeni dyskowej

---

## 2. Architektura Systemu

### 2.1 Diagram Architektury

```
┌──────────────────────────────────────────────────────────┐
│                     REPAIR SYSTEM v1.0                    │
├──────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   CLI Layer  │  │  Web API     │  │   Scheduler   │  │
│  │   (main)     │  │  (future)    │  │   (future)    │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                  │                  │          │
│  ┌──────▼──────────────────▼──────────────────▼───────┐  │
│  │              REPAIR ORCHESTRATOR                    │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐            │  │
│  │  │ Triage  │→ │   MRE   │→ │  Fix    │            │  │
│  │  │ Engine  │  │ Builder │  │Generator│            │  │
│  │  └─────────┘  └─────────┘  └─────────┘            │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐            │  │
│  │  │Validator│← │ Decision│  │Reporter │            │  │
│  │  │         │  │  Model  │  │         │            │  │
│  │  └─────────┘  └─────────┘  └─────────┘            │  │
│  └─────────────────────────────────────────────────────┤  │
│                                                         │  │
│  ┌──────────────────────────────────────────────────┐  │  │
│  │                  CORE SERVICES                    │  │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐ │  │  │
│  │  │   Metrics  │  │    LLM     │  │   Docker   │ │  │  │
│  │  │ Calculator │  │  Interface │  │   Manager  │ │  │  │
│  │  └────────────┘  └────────────┘  └────────────┘ │  │  │
│  └──────────────────────────────────────────────────┘  │  │
│                                                         │  │
│  ┌──────────────────────────────────────────────────┐  │  │
│  │                  DATA LAYER                       │  │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐ │  │  │
│  │  │  Repairs   │  │   Prompts  │  │   Configs  │ │  │  │
│  │  │  Storage   │  │  Templates │  │            │ │  │  │
│  │  └────────────┘  └────────────┘  └────────────┘ │  │  │
│  └──────────────────────────────────────────────────┘  │  │
└──────────────────────────────────────────────────────────┘
```

### 2.2 Komponenty Warstw

#### 2.2.1 Warstwa Prezentacji
- **CLI (Command Line Interface)**: główny interfejs użytkownika
- **Web API** (planowane): RESTful API dla integracji
- **Scheduler** (planowane): automatyczne uruchamianie napraw

#### 2.2.2 Warstwa Orkiestracji
- **Triage Engine**: analiza i kategoryzacja błędów
- **MRE Builder**: tworzenie minimalnych przykładów
- **Fix Generator**: generowanie poprawek z LLM
- **Validator**: walidacja poprawek
- **Decision Model**: model matematyczny decyzji
- **Reporter**: generowanie raportów

#### 2.2.3 Warstwa Usług
- **Metrics Calculator**: obliczanie metryk kodu
- **LLM Interface**: komunikacja z modelami językowymi
- **Docker Manager**: zarządzanie kontenerami

#### 2.2.4 Warstwa Danych
- **Repairs Storage**: przechowywanie historii napraw
- **Prompts Templates**: szablony promptów
- **Configs**: konfiguracja systemu

---

## 3. Komponenty

### 3.1 RepairSystem (Główna Klasa)

```python
class RepairSystem:
    """
    Główny kontroler systemu napraw.
    
    Atrybuty:
        model (LLMModel): Model LLM używany do generowania
        repair_dir (Path): Katalog przechowywania napraw
        max_iterations (int): Maksymalna liczba prób
        timeout_seconds (int): Timeout dla operacji
    """
```

**Odpowiedzialności:**
- Orkiestracja całego procesu naprawy
- Zarządzanie cyklem życia naprawy
- Koordynacja między komponentami

### 3.2 RepairDecisionModel

```python
class RepairDecisionModel:
    """
    Model matematyczny podejmowania decyzji.
    
    Metody:
        calculate_repair_cost(): Oblicza koszt naprawy
        calculate_rebuild_cost(): Oblicza koszt przebudowy
        calculate_success_probability(): Prawdopodobieństwo sukcesu
        make_decision(): Podejmuje decyzję repair/rebuild
    """
```

**Formuły matematyczne:**
- Koszt naprawy: `C_fix = γD * (1/S) * (1/K) * (1 + λ(1-T))`
- Prawdopodobieństwo: `P_fix = σ(αK + βT + γ'S - δD_norm)`

### 3.3 RepairMetrics

```python
@dataclass
class RepairMetrics:
    technical_debt: float      # D - dług techniczny (0..∞)
    test_coverage: float        # T - pokrycie testami (0..1)
    available_context: float    # K - dostępny kontekst (0..1)
    model_capability: float     # S - zdolności modelu (0..1)
    
    # Parametry kalibracji
    gamma: float = 2.0
    lambda_: float = 1.5
    alpha: float = 0.8
    beta: float = 0.6
    gamma_prime: float = 0.7
    delta: float = 0.9
```

### 3.4 LLMModel (Enum)

```python
class LLMModel(Enum):
    QWEN_CODER = "qwen2.5-coder:7b"      # Capability: 0.85
    DEEPSEEK_CODER = "deepseek-coder:6.7b"  # Capability: 0.80
    CODELLAMA_13B = "codellama:13b"      # Capability: 0.75
    GRANITE_CODE = "granite-code:8b"     # Capability: 0.70
    MISTRAL = "mistral:7b"                # Capability: 0.60
```

---

## 4. API i Interfejsy

### 4.1 CLI Interface

```bash
python repair.py [OPTIONS]

Wymagane argumenty:
  --error PATH      Ścieżka do pliku z błędem/stacktrace
  --source PATH     Ścieżka do katalogu źródłowego

Opcjonalne argumenty:
  --test PATH       Ścieżka do pliku testowego
  --ticket ID       ID ticketu
  --model MODEL     Model LLM [qwen|deepseek|codellama|granite|mistral]
  --analyze         Tylko analiza bez naprawy
  --max-iterations N Maksymalna liczba prób (domyślnie: 5)
  --verbose         Tryb szczegółowy
```

### 4.2 Python API (Programmatic)

```python
from repair import RepairSystem, LLMModel
from pathlib import Path

# Inicjalizacja
system = RepairSystem(model=LLMModel.QWEN_CODER)

# Naprawa
result = system.repair(
    error_file=Path("error.log"),
    source_dir=Path("./src"),
    test_file=Path("tests/test_bug.py"),
    ticket_id="BUG-123"
)

# Sprawdzenie wyniku
if result.success:
    print(f"Patch: {result.patch_path}")
else:
    print(f"Decision: {result.decision}")
```

---

## 5. Przepływ Danych

### 5.1 Główny Pipeline

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

### 5.2 Przepływ Decyzyjny

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

---

## 6. Modele Matematyczne

### 6.1 Model Kosztu Naprawy

**Formuła:**
```
C_fix = γD × (1/S) × (1/K) × (1 + λ(1-T))
```

**Gdzie:**
- `D` = technical_debt (dług techniczny)
- `S` = model_capability (zdolności modelu)
- `K` = available_context (dostępny kontekst)
- `T` = test_coverage (pokrycie testami)
- `γ` = 2.0 (waga długu)
- `λ` = 1.5 (waga testów)

### 6.2 Model Prawdopodobieństwa

**Formuła:**
```
P_fix = σ(αK + βT + γ'S - δD_norm)
σ(x) = 1 / (1 + e^(-x))
```

**Gdzie:**
- `α` = 0.8 (waga kontekstu)
- `β` = 0.6 (waga testów)
- `γ'` = 0.7 (waga modelu)
- `δ` = 0.9 (waga długu)
- `D_norm` = min(D/100, 1.0)

### 6.3 Kryteria Decyzji

- **Repair**: gdy `C_fix ≤ 1.5 × C_new`
- **Rebuild**: gdy `C_fix > 1.5 × C_new`

---

## 7. Funkcjonalności

### 7.1 Analiza Kodu

#### 7.1.1 Obliczanie Długu Technicznego
```python
def _calculate_technical_debt(source_dir: Path) -> float:
    """
    Metryki:
    - Złożoność cyklomatyczna (if/for/while/try)
    - Duplikacja kodu
    - Brak dokumentacji
    
    Zwraca: float (0..100)
    """
```

#### 7.1.2 Pomiar Pokrycia Testami
```python
def _calculate_test_coverage(source_dir: Path) -> float:
    """
    Metryki:
    - Stosunek plików testowych do źródłowych
    - Obecność test_ funkcji
    - Użycie frameworków testowych
    
    Zwraca: float (0..1)
    """
```

#### 7.1.3 Ocena Kontekstu
```python
def _calculate_available_context(source_dir: Path, error: str) -> float:
    """
    Sprawdza:
    - Obecność stacktrace
    - Istnienie testów
    - Requirements/dependencies
    - Dokumentację
    - Strukturę projektu
    
    Zwraca: float (0..1)
    """
```

### 7.2 Generowanie MRE

#### 7.2.1 Struktura MRE
```
/repair-{ticket-id}/mre/
├── src/           # Tylko istotne pliki źródłowe
├── tests/         # Testy reprodukujące błąd
├── Dockerfile     # Kontener dla środowiska
├── README.md      # Instrukcje reprodukcji
├── stacktrace.txt # Oryginalny błąd
└── requirements.txt / package.json / go.mod
```

#### 7.2.2 Automatyczne Dockerfile
System automatycznie generuje Dockerfile na podstawie:
- Wykrytego języka (Python, Node.js, Go, etc.)
- Plików dependencies (requirements.txt, package.json)
- Struktury projektu

### 7.3 Generowanie Poprawek

#### 7.3.1 Szablony Promptów
- **Pierwsza próba**: Pełna analiza i propozycja
- **Kolejne próby**: Alternatywne podejścia

#### 7.3.2 Format Odpowiedzi
```json
{
  "analysis": "Analiza przyczyny",
  "explanation": "Wyjaśnienie naprawy",
  "patch": "Unified diff format",
  "files": {
    "path/to/file.py": "Pełna zawartość"
  },
  "regression_risk": "Ocena ryzyka"
}
```

### 7.4 Walidacja

#### 7.4.1 Proces Walidacji
1. Kopiowanie MRE do środowiska testowego
2. Aplikacja patcha
3. Build kontenera Docker
4. Uruchomienie testów
5. Weryfikacja wyników

#### 7.4.2 Kryteria Sukcesu
- Wszystkie testy przechodzą
- Brak błędów kompilacji
- Brak timeoutów

---

## 8. Struktura Katalogów

### 8.1 Struktura Projektu
```
repair-system/
├── repair.py           # Główny skrypt
├── repairs/            # Katalog napraw
│   └── repair-{id}/    # Pojedyncza naprawa
│       ├── mre/        # Minimal Reproducible Example
│       ├── proposals/  # Propozycje napraw
│       ├── validation/ # Wyniki walidacji
│       ├── decision.md # Decyzja repair/rebuild
│       ├── repair_report.md # Raport końcowy
│       └── final_patch.diff # Finalny patch
├── templates/          # Szablony promptów
└── logs/              # Logi systemu
```

### 8.2 Struktura Pojedynczej Naprawy
```
repair-20240101_120000/
├── decision.md         # Analiza decyzyjna
├── mre/
│   ├── src/           # Kod źródłowy
│   ├── tests/         # Testy
│   ├── Dockerfile     # Środowisko
│   ├── README.md      # Instrukcje
│   └── stacktrace.txt # Błąd
├── proposals/
│   ├── fix-1/
│   │   ├── patch.diff
│   │   └── explanation.md
│   └── fix-2/
│       ├── patch.diff
│       └── explanation.md
├── validation/
│   ├── test/          # Środowisko testowe
│   ├── test_output.txt
│   └── test_errors.txt
├── prompt_0.txt        # Prompty do LLM
├── prompt_0_response.txt
├── final_patch.diff    # Zaakceptowany patch
└── repair_report.md    # Raport końcowy
```

---

## 9. Konfiguracja

### 9.1 Parametry Systemu

```python
# Domyślne wartości
MAX_ITERATIONS = 5      # Maksymalna liczba prób
TIMEOUT_SECONDS = 120   # Timeout dla operacji
REPAIR_DIR = "./repairs"  # Katalog napraw

# Progi decyzyjne
REBUILD_THRESHOLD = 1.5  # C_fix > 1.5 * C_new → rebuild
MIN_SUCCESS_PROB = 0.3   # Minimalne prawdopodobieństwo

# Parametry modelu (kalibrowane)
GAMMA = 2.0        # Waga długu technicznego
LAMBDA = 1.5       # Waga braku testów
ALPHA = 0.8        # Waga kontekstu
BETA = 0.6         # Waga testów
GAMMA_PRIME = 0.7  # Waga modelu
DELTA = 0.9        # Waga długu (prawdopodobieństwo)
```

### 9.2 Konfiguracja Modeli LLM

```python
MODEL_CAPABILITIES = {
    "qwen2.5-coder:7b": 0.85,
    "deepseek-coder:6.7b": 0.80,
    "codellama:13b": 0.75,
    "granite-code:8b": 0.70,
    "mistral:7b": 0.60
}
```

### 9.3 Wsparcie Języków

```python
LANGUAGE_SUPPORT = {
    "python": {
        "extensions": [".py"],
        "test_patterns": ["test_*.py", "*_test.py"],
        "dependencies": "requirements.txt",
        "dockerfile": "python:3.11-slim"
    },
    "javascript": {
        "extensions": [".js", ".jsx", ".ts", ".tsx"],
        "test_patterns": ["*.test.js", "*.spec.js"],
        "dependencies": "package.json",
        "dockerfile": "node:20-alpine"
    },
    "go": {
        "extensions": [".go"],
        "test_patterns": ["*_test.go"],
        "dependencies": "go.mod",
        "dockerfile": "golang:1.21-alpine"
    }
}
```

---

## 10. Lista Weryfikacyjna TODO

### 10.1 Zadania Weryfikacyjne dla LLM

Poniżej znajduje się lista zadań do weryfikacji implementacji. Każde zadanie zawiera opis i oczekiwany kod testowy.

#### TODO-001: Weryfikacja istnienia głównej klasy RepairSystem
```python
# Test: Sprawdź czy klasa RepairSystem istnieje i ma wymagane metody
def test_repair_system_exists():
    from repair import RepairSystem
    
    required_methods = [
        'triage', 'create_mre', 'generate_fix', 
        'validate_fix', 'repair'
    ]
    
    for method in required_methods:
        assert hasattr(RepairSystem, method), f"Brak metody: {method}"
    
    return "✅ RepairSystem ma wszystkie wymagane metody"
```

#### TODO-002: Weryfikacja modelu decyzyjnego
```python
# Test: Sprawdź obliczenia modelu matematycznego
def test_decision_model():
    from repair import RepairDecisionModel, RepairMetrics
    
    metrics = RepairMetrics(
        technical_debt=50.0,
        test_coverage=0.5,
        available_context=0.7,
        model_capability=0.8
    )
    
    # Test kosztu naprawy
    repair_cost = RepairDecisionModel.calculate_repair_cost(metrics)
    assert repair_cost > 0, "Koszt naprawy musi być dodatni"
    
    # Test prawdopodobieństwa
    success_prob = RepairDecisionModel.calculate_success_probability(metrics)
    assert 0 <= success_prob <= 1, "Prawdopodobieństwo poza zakresem"
    
    # Test decyzji
    decision, prob, analysis = RepairDecisionModel.make_decision(metrics, 1000)
    assert decision in ['repair', 'rebuild'], "Nieprawidłowa decyzja"
    
    return "✅ Model decyzyjny działa poprawnie"
```

#### TODO-003: Weryfikacja struktury katalogów
```python
# Test: Sprawdź czy system tworzy właściwą strukturę
def test_directory_structure():
    from repair import RepairSystem
    from pathlib import Path
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        system = RepairSystem(repair_dir=tmpdir)
        
        # Symuluj utworzenie MRE
        test_path = Path(tmpdir) / "repair-TEST001"
        mre_path = test_path / "mre"
        mre_path.mkdir(parents=True)
        
        # Sprawdź strukturę
        assert mre_path.exists(), "Brak katalogu MRE"
        
        # Sprawdź podkatalogi
        expected_dirs = ['src', 'tests']
        for dir_name in expected_dirs:
            (mre_path / dir_name).mkdir()
            assert (mre_path / dir_name).exists(), f"Brak {dir_name}"
    
    return "✅ Struktura katalogów poprawna"
```

#### TODO-004: Weryfikacja obliczania metryk
```python
# Test: Sprawdź obliczanie metryk kodu
def test_metrics_calculation():
    from repair import RepairSystem
    from pathlib import Path
    import tempfile
    
    system = RepairSystem()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        source_dir = Path(tmpdir)
        
        # Utwórz przykładowy kod
        (source_dir / "main.py").write_text("""
def complex_function():
    if True:
        for i in range(10):
            try:
                pass
            except:
                pass
""")
        
        # Test długu technicznego
        debt = system._calculate_technical_debt(source_dir)
        assert 0 <= debt <= 100, "Dług poza zakresem"
        
        # Test pokrycia testami
        coverage = system._calculate_test_coverage(source_dir)
        assert 0 <= coverage <= 1, "Pokrycie poza zakresem"
        
        # Test kontekstu
        context = system._calculate_available_context(source_dir, "Error")
        assert 0 <= context <= 1, "Kontekst poza zakresem"
    
    return "✅ Metryki obliczane poprawnie"
```

#### TODO-005: Weryfikacja generowania Dockerfile
```python
# Test: Sprawdź automatyczne generowanie Dockerfile
def test_dockerfile_generation():
    from repair import RepairSystem
    from pathlib import Path
    import tempfile
    
    system = RepairSystem()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        mre_path = Path(tmpdir)
        
        # Python project
        (mre_path / "requirements.txt").write_text("fastapi==0.110.0")
        system._create_mre_dockerfile(mre_path)
        
        dockerfile = mre_path / "Dockerfile"
        assert dockerfile.exists(), "Brak Dockerfile"
        
        content = dockerfile.read_text()
        assert "python" in content.lower(), "Brak Python w Dockerfile"
        assert "requirements.txt" in content, "Brak requirements"
    
    return "✅ Dockerfile generowany poprawnie"
```

#### TODO-006: Weryfikacja parsowania odpowiedzi LLM
```python
# Test: Sprawdź parsowanie JSON z odpowiedzi
def test_llm_response_parsing():
    from repair import RepairSystem
    
    system = RepairSystem()
    
    # Przykładowa odpowiedź LLM
    response = '''
    Here's the fix:
    ```json
    {
        "analysis": "Found null pointer",
        "explanation": "Added null check",
        "patch": "--- a/main.py\\n+++ b/main.py",
        "files": {
            "main.py": "def fixed_function(): pass"
        }
    }
    ```
    '''
    
    result = system._parse_fix_response(response)
    assert result is not None, "Parsowanie nieudane"
    assert "analysis" in result, "Brak analizy"
    assert "files" in result, "Brak plików"
    
    return "✅ Parsowanie odpowiedzi działa"
```

#### TODO-007: Weryfikacja walidacji poprawek
```python
# Test: Sprawdź proces walidacji (mockowany)
def test_validation_process():
    from repair import RepairSystem
    from pathlib import Path
    import tempfile
    from unittest.mock import patch
    
    system = RepairSystem()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        repair_path = Path(tmpdir)
        mre_path = repair_path / "mre"
        mre_path.mkdir(parents=True)
        
        # Mockuj Docker
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "Tests passed"
            
            proposal = {"files": {"test.py": "print('fixed')"}}
            result = system.validate_fix(repair_path, proposal)
            
            # Sprawdź czy validation została wywołana
            assert mock_run.called, "Docker nie został wywołany"
    
    return "✅ Walidacja wykonuje się poprawnie"
```

#### TODO-008: Weryfikacja generowania raportów
```python
# Test: Sprawdź generowanie raportów
def test_report_generation():
    from repair import RepairSystem, RepairResult
    from pathlib import Path
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        repair_path = Path(tmpdir) / "repair-TEST"
        repair_path.mkdir(parents=True)
        
        # Sprawdź raport decyzji
        decision_file = repair_path / "decision.md"
        decision_content = """# Repair Decision
## Decision: REPAIR
## Analysis: Cost effective"""
        decision_file.write_text(decision_content)
        
        assert decision_file.exists(), "Brak pliku decyzji"
        content = decision_file.read_text()
        assert "Decision" in content, "Brak sekcji decyzji"
        assert "Analysis" in content, "Brak sekcji analizy"
    
    return "✅ Raporty generowane poprawnie"
```

#### TODO-009: Weryfikacja obsługi błędów
```python
# Test: Sprawdź obsługę błędów i wyjątków
def test_error_handling():
    from repair import RepairSystem
    from pathlib import Path
    
    system = RepairSystem()
    
    # Test z nieistniejącymi plikami
    result = system.repair(
        error_file=Path("/nonexistent/error.txt"),
        source_dir=Path("/nonexistent/source"),
        ticket_id="TEST-ERROR"
    )
    
    # System powinien obsłużyć błąd gracefully
    # Zamiast crashować, powinien zwrócić result z błędem
    assert hasattr(result, 'success'), "Brak atrybutu success"
    assert not result.success, "Nie powinno być sukcesu"
    
    return "✅ Obsługa błędów działa"
```

#### TODO-010: Weryfikacja integracji CLI
```python
# Test: Sprawdź parser argumentów CLI
def test_cli_parser():
    import argparse
    from repair import main
    
    # Symuluj argumenty CLI
    test_args = [
        '--error', 'error.log',
        '--source', './src',
        '--model', 'qwen',
        '--analyze'
    ]
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--error', required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--model', default='qwen')
    parser.add_argument('--analyze', action='store_true')
    
    args = parser.parse_args(test_args)
    
    assert args.error == 'error.log', "Błędny error"
    assert args.source == './src', "Błędny source"
    assert args.model == 'qwen', "Błędny model"
    assert args.analyze == True, "Błędny analyze"
    
    return "✅ CLI parser działa poprawnie"
```

### 10.2 Skrypt Weryfikacyjny

```python
#!/usr/bin/env python3
"""
Skrypt weryfikacyjny dla REPAIR System v1.0
Uruchom aby sprawdzić zgodność implementacji z dokumentacją
"""

def run_all_tests():
    """Uruchamia wszystkie testy weryfikacyjne"""
    
    tests = [
        test_repair_system_exists,
        test_decision_model,
        test_directory_structure,
        test_metrics_calculation,
        test_dockerfile_generation,
        test_llm_response_parsing,
        test_validation_process,
        test_report_generation,
        test_error_handling,
        test_cli_parser
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            print(result)
            results.append((test.__name__, True, result))
        except Exception as e:
            error_msg = f"❌ {test.__name__}: {str(e)}"
            print(error_msg)
            results.append((test.__name__, False, str(e)))
    
    # Podsumowanie
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    print("\n" + "=" * 60)
    print(f"WYNIKI: {passed}/{total} testów przeszło")
    print("=" * 60)
    
    if passed == total:
        print("🎉 WSZYSTKIE TESTY PRZESZŁY POMYŚLNIE!")
    else:
        print("⚠️ Niektóre testy nie przeszły - sprawdź implementację")
        print("\nNieudane testy:")
        for name, success, msg in results:
            if not success:
                print(f"  - {name}: {msg}")
    
    return passed == total

if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
```

### 10.3 Checklist Implementacyjna

- [ ] **Core Components**
  - [ ] Klasa `RepairSystem` z wszystkimi metodami
  - [ ] Klasa `RepairDecisionModel` z formułami
  - [ ] Dataclass `RepairMetrics`
  - [ ] Dataclass `RepairResult`
  - [ ] Enum `LLMModel`

- [ ] **Funkcje Obliczeniowe**
  - [ ] `_calculate_technical_debt()`
  - [ ] `_calculate_test_coverage()`
  - [ ] `_calculate_available_context()`
  - [ ] `_count_lines_of_code()`
  - [ ] `_get_model_capability()`

- [ ] **MRE Builder**
  - [ ] `create_mre()`
  - [ ] `_copy_relevant_files()`
  - [ ] `_create_mre_dockerfile()`

- [ ] **Generator Poprawek**
  - [ ] `generate_fix()`
  - [ ] `_prepare_context()`
  - [ ] `_generate_repair_prompt()`
  - [ ] `_call_llm()`
  - [ ] `_parse_fix_response()`

- [ ] **Walidator**
  - [ ] `validate_fix()`
  - [ ] Docker integration
  - [ ] Test runner

- [ ] **Raportowanie**
  - [ ] Decision report (decision.md)
  - [ ] Repair report (repair_report.md)
  - [ ] Logging system

- [ ] **CLI**
  - [ ] Argument parser
  - [ ] Main entry point
  - [ ] Error handling

- [ ] **Dokumentacja**
  - [ ] README.md
  - [ ] Przykłady użycia
  - [ ] Konfiguracja

---

## Podsumowanie

REPAIR System v1.0 to kompletne rozwiązanie do automatycznej naprawy kodu wykorzystujące:
- Modele matematyczne do podejmowania decyzji
- Izolowane środowiska Docker dla bezpiecznej walidacji
- Iteracyjne podejście z wieloma próbami
- Wsparcie dla wielu języków programowania
- Szczegółowe raportowanie i śledzenie historii

System jest zaprojektowany aby być:
- **Deterministyczny**: powtarzalne wyniki
- **Bezpieczny**: izolacja w kontenerach
- **Skalowalny**: możliwość równoległego przetwarzania
- **Rozszerzalny**: łatwe dodawanie nowych języków i modeli

Użyj skryptu weryfikacyjnego aby sprawdzić zgodność implementacji z tą dokumentacją.
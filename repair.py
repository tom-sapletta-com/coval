#!/usr/bin/env python3
"""
REPAIR v1.0 - Inteligentny system naprawiania kodu z użyciem LLM
Bazowany na YMLL v3 z implementacją modelu decyzyjnego repair vs rebuild
"""

import json
import yaml
import subprocess
import shutil
import re
import time
import argparse
import logging
import math
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================
# MODELE I KONFIGURACJA
# ============================================

class LLMModel(Enum):
    """Dostępne modele LLM zoptymalizowane pod kątem naprawy kodu"""
    QWEN_CODER = "qwen2.5-coder:7b"  # Najlepszy do debugowania
    DEEPSEEK_CODER = "deepseek-coder:6.7b"  # Dobry do analizy
    CODELLAMA_13B = "codellama:13b"  # Większy kontekst
    DEEPSEEK_R1 = "deepseek-r1:7b"  # Nowy model z reasoning
    GRANITE_CODE = "granite-code:8b"  # IBM, stabilny
    MISTRAL = "mistral:7b"  # Fallback


@dataclass
class RepairMetrics:
    """Metryki do modelu decyzyjnego"""
    technical_debt: float  # D - dług techniczny (0..∞)
    test_coverage: float  # T - pokrycie testami (0..1)
    available_context: float  # K - dostępny kontekst (0..1)
    model_capability: float  # S - zdolności modelu (0..1)
    historical_success_rate: float = 0.0  # H - historyczna skuteczność (0..1)

    # Parametry modelu (kalibrowane)
    gamma: float = 2.0
    lambda_: float = 1.5
    alpha: float = 0.8
    beta: float = 0.6
    gamma_prime: float = 0.7
    delta: float = 0.9
    eta: float = 0.4  # Waga dla historycznej skuteczności


@dataclass
class RepairResult:
    """Wynik naprawy"""
    success: bool
    patch_path: Optional[Path]
    test_path: Optional[Path]
    validation_passed: bool
    iterations_needed: int
    decision: str  # 'repair' lub 'rebuild'
    confidence: float
    error_log: Optional[str] = None
    
    # Nowe pola dla adaptacyjnej oceny
    model_used: str = ""
    problem_category: str = ""
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


class RepairDecisionModel:
    """Model matematyczny decyzji repair vs rebuild"""

    @staticmethod
    def calculate_repair_cost(metrics: RepairMetrics) -> float:
        """
        Oblicza koszt naprawy według wzoru:
        C_fix = γD * (1/S) * (1/K) * (1 + λ(1-T))
        """
        cost = (
                metrics.gamma * metrics.technical_debt *
                (1 / max(metrics.model_capability, 0.01)) *
                (1 / max(metrics.available_context, 0.01)) *
                (1 + metrics.lambda_ * (1 - metrics.test_coverage))
        )
        return cost

    @staticmethod
    def calculate_rebuild_cost(loc: int) -> float:
        """Szacuje koszt przebudowy od zera"""
        # Prosty model: koszt rośnie liniowo z LOC
        base_cost = 10.0
        cost_per_loc = 0.01
        return base_cost + (loc * cost_per_loc)

    @staticmethod
    def calculate_success_probability(metrics: RepairMetrics) -> float:
        """
        Oblicza prawdopodobieństwo sukcesu z uwzględnieniem historii:
        P_fix = σ(αK + βT + γ'S + ηH - δD_norm)
        """
        # Normalizacja długu technicznego
        d_norm = min(metrics.technical_debt / 100, 1.0)

        # Funkcja logitowa z historyczną skutecznością
        x = (
                metrics.alpha * metrics.available_context +
                metrics.beta * metrics.test_coverage +
                metrics.gamma_prime * metrics.model_capability +
                metrics.eta * metrics.historical_success_rate -
                metrics.delta * d_norm
        )

        # Sigmoid
        probability = 1 / (1 + math.exp(-x))
        return probability

    @staticmethod
    def make_decision(metrics: RepairMetrics, loc: int) -> Tuple[str, float, Dict]:
        """Podejmuje decyzję repair vs rebuild"""
        repair_cost = RepairDecisionModel.calculate_repair_cost(metrics)
        rebuild_cost = RepairDecisionModel.calculate_rebuild_cost(loc)
        success_prob = RepairDecisionModel.calculate_success_probability(metrics)

        # Decyzja z marginesem 1.5x
        decision = "rebuild" if repair_cost > 1.5 * rebuild_cost else "repair"

        return decision, success_prob, {
            "repair_cost": repair_cost,
            "rebuild_cost": rebuild_cost,
            "success_probability": success_prob,
            "cost_ratio": repair_cost / rebuild_cost
        }


# ============================================
# GŁÓWNA KLASA SYSTEMU REPAIR
# ============================================

class RepairSystem:
    """Główny system naprawiania kodu"""

    def __init__(self,
                 model: LLMModel = LLMModel.QWEN_CODER,
                 repair_dir: str = "./repairs",
                 config_path: str = "./llm.config.yaml"):

        self.model = model
        self.repair_dir = Path(repair_dir)
        self.repair_dir.mkdir(exist_ok=True)
        
        # Załaduj konfigurację
        self.config = self._load_config(config_path)
        self.model_config = self._get_model_config()
        
        # Sprawdź i pobierz model jeśli potrzeba
        self._ensure_model_available()
        
        # Historia dla adaptacyjnej oceny
        self.history_file = self.repair_dir / "repair_history.json"
        self.history = self._load_history()

        # Konfiguracja
        self.max_iterations = self.config.get('global', {}).get('max_repair_iterations', 5)
        self.timeout_seconds = self.config.get('global', {}).get('timeout_seconds', 120)

    def triage(self,
               error_file: Path,
               source_dir: Path,
               test_file: Optional[Path] = None) -> RepairMetrics:
        """
        Faza triage - analiza problemu i zbieranie metryk
        """
        logger.info("🔍 Rozpoczynam triage...")

        # Analiza błędu i kategoryzacja problemu
        error_content = error_file.read_text() if error_file.exists() else ""
        problem_category = self._categorize_problem(error_content)
        
        # Historyczna skuteczność dla tej kategorii
        historical_success = self._get_historical_success_rate(problem_category)

        # Zbieranie metryk z dynamiczną zdolnością modelu
        metrics = RepairMetrics(
            technical_debt=self._calculate_technical_debt(source_dir),
            test_coverage=self._calculate_test_coverage(source_dir),
            available_context=self._calculate_available_context(source_dir, error_content),
            model_capability=self._get_model_capability(problem_category),
            historical_success_rate=historical_success
        )

        # Liczenie LOC
        loc = self._count_lines_of_code(source_dir)

        logger.info(f"📊 Metryki:")
        logger.info(f"  - Dług techniczny: {metrics.technical_debt:.2f}")
        logger.info(f"  - Pokrycie testami: {metrics.test_coverage:.2%}")
        logger.info(f"  - Dostępny kontekst: {metrics.available_context:.2%}")
        logger.info(f"  - Zdolności modelu: {metrics.model_capability:.2%}")
        logger.info(f"  - Historyczna skuteczność: {metrics.historical_success_rate:.2%}")
        logger.info(f"  - Kategoria problemu: {problem_category}")
        logger.info(f"  - LOC: {loc}")

        return metrics

    def create_mre(self,
                   source_dir: Path,
                   error_file: Path,
                   ticket_id: str) -> Path:
        """
        Tworzy Minimal Reproducible Example
        """
        logger.info("🔧 Tworzenie MRE...")

        # Struktura folderów
        repair_path = self.repair_dir / f"repair-{ticket_id}"
        mre_path = repair_path / "mre"
        mre_path.mkdir(parents=True, exist_ok=True)

        # Kopiuj tylko istotne pliki
        self._copy_relevant_files(source_dir, mre_path, error_file)

        # Tworzenie Dockerfile
        self._create_mre_dockerfile(mre_path)

        # README z instrukcjami
        readme_content = f"""# MRE for ticket {ticket_id}

## Reproduce error:
```bash
docker build -t mre-{ticket_id} .
docker run mre-{ticket_id} python test_bug.py
```

## Error:
{error_file.read_text() if error_file.exists() else 'See stacktrace.txt'}

## Files:
- src/ - source code
- tests/ - test files
- Dockerfile - container definition
"""
        (mre_path / "README.md").write_text(readme_content)

        logger.info(f"✅ MRE utworzone w: {mre_path}")
        return repair_path

    def generate_fix(self,
                     repair_path: Path,
                     metrics: RepairMetrics) -> List[Dict]:
        """
        Generuje propozycje naprawy używając LLM
        """
        logger.info("🤖 Generowanie propozycji naprawy...")

        mre_path = repair_path / "mre"
        proposals_path = repair_path / "proposals"
        proposals_path.mkdir(exist_ok=True)

        # Przygotuj kontekst
        context = self._prepare_context(mre_path)

        proposals = []

        for i in range(min(3, self.max_iterations)):
            logger.info(f"  Generowanie propozycji {i + 1}...")

            # Generuj prompt
            prompt = self._generate_repair_prompt(context, i)

            # Wywołaj LLM
            response = self._call_llm(prompt, repair_path / f"prompt_{i}.txt")

            # Parsuj odpowiedź
            proposal = self._parse_fix_response(response)

            if proposal:
                # Zapisz propozycję
                fix_dir = proposals_path / f"fix-{i + 1}"
                fix_dir.mkdir(exist_ok=True)

                # Zapisz patch
                if "patch" in proposal:
                    (fix_dir / "patch.diff").write_text(proposal["patch"])

                # Zapisz wyjaśnienie
                if "explanation" in proposal:
                    (fix_dir / "explanation.md").write_text(proposal["explanation"])

                # Zapisz zaktualizowane pliki
                if "files" in proposal:
                    for filename, content in proposal["files"].items():
                        (fix_dir / filename).write_text(content)

                proposals.append(proposal)
                logger.info(f"  ✅ Propozycja {i + 1} wygenerowana")

        return proposals

    def validate_fix(self,
                     repair_path: Path,
                     proposal: Dict) -> bool:
        """
        Waliduje propozycję naprawy
        """
        logger.info("🧪 Walidacja naprawy...")

        validation_path = repair_path / "validation"
        validation_path.mkdir(exist_ok=True)

        # Kopiuj MRE do walidacji
        mre_path = repair_path / "mre"
        test_path = validation_path / "test"

        if test_path.exists():
            shutil.rmtree(test_path)
        shutil.copytree(mre_path, test_path)

        # Zastosuj patch
        if "files" in proposal:
            for filename, content in proposal["files"].items():
                file_path = test_path / filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content)

        # Uruchom testy w kontenerze
        try:
            # Build
            result = subprocess.run(
                ["docker", "build", "-t", "repair-test", "."],
                cwd=test_path,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                logger.error(f"  ❌ Build failed: {result.stderr}")
                return False

            # Run tests
            result = subprocess.run(
                ["docker", "run", "--rm", "repair-test", "python", "-m", "pytest", "-v"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                logger.info("  ✅ Testy przeszły pomyślnie")
                (validation_path / "test_output.txt").write_text(result.stdout)
                return True
            else:
                logger.error(f"  ❌ Testy nie przeszły: {result.stdout}")
                (validation_path / "test_errors.txt").write_text(result.stderr)
                return False

        except subprocess.TimeoutExpired:
            logger.error("  ❌ Timeout podczas walidacji")
            return False
        except Exception as e:
            logger.error(f"  ❌ Błąd walidacji: {e}")
            return False

    def repair(self,
               error_file: Path,
               source_dir: Path,
               test_file: Optional[Path] = None,
               ticket_id: Optional[str] = None) -> RepairResult:
        """
        Główna funkcja naprawy - orkiestruje cały proces
        """
        logger.info("=" * 60)
        logger.info("🔧 REPAIR SYSTEM v1.0")
        logger.info("=" * 60)

        # Generuj ticket ID jeśli nie podano
        if not ticket_id:
            ticket_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        logger.info(f"📋 Ticket ID: {ticket_id}")

        # 1. TRIAGE
        metrics = self.triage(error_file, source_dir, test_file)
        loc = self._count_lines_of_code(source_dir)

        # 2. DECYZJA
        decision, success_prob, analysis = RepairDecisionModel.make_decision(metrics, loc)

        logger.info(f"📊 Analiza decyzyjna:")
        logger.info(f"  - Decyzja: {decision.upper()}")
        logger.info(f"  - Prawdopodobieństwo sukcesu: {success_prob:.2%}")
        logger.info(f"  - Koszt naprawy: {analysis['repair_cost']:.2f}")
        logger.info(f"  - Koszt przebudowy: {analysis['rebuild_cost']:.2f}")
        logger.info(f"  - Stosunek kosztów: {analysis['cost_ratio']:.2f}")

        # Zapisz decyzję
        repair_path = self.repair_dir / f"repair-{ticket_id}"
        repair_path.mkdir(parents=True, exist_ok=True)

        decision_file = repair_path / "decision.md"
        decision_content = f"""# Repair Decision for {ticket_id}

## Decision: **{decision.upper()}**

## Analysis:
- Success Probability: {success_prob:.2%}
- Repair Cost: {analysis['repair_cost']:.2f}
- Rebuild Cost: {analysis['rebuild_cost']:.2f}
- Cost Ratio: {analysis['cost_ratio']:.2f}

## Metrics:
- Technical Debt: {metrics.technical_debt:.2f}
- Test Coverage: {metrics.test_coverage:.2%}
- Available Context: {metrics.available_context:.2%}
- Model Capability: {metrics.model_capability:.2%}
- Lines of Code: {loc}

## Recommendation:
{"Proceed with repair - cost effective and high success probability" if decision == "repair" else "Consider rebuilding - repair cost exceeds rebuild threshold"}
"""
        decision_file.write_text(decision_content)

        # Jeśli decyzja to rebuild, zakończ
        if decision == "rebuild":
            logger.warning("⚠️ Rekomendacja: PRZEBUDOWA od zera")
            logger.warning("   Koszt naprawy przekracza próg opłacalności")
            return RepairResult(
                success=False,
                patch_path=None,
                test_path=None,
                validation_passed=False,
                iterations_needed=0,
                decision="rebuild",
                confidence=success_prob
            )

        # 3. MRE
        repair_path = self.create_mre(source_dir, error_file, ticket_id)

        # 4. GENEROWANIE POPRAWEK
        proposals = self.generate_fix(repair_path, metrics)

        if not proposals:
            logger.error("❌ Nie udało się wygenerować propozycji naprawy")
            return RepairResult(
                success=False,
                patch_path=None,
                test_path=None,
                validation_passed=False,
                iterations_needed=0,
                decision="repair",
                confidence=success_prob,
                error_log="No proposals generated"
            )

        # 5. WALIDACJA
        best_proposal = None
        for i, proposal in enumerate(proposals):
            logger.info(f"🔍 Testowanie propozycji {i + 1}/{len(proposals)}...")

            if self.validate_fix(repair_path, proposal):
                best_proposal = proposal
                logger.info(f"✅ Propozycja {i + 1} zaakceptowana!")
                break

        # 6. INTEGRACJA
        if best_proposal:
            # Zapisz finalny patch
            final_patch_path = repair_path / "final_patch.diff"
            if "patch" in best_proposal:
                final_patch_path.write_text(best_proposal["patch"])

            # Utwórz raport sukcesu
            report_path = repair_path / "repair_report.md"
            report_content = f"""# Repair Report - {ticket_id}

## Status: ✅ SUCCESS

## Summary:
- Decision: {decision}
- Success Probability: {success_prob:.2%}
- Iterations Needed: {len(proposals)}
- Validation: PASSED

## Applied Fix:
{best_proposal.get('explanation', 'See patch file')}

## Files Modified:
{chr(10).join('- ' + f for f in best_proposal.get('files', {}).keys())}

## Next Steps:
1. Review the patch in `final_patch.diff`
2. Run integration tests
3. Deploy to staging
4. Monitor for regressions
"""
            report_path.write_text(report_content)

            logger.info("=" * 60)
            logger.info("🎉 NAPRAWA ZAKOŃCZONA SUKCESEM!")
            logger.info(f"📁 Wyniki w: {repair_path}")
            logger.info("=" * 60)

            return RepairResult(
                success=True,
                patch_path=final_patch_path,
                test_path=repair_path / "validation/test",
                validation_passed=True,
                iterations_needed=len(proposals),
                decision="repair",
                confidence=success_prob
            )

        else:
            logger.error("❌ Żadna propozycja nie przeszła walidacji")

            # Raport niepowodzenia
            report_path = repair_path / "repair_report.md"
            report_content = f"""# Repair Report - {ticket_id}

## Status: ❌ FAILED

## Summary:
- Decision: {decision}
- Success Probability: {success_prob:.2%}
- Iterations Attempted: {len(proposals)}
- Validation: FAILED

## Recommendation:
Consider manual intervention or rebuilding the component.

## Attempted Fixes:
{chr(10).join(f'- Proposal {i + 1}: Failed validation' for i in range(len(proposals)))}
"""
            report_path.write_text(report_content)

            return RepairResult(
                success=False,
                patch_path=None,
                test_path=None,
                validation_passed=False,
                iterations_needed=len(proposals),
                decision="repair",
                confidence=success_prob,
                error_log="All proposals failed validation"
            )

    # ============================================
    # FUNKCJE POMOCNICZE
    # ============================================

    def _calculate_technical_debt(self, source_dir: Path) -> float:
        """Oblicza dług techniczny na podstawie różnych metryk"""
        debt = 0.0

        # Złożoność cyklomatyczna (przybliżona)
        for py_file in source_dir.rglob("*.py"):
            content = py_file.read_text()
            # Liczba if/for/while/try jako proxy dla złożoności
            complexity_keywords = ['if ', 'for ', 'while ', 'try:', 'except:', 'elif ']
            for keyword in complexity_keywords:
                debt += content.count(keyword) * 0.5

        # Duplikacja kodu (bardzo uproszczona)
        all_lines = []
        for py_file in source_dir.rglob("*.py"):
            all_lines.extend(py_file.read_text().splitlines())

        unique_lines = set(all_lines)
        if all_lines:
            duplication_ratio = 1 - (len(unique_lines) / len(all_lines))
            debt += duplication_ratio * 20

        # Brak dokumentacji
        for py_file in source_dir.rglob("*.py"):
            content = py_file.read_text()
            if '"""' not in content and "'''" not in content:
                debt += 2

        return min(debt, 100)  # Cap at 100

    def _calculate_test_coverage(self, source_dir: Path) -> float:
        """Szacuje pokrycie testami"""
        test_files = list(source_dir.rglob("test_*.py")) + list(source_dir.rglob("*_test.py"))
        source_files = [f for f in source_dir.rglob("*.py")
                        if not f.name.startswith("test_") and not f.name.endswith("_test.py")]

        if not source_files:
            return 0.0

        # Przybliżenie: stosunek liczby testów do liczby plików źródłowych
        coverage = min(len(test_files) / len(source_files), 1.0)

        # Bonus za pytest/unittest
        for test_file in test_files:
            content = test_file.read_text()
            if "def test_" in content or "class Test" in content:
                coverage = min(coverage + 0.1, 1.0)

        return coverage

    def _calculate_available_context(self, source_dir: Path, error_content: str) -> float:
        """Oblicza dostępny kontekst"""
        context_score = 0.0

        # Czy mamy stacktrace?
        if "Traceback" in error_content or "Error" in error_content:
            context_score += 0.3

        # Czy mamy testy?
        if list(source_dir.rglob("test_*.py")):
            context_score += 0.2

        # Czy mamy requirements/dependencies?
        if (source_dir / "requirements.txt").exists() or (source_dir / "package.json").exists():
            context_score += 0.2

        # Czy mamy dokumentację?
        if (source_dir / "README.md").exists() or (source_dir / "README.rst").exists():
            context_score += 0.1

        # Czy kod jest dobrze zorganizowany?
        if (source_dir / "src").exists() or (source_dir / "lib").exists():
            context_score += 0.1

        # Czy mamy pliki konfiguracyjne?
        config_files = [".env", "config.yaml", "config.json", "settings.py"]
        if any((source_dir / cf).exists() for cf in config_files):
            context_score += 0.1

        return min(context_score, 1.0)

    def _get_model_capability(self, problem_category: str = "general") -> float:
        """Dynamiczna zdolność modelu z uwzględnieniem parametrów i historii"""
        # Bazowa zdolność z konfiguracji
        base_capability = self.model_config.get('base_capability', 0.5)
        
        # Parametry modelu
        max_tokens = self.model_config.get('max_tokens', 8192)
        temperature = self.model_config.get('temperature', 0.2)
        context_window = self.model_config.get('context_window', 8192)
        
        # Dynamiczne bonusy z konfiguracji globalnej
        calc_config = self.config.get('global', {}).get('capability_calculation', {})
        
        # Bonus za większy kontekst tokenów
        token_bonus = max(0, max_tokens - 8192) * calc_config.get('token_bonus_multiplier', 0.0001)
        
        # Penalty za wysoką temperaturę
        temp_penalty = temperature * calc_config.get('temperature_penalty', 0.2)
        
        # Bonus za większe okno kontekstu
        context_bonus = max(0, context_window - 8192) * calc_config.get('context_bonus_multiplier', 0.0001)
        
        # Historyczna skuteczność dla danej kategorii problemu
        historical_bonus = self._get_historical_success_rate(problem_category) * 0.1
        
        # Oblicz końcową zdolność
        final_capability = base_capability + token_bonus - temp_penalty + context_bonus + historical_bonus
        
        # Ogranicz do maksymalnej wartości
        max_cap = calc_config.get('max_capability', 0.95)
        return min(final_capability, max_cap)

    def _count_lines_of_code(self, source_dir: Path) -> int:
        """Liczy linie kodu"""
        loc = 0
        for file_path in source_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in ['.py', '.js', '.java', '.cpp', '.c', '.go']:
                try:
                    loc += len(file_path.read_text().splitlines())
                except:
                    pass
        return loc

    def _load_config(self, config_path: str) -> Dict:
        """Ładuje konfigurację z pliku YAML"""
        config_file = Path(config_path)
        if not config_file.exists():
            logger.warning(f"⚠️ Nie znaleziono pliku konfiguracji: {config_path}, używam wartości domyślnych")
            return self._get_default_config()
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                logger.info(f"✅ Załadowano konfigurację z: {config_path}")
                return config
        except Exception as e:
            logger.error(f"❌ Błąd wczytywania konfiguracji: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Zwraca domyślną konfigurację"""
        return {
            'qwen': {
                'model': 'qwen2.5-coder:7b',
                'max_tokens': 16384,
                'temperature': 0.2,
                'base_capability': 0.85
            },
            'global': {
                'timeout_seconds': 120,
                'max_repair_iterations': 5,
                'capability_calculation': {
                    'token_bonus_multiplier': 0.0001,
                    'temperature_penalty': 0.2,
                    'max_capability': 0.95
                }
            }
        }
    
    def _get_model_config(self) -> Dict:
        """Pobiera konfigurację dla bieżącego modelu"""
        model_name = self.model.value.split(':')[0].replace('.', '').replace('-', '')
        
        # Mapowanie nazw modeli na klucze konfiguracji
        model_mapping = {
            'qwen25coder': 'qwen',
            'deepseekcoder': 'deepseek', 
            'codellama': 'codellama13b',
            'deepseekr1': 'deepseek-r1',
            'granitecode': 'granite',
            'mistral': 'mistral'
        }
        
        config_key = model_mapping.get(model_name, 'qwen')
        return self.config.get(config_key, self.config.get('qwen', {}))
    
    def _ensure_model_available(self) -> bool:
        """Sprawdza dostępność modelu i pobiera go jeśli potrzeba"""
        model_name = self.model.value
        logger.info(f"🔍 Sprawdzam dostępność modelu: {model_name}")
        
        try:
            # Sprawdź czy model jest dostępny
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and model_name in result.stdout:
                logger.info(f"✅ Model {model_name} jest dostępny")
                return True
            
            # Model nie jest dostępny - pobierz go
            logger.info(f"📥 Pobieram model: {model_name}")
            pull_result = subprocess.run(
                ["ollama", "pull", model_name],
                capture_output=True,
                text=True,
                timeout=600  # 10 minut na pobranie
            )
            
            if pull_result.returncode == 0:
                logger.info(f"✅ Pomyślnie pobrano model: {model_name}")
                return True
            else:
                logger.error(f"❌ Błąd pobierania modelu: {pull_result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"⏱️ Timeout przy pobieraniu modelu: {model_name}")
            return False
        except FileNotFoundError:
            logger.error("❌ Ollama nie jest zainstalowane lub nie jest w PATH")
            return False
        except Exception as e:
            logger.error(f"❌ Nieoczekiwany błąd: {e}")
            return False
    
    def _load_history(self) -> Dict:
        """Ładuje historię napraw"""
        if not self.history_file.exists():
            return {'repairs': [], 'categories': {}}
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"⚠️ Nie można wczytać historii: {e}")
            return {'repairs': [], 'categories': {}}
    
    def _save_history(self):
        """Zapisuje historię napraw"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2, default=str, ensure_ascii=False)
        except Exception as e:
            logger.error(f"❌ Błąd zapisu historii: {e}")
    
    def _categorize_problem(self, error_content: str) -> str:
        """Kategoryzuje problem na podstawie błędu"""
        error_lower = error_content.lower()
        
        # Kategoryzacja na podstawie typowych błędów
        if any(word in error_lower for word in ['syntax', 'invalid syntax', 'unexpected token']):
            return 'syntax_error'
        elif any(word in error_lower for word in ['import', 'module', 'not found']):
            return 'import_error' 
        elif any(word in error_lower for word in ['type', 'attribute', 'object has no']):
            return 'type_error'
        elif any(word in error_lower for word in ['name', 'undefined', 'not defined']):
            return 'name_error'
        elif any(word in error_lower for word in ['connection', 'network', 'timeout']):
            return 'network_error'
        elif any(word in error_lower for word in ['file', 'directory', 'path']):
            return 'file_error'
        elif any(word in error_lower for word in ['docker', 'container', 'compose']):
            return 'docker_error'
        else:
            return 'general'
    
    def _get_historical_success_rate(self, category: str) -> float:
        """Zwraca historyczną skuteczność dla danej kategorii"""
        category_data = self.history.get('categories', {}).get(category, {})
        
        total_attempts = category_data.get('total_attempts', 0)
        successful_repairs = category_data.get('successful_repairs', 0)
        
        if total_attempts == 0:
            return 0.0
        
        # Zastosuj wagę historii z konfiguracji
        adaptive_config = self.config.get('global', {}).get('adaptive_evaluation', {})
        decay_factor = adaptive_config.get('decay_factor', 0.95)
        
        # Oblicz ważoną skuteczność z decay factor
        raw_rate = successful_repairs / total_attempts
        return raw_rate * (decay_factor ** (total_attempts - successful_repairs))
    
    def _record_repair_result(self, result: RepairResult, category: str):
        """Zapisuje wynik naprawy w historii"""
        # Dodaj do ogólnej listy napraw
        repair_record = {
            'timestamp': result.timestamp.isoformat(),
            'success': result.success,
            'model_used': result.model_used,
            'problem_category': category,
            'execution_time': result.execution_time,
            'iterations_needed': result.iterations_needed,
            'confidence': result.confidence
        }
        
        self.history['repairs'].append(repair_record)
        
        # Aktualizuj statystyki kategorii
        if 'categories' not in self.history:
            self.history['categories'] = {}
        
        if category not in self.history['categories']:
            self.history['categories'][category] = {
                'total_attempts': 0,
                'successful_repairs': 0,
                'last_updated': datetime.now().isoformat()
            }
        
        cat_data = self.history['categories'][category]
        cat_data['total_attempts'] += 1
        if result.success:
            cat_data['successful_repairs'] += 1
        cat_data['last_updated'] = datetime.now().isoformat()
        
        # Zapisz historię
        self._save_history()
        
        logger.info(f"📊 Zapisano wynik naprawy: {category} - {'sukces' if result.success else 'porażka'}")

    def _copy_relevant_files(self, source_dir: Path, mre_path: Path, error_file: Path):
        """Kopiuje tylko istotne pliki do MRE"""
        # Parsuj błąd aby znaleźć powiązane pliki
        error_content = error_file.read_text() if error_file.exists() else ""
        mentioned_files = re.findall(r'File "([^"]+)"', error_content)

        # Kopiuj wymienione pliki
        for file_path in mentioned_files:
            source_file = source_dir / file_path
            if source_file.exists():
                dest_file = mre_path / "src" / file_path
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_file, dest_file)

        # Kopiuj testy
        test_dir = mre_path / "tests"
        test_dir.mkdir(exist_ok=True)

        for test_file in source_dir.rglob("test_*.py"):
            shutil.copy2(test_file, test_dir / test_file.name)

        # Kopiuj requirements
        for req_file in ["requirements.txt", "package.json", "go.mod", "Cargo.toml"]:
            if (source_dir / req_file).exists():
                shutil.copy2(source_dir / req_file, mre_path / req_file)

        # Kopiuj błąd
        shutil.copy2(error_file, mre_path / "stacktrace.txt")

    def _create_mre_dockerfile(self, mre_path: Path):
        """Tworzy Dockerfile dla MRE"""
        # Wykryj język/framework
        if (mre_path / "requirements.txt").exists():
            dockerfile = """FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "-m", "pytest", "-v"]
"""
        elif (mre_path / "package.json").exists():
            dockerfile = """FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
CMD ["npm", "test"]
"""
        elif (mre_path / "go.mod").exists():
            dockerfile = """FROM golang:1.21-alpine
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
CMD ["go", "test", "./..."]
"""
        else:
            # Fallback Python
            dockerfile = """FROM python:3.11-slim
WORKDIR /app
RUN pip install pytest
COPY . .
CMD ["python", "-m", "pytest", "-v"]
"""

        (mre_path / "Dockerfile").write_text(dockerfile)

    def _prepare_context(self, mre_path: Path) -> Dict:
        """Przygotowuje kontekst dla LLM"""
        context = {
            "error": "",
            "source_files": {},
            "test_files": {},
            "structure": []
        }

        # Błąd
        stacktrace_file = mre_path / "stacktrace.txt"
        if stacktrace_file.exists():
            context["error"] = stacktrace_file.read_text()

        # Pliki źródłowe
        src_dir = mre_path / "src"
        if src_dir.exists():
            for file_path in src_dir.rglob("*.py"):
                rel_path = file_path.relative_to(src_dir)
                context["source_files"][str(rel_path)] = file_path.read_text()

        # Testy
        test_dir = mre_path / "tests"
        if test_dir.exists():
            for file_path in test_dir.rglob("*.py"):
                rel_path = file_path.relative_to(test_dir)
                context["test_files"][str(rel_path)] = file_path.read_text()

        # Struktura
        for item in mre_path.rglob("*"):
            if item.is_file():
                context["structure"].append(str(item.relative_to(mre_path)))

        return context

    def _generate_repair_prompt(self, context: Dict, iteration: int) -> str:
        """Generuje prompt dla LLM"""

        # Template bazowy
        if iteration == 0:
            template = """You are debugging a Python application.

## Error/Stacktrace:
{error}

## MRE Structure:
{structure}

## Source Files:
{source_files}

## Test Files:
{test_files}

## Task:
1. Analyze the error and identify the root cause
2. Generate a minimal patch that fixes the issue
3. Ensure the fix doesn't introduce regressions
4. Provide clear explanation of the fix

## Response Format (JSON):
{{
  "analysis": "Brief analysis of the root cause",
  "explanation": "Clear explanation of the fix",
  "patch": "Unified diff format patch",
  "files": {{
    "path/to/file.py": "Complete fixed file content",
    "path/to/another.py": "Another fixed file if needed"
  }},
  "test_updates": "Any required test updates",
  "regression_risk": "Assessment of regression risk"
}}

IMPORTANT: Return ONLY valid JSON, no additional text."""

        else:
            # Template dla kolejnych iteracji
            template = """Previous fix attempt failed validation. Try a different approach.

## Error/Stacktrace:
{error}

## Previous Attempts: {iteration}

## MRE Structure:
{structure}

## Source Files:
{source_files}

## Task:
Generate an alternative fix using a DIFFERENT approach than previous attempts.

## Response Format (JSON):
{{
  "analysis": "New analysis considering previous failures",
  "explanation": "Alternative fix explanation",
  "patch": "Unified diff format patch",
  "files": {{
    "path/to/file.py": "Complete fixed file content"
  }},
  "approach": "How this differs from previous attempts"
}}

Return ONLY valid JSON."""

        # Formatowanie kontekstu
        source_files_str = "\n\n".join(
            f"### {path}\n```python\n{content}\n```"
            for path, content in context.get("source_files", {}).items()
        )

        test_files_str = "\n\n".join(
            f"### {path}\n```python\n{content}\n```"
            for path, content in context.get("test_files", {}).items()
        )

        structure_str = "\n".join(f"- {item}" for item in context.get("structure", []))

        prompt = template.format(
            error=context.get("error", "No error provided"),
            structure=structure_str,
            source_files=source_files_str or "No source files",
            test_files=test_files_str or "No test files",
            iteration=iteration
        )

        return prompt

    def _call_llm(self, prompt: str, save_path: Optional[Path] = None) -> str:
        """Wywołuje model LLM"""
        logger.info(f"  📞 Wywołanie modelu: {self.model.value}")

        try:
            # Zapisz prompt
            if save_path:
                save_path.write_text(prompt)

            # Wywołaj Ollama
            result = subprocess.run(
                ["ollama", "run", self.model.value],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds
            )

            response = result.stdout

            # Zapisz odpowiedź
            if save_path:
                response_path = save_path.parent / f"{save_path.stem}_response.txt"
                response_path.write_text(response)

            return response

        except subprocess.TimeoutExpired:
            logger.error("  ⌛ Timeout podczas wywołania LLM")
            return "{}"
        except Exception as e:
            logger.error(f"  ❌ Błąd wywołania LLM: {e}")
            return "{}"

    def _parse_fix_response(self, response: str) -> Optional[Dict]:
        """Parsuje odpowiedź LLM"""
        try:
            # Wyciągnij JSON z odpowiedzi
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                # Napraw ewentualne problemy z JSON
                json_str = re.sub(r',\s*}', '}', json_str)
                json_str = re.sub(r',\s*]', ']', json_str)

                data = json.loads(json_str)
                return data

            return None

        except json.JSONDecodeError as e:
            logger.error(f"  ❌ Błąd parsowania JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"  ❌ Nieoczekiwany błąd: {e}")
            return None


# ============================================
# CLI INTERFACE
# ============================================

def main():
    """Główny punkt wejścia CLI"""

    parser = argparse.ArgumentParser(
        description="REPAIR v1.0 - Inteligentny system naprawiania kodu",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady użycia:

  # Naprawa z plikiem błędu
  python repair.py --error error.log --source ./src

  # Naprawa z testem
  python repair.py --error stacktrace.txt --source ./project --test tests/test_bug.py

  # Analiza bez naprawy
  python repair.py --analyze --source ./src --error error.txt

  # Użyj innego modelu
  python repair.py --error err.log --source ./app --model deepseek
  
  # Użyj zaawansowanego modelu z większym kontekstem
  python repair.py --error err.log --source ./app --model codellama13b
  
  # Użyj najnowszego modelu z reasoning
  python repair.py --error err.log --source ./app --model deepseek-r1
        """
    )

    parser.add_argument('--error', type=str, required=True,
                        help='Ścieżka do pliku z błędem/stacktrace')
    parser.add_argument('--source', type=str, required=True,
                        help='Ścieżka do katalogu źródłowego')
    parser.add_argument('--test', type=str,
                        help='Ścieżka do pliku testowego (opcjonalne)')
    parser.add_argument('--ticket', type=str,
                        help='ID ticketu (opcjonalne)')
    parser.add_argument('--model', type=str, default='qwen',
                        choices=['qwen', 'deepseek', 'codellama13b', 'deepseek-r1', 'granite', 'mistral'],
                        help='Model LLM do użycia')
    parser.add_argument('--analyze', action='store_true',
                        help='Tylko analiza, bez naprawy')
    parser.add_argument('--max-iterations', type=int, default=5,
                        help='Maksymalna liczba prób naprawy')
    parser.add_argument('--verbose', action='store_true',
                        help='Tryb szczegółowy')

    args = parser.parse_args()

    # Konfiguracja logowania
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Mapowanie modeli
    model_map = {
        'qwen': LLMModel.QWEN_CODER,
        'deepseek': LLMModel.DEEPSEEK_CODER,
        'codellama13b': LLMModel.CODELLAMA_13B,
        'deepseek-r1': LLMModel.DEEPSEEK_R1,
        'granite': LLMModel.GRANITE_CODE,
        'mistral': LLMModel.MISTRAL
    }

    model = model_map[args.model]

    # Ścieżki
    error_file = Path(args.error)
    source_dir = Path(args.source)
    test_file = Path(args.test) if args.test else None

    # Walidacja
    if not error_file.exists():
        logger.error(f"❌ Plik błędu nie istnieje: {error_file}")
        return 1

    if not source_dir.exists():
        logger.error(f"❌ Katalog źródłowy nie istnieje: {source_dir}")
        return 1

    # Inicjalizacja systemu z konfiguracją
    config_path = Path("./llm.config.yaml")
    repair_system = RepairSystem(model=model, config_path=str(config_path))
    repair_system.max_iterations = args.max_iterations
    
    logger.info(f"🤖 Użyto modelu: {model.value}")
    logger.info(f"⚙️  Konfiguracja: {repair_system.model_config.get('max_tokens', 8192)} tokenów, temp: {repair_system.model_config.get('temperature', 0.2)}")

    # Tryb analizy
    if args.analyze:
        logger.info("📊 Tryb analizy (bez naprawy)")

        metrics = repair_system.triage(error_file, source_dir, test_file)
        loc = repair_system._count_lines_of_code(source_dir)
        decision, success_prob, analysis = RepairDecisionModel.make_decision(metrics, loc)

        print("\n" + "=" * 60)
        print("📊 ANALIZA DECYZYJNA")
        print("=" * 60)
        print(f"Rekomendacja: {decision.upper()}")
        print(f"Prawdopodobieństwo sukcesu: {success_prob:.2%}")
        print(f"Koszt naprawy: {analysis['repair_cost']:.2f}")
        print(f"Koszt przebudowy: {analysis['rebuild_cost']:.2f}")
        print(f"Stosunek kosztów: {analysis['cost_ratio']:.2f}")
        print("\nMetryki:")
        print(f"  - Dług techniczny: {metrics.technical_debt:.2f}")
        print(f"  - Pokrycie testami: {metrics.test_coverage:.2%}")
        print(f"  - Dostępny kontekst: {metrics.available_context:.2%}")
        print(f"  - Zdolności modelu: {metrics.model_capability:.2%}")
        print(f"  - Historyczna skuteczność: {metrics.historical_success_rate:.2%}")
        print(f"  - Linie kodu: {loc}")
        print(f"  - Model użyty: {model.value}")
        print(f"  - Parametry: {repair_system.model_config.get('max_tokens', 8192)} tokenów, temp: {repair_system.model_config.get('temperature', 0.2)}")
        print("=" * 60)

        return 0

    # Tryb naprawy
    try:
        result = repair_system.repair(
            error_file=error_file,
            source_dir=source_dir,
            test_file=test_file,
            ticket_id=args.ticket
        )

        if result.success:
            logger.info("✅ Naprawa zakończona sukcesem!")
            if result.patch_path:
                logger.info(f"📄 Patch: {result.patch_path}")
            logger.info(f"🎯 Iteracji potrzebnych: {result.iterations_needed}")
            logger.info(f"⏱️  Czas wykonania: {result.execution_time:.2f}s")
            return 0
        else:
            if result.decision == "rebuild":
                logger.warning("🔄 Zalecana przebudowa zamiast naprawy")
            else:
                logger.error("❌ Naprawa nie powiodła się")
            return 1

    except KeyboardInterrupt:
        logger.warning("\n⚠️ Przerwano przez użytkownika")
        return 130
    except Exception as e:
        logger.error(f"💥 Nieoczekiwany błąd: {e}")
        if args.verbose:
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
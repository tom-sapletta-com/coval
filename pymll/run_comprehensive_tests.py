#!/usr/bin/env python3
"""
YMLL Comprehensive Test Suite - 10 Different Scenarios
Tests various frameworks, architectures, and complexity levels
"""

import subprocess
import time
import json
import requests
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class TestScenario:
    """Test scenario definition"""
    name: str
    description: str
    frameworks: Dict[str, str]
    expected_components: int
    expected_files: int
    test_endpoints: List[str]
    timeout: int = 120

@dataclass
class TestResult:
    """Test result data"""
    name: str
    success: bool
    duration: float
    components_created: int
    files_created: int
    endpoints_working: int
    error_message: str = ""

class YMLLTestRunner:
    """Comprehensive YMLL test runner"""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.base_path = Path(".")
        
    def setup_test_scenarios(self) -> List[TestScenario]:
        """Define all 10 test scenarios"""
        
        scenarios = [
            TestScenario(
                name="01_simple_api",
                description="Basic REST API with Express + FastAPI",
                frameworks={"frontend": "express", "backend": "fastapi"},
                expected_components=2,
                expected_files=6,
                test_endpoints=["http://localhost:3003", "http://localhost:3100/docs"]
            ),
            
            TestScenario(
                name="02_ecommerce_full",
                description="E-commerce with cart, payments, and NextJS frontend",
                frameworks={"frontend": "nextjs", "backend": "fastapi", "workers": "python"},
                expected_components=3,
                expected_files=10,
                test_endpoints=["http://localhost:3003", "http://localhost:3100/products", "http://localhost:3100/cart/items"]
            ),
            
            TestScenario(
                name="03_microservices_go",
                description="Microservices with Go Gin API and FastAPI backend",
                frameworks={"frontend": "express", "backend": "fastapi", "api": "gin"},
                expected_components=3,
                expected_files=8,
                test_endpoints=["http://localhost:3003", "http://localhost:3100", "http://localhost:3200"]
            ),
            
            TestScenario(
                name="04_fullstack_react",
                description="Full-stack React application with workers",
                frameworks={"frontend": "nextjs", "backend": "fastapi", "workers": "python"},
                expected_components=3,
                expected_files=12,
                test_endpoints=["http://localhost:3003", "http://localhost:3100"]
            ),
            
            TestScenario(
                name="05_minimal_setup",
                description="Minimal setup - just Express frontend",
                frameworks={"frontend": "express"},
                expected_components=1,
                expected_files=3,
                test_endpoints=["http://localhost:3003"]
            ),
            
            TestScenario(
                name="06_api_gateway",
                description="API Gateway pattern with multiple services",
                frameworks={"frontend": "express", "backend": "fastapi", "api": "gin", "workers": "python"},
                expected_components=4,
                expected_files=15,
                test_endpoints=["http://localhost:3003", "http://localhost:3100", "http://localhost:3200"]
            ),
            
            TestScenario(
                name="07_python_heavy",
                description="Python-heavy stack with FastAPI everywhere",
                frameworks={"frontend": "express", "backend": "fastapi", "api": "fastapi", "workers": "python"},
                expected_components=4,
                expected_files=12,
                test_endpoints=["http://localhost:3003", "http://localhost:3100", "http://localhost:3200"]
            ),
            
            TestScenario(
                name="08_realtime_chat",
                description="Real-time chat application with WebSocket support",
                frameworks={"frontend": "nextjs", "backend": "fastapi", "workers": "python"},
                expected_components=3,
                expected_files=10,
                test_endpoints=["http://localhost:3003", "http://localhost:3100"]
            ),
            
            TestScenario(
                name="09_data_processing",
                description="Data processing pipeline with workers",
                frameworks={"backend": "fastapi", "workers": "python", "api": "fastapi"},
                expected_components=3,
                expected_files=9,
                test_endpoints=["http://localhost:3100", "http://localhost:3200"]
            ),
            
            TestScenario(
                name="10_complex_enterprise",
                description="Complex enterprise application with all layers",
                frameworks={"frontend": "nextjs", "backend": "fastapi", "api": "gin", "workers": "python"},
                expected_components=4,
                expected_files=18,
                test_endpoints=["http://localhost:3003", "http://localhost:3100", "http://localhost:3200"]
            )
        ]
        
        return scenarios
    
    def cleanup_system(self):
        """Clean up before each test"""
        logger.info("🧹 Cleaning up system...")
        
        # Stop containers
        subprocess.run(["docker-compose", "down"], capture_output=True)
        subprocess.run(["docker", "stop"] + 
                      subprocess.run(["docker", "ps", "-aq"], capture_output=True, text=True).stdout.split(),
                      capture_output=True)
        
        # Remove old iterations
        iterations_dir = Path("iterations")
        if iterations_dir.exists():
            import shutil
            shutil.rmtree(iterations_dir)
        
        # Remove docker-compose.yml
        compose_file = Path("docker-compose.yml")
        if compose_file.exists():
            compose_file.unlink()
            
        time.sleep(2)
    
    def run_single_test(self, scenario: TestScenario) -> TestResult:
        """Run a single test scenario"""
        
        logger.info(f"🧪 Starting test: {scenario.name}")
        logger.info(f"📝 Description: {scenario.description}")
        
        start_time = time.time()
        
        try:
            # Clean up before test
            self.cleanup_system()
            
            # Generate frameworks string
            frameworks_str = ",".join([f"{k}:{v}" for k, v in scenario.frameworks.items()])
            
            # Generate iteration
            logger.info(f"🚀 Generating iteration with frameworks: {frameworks_str}")
            generate_cmd = [
                "./ymll.py", "generate", scenario.description,
                "--frameworks", frameworks_str
            ]
            
            result = subprocess.run(generate_cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                return TestResult(
                    name=scenario.name,
                    success=False,
                    duration=time.time() - start_time,
                    components_created=0,
                    files_created=0,
                    endpoints_working=0,
                    error_message=f"Generation failed: {result.stderr}"
                )
            
            # Count generated components and files
            components_created, files_created = self.count_generated_artifacts()
            
            # Run the system
            logger.info("🚀 Running system...")
            run_result = subprocess.run(["./ymll.py", "run"], capture_output=True, text=True, timeout=scenario.timeout)
            
            if run_result.returncode != 0:
                return TestResult(
                    name=scenario.name,
                    success=False,
                    duration=time.time() - start_time,
                    components_created=components_created,
                    files_created=files_created,
                    endpoints_working=0,
                    error_message=f"System run failed: {run_result.stderr}"
                )
            
            # Test endpoints
            working_endpoints = self.test_endpoints(scenario.test_endpoints)
            
            # Determine success
            success = (
                components_created >= scenario.expected_components and
                files_created >= scenario.expected_files and
                working_endpoints > 0
            )
            
            duration = time.time() - start_time
            
            return TestResult(
                name=scenario.name,
                success=success,
                duration=duration,
                components_created=components_created,
                files_created=files_created,
                endpoints_working=working_endpoints
            )
            
        except subprocess.TimeoutExpired:
            return TestResult(
                name=scenario.name,
                success=False,
                duration=time.time() - start_time,
                components_created=0,
                files_created=0,
                endpoints_working=0,
                error_message="Test timeout"
            )
        except Exception as e:
            return TestResult(
                name=scenario.name,
                success=False,
                duration=time.time() - start_time,
                components_created=0,
                files_created=0,
                endpoints_working=0,
                error_message=str(e)
            )
    
    def count_generated_artifacts(self) -> tuple:
        """Count generated components and files"""
        components_created = 0
        files_created = 0
        
        iterations_dir = Path("iterations")
        if iterations_dir.exists():
            # Count component directories
            for iteration_dir in iterations_dir.iterdir():
                if iteration_dir.is_dir():
                    for component_dir in iteration_dir.iterdir():
                        if component_dir.is_dir() and component_dir.name in ["frontend", "backend", "api", "workers"]:
                            components_created += 1
                            # Count files in component
                            for file_path in component_dir.rglob("*"):
                                if file_path.is_file():
                                    files_created += 1
        
        return components_created, files_created
    
    def test_endpoints(self, endpoints: List[str]) -> int:
        """Test HTTP endpoints"""
        working_count = 0
        
        # Wait for services to start
        time.sleep(15)
        
        for endpoint in endpoints:
            try:
                response = requests.get(endpoint, timeout=10)
                if response.status_code == 200:
                    working_count += 1
                    logger.info(f"✅ Endpoint working: {endpoint}")
                else:
                    logger.warning(f"⚠️ Endpoint returned {response.status_code}: {endpoint}")
            except Exception as e:
                logger.warning(f"❌ Endpoint failed: {endpoint} - {e}")
        
        return working_count
    
    def generate_report(self):
        """Generate test report"""
        
        logger.info("\n" + "="*80)
        logger.info("📊 YMLL COMPREHENSIVE TEST REPORT")
        logger.info("="*80)
        
        total_tests = len(self.results)
        successful_tests = len([r for r in self.results if r.success])
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Successful: {successful_tests}")
        logger.info(f"Failed: {total_tests - successful_tests}")
        logger.info(f"Success Rate: {success_rate:.1f}%")
        logger.info("")
        
        # Detailed results
        for result in self.results:
            status = "✅ PASS" if result.success else "❌ FAIL"
            logger.info(f"{status} {result.name}")
            logger.info(f"    Duration: {result.duration:.1f}s")
            logger.info(f"    Components: {result.components_created}")
            logger.info(f"    Files: {result.files_created}")
            logger.info(f"    Working Endpoints: {result.endpoints_working}")
            
            if not result.success and result.error_message:
                logger.info(f"    Error: {result.error_message}")
            logger.info("")
        
        # Summary statistics
        if self.results:
            avg_duration = sum(r.duration for r in self.results) / len(self.results)
            total_components = sum(r.components_created for r in self.results)
            total_files = sum(r.files_created for r in self.results)
            total_endpoints = sum(r.endpoints_working for r in self.results)
            
            logger.info("📈 STATISTICS")
            logger.info(f"Average test duration: {avg_duration:.1f}s")
            logger.info(f"Total components created: {total_components}")
            logger.info(f"Total files generated: {total_files}")
            logger.info(f"Total working endpoints: {total_endpoints}")
        
        logger.info("="*80)
        
        # Save report to file
        report_file = Path("test_report.json")
        report_data = {
            "timestamp": time.time(),
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "success_rate": success_rate,
            "results": [
                {
                    "name": r.name,
                    "success": r.success,
                    "duration": r.duration,
                    "components_created": r.components_created,
                    "files_created": r.files_created,
                    "endpoints_working": r.endpoints_working,
                    "error_message": r.error_message
                }
                for r in self.results
            ]
        }
        
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        logger.info(f"📄 Report saved to: {report_file}")
    
    def run_all_tests(self):
        """Run all test scenarios"""
        
        logger.info("🚀 Starting YMLL Comprehensive Test Suite")
        logger.info("=" * 60)
        
        scenarios = self.setup_test_scenarios()
        
        for i, scenario in enumerate(scenarios, 1):
            logger.info(f"\n🧪 Test {i}/{len(scenarios)}: {scenario.name}")
            result = self.run_single_test(scenario)
            self.results.append(result)
            
            status = "✅ PASSED" if result.success else "❌ FAILED"
            logger.info(f"Result: {status} (Duration: {result.duration:.1f}s)")
        
        # Generate final report
        self.generate_report()

def main():
    """Main entry point"""
    runner = YMLLTestRunner()
    runner.run_all_tests()

if __name__ == "__main__":
    main()

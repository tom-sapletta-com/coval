# YMLL System Management Makefile
# Provides easy commands for running, testing, and managing the YMLL system

.PHONY: help init clean reset run stop status test test-all logs build validate

# Default target
help:
	@echo "🚀 YMLL System Management Commands:"
	@echo ""
	@echo "  📋 Basic Operations:"
	@echo "    make init       - Initialize YMLL project"
	@echo "    make run        - Run the latest iteration with self-healing"
	@echo "    make stop       - Stop all containers"
	@echo "    make status     - Show system status"
	@echo "    make logs       - Show container logs"
	@echo ""
	@echo "  🧹 Cleanup Operations:"
	@echo "    make clean      - Clean containers and cache"
	@echo "    make reset      - Full reset (clean + remove iterations)"
	@echo "    make deep-clean - Nuclear option (remove everything)"
	@echo ""
	@echo "  🧪 Testing Operations:"
	@echo "    make test       - Run quick validation tests"
	@echo "    make test-all   - Run comprehensive 10-scenario test suite"
	@echo "    make validate   - Validate current iteration"
	@echo ""
	@echo "  🔧 Development Operations:"
	@echo "    make build      - Build containers without running"
	@echo "    make debug      - Show debug information"

# Initialization
init:
	@echo "🎯 Initializing YMLL project..."
	./ymll.py init
	@echo "✅ Project initialized"

# System Operations
run:
	@echo "🚀 Running YMLL system with self-healing..."
	./ymll.py run

stop:
	@echo "🛑 Stopping all containers..."
	docker-compose down
	@docker stop $$(docker ps -aq) 2>/dev/null || true
	@echo "✅ All containers stopped"

status:
	@echo "📊 System Status:"
	@echo ""
	@echo "🗂️  Iterations:"
	@ls -la iterations/ 2>/dev/null || echo "  No iterations found"
	@echo ""
	@echo "🐳 Docker Status:"
	@docker-compose ps 2>/dev/null || echo "  No containers running"
	@echo ""
	@echo "🌐 Port Status:"
	@netstat -tulpn 2>/dev/null | grep -E "3003|3100|3200|3300" || echo "  No YMLL ports active"

logs:
	@echo "📋 Container Logs:"
	docker-compose logs --tail=50

# Cleanup Operations
clean:
	@echo "🧹 Cleaning containers and cache..."
	docker-compose down
	@docker stop $$(docker ps -aq) 2>/dev/null || true
	@docker rm $$(docker ps -aq) 2>/dev/null || true
	@docker system prune -f
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cleanup completed"

reset: clean
	@echo "🔄 Resetting YMLL system..."
	rm -rf iterations/*
	rm -f docker-compose.yml
	rm -f ymll.config.yaml
	@echo "✅ System reset completed"

deep-clean: reset
	@echo "💥 Nuclear cleanup (removes everything)..."
	@docker rmi $$(docker images -q) 2>/dev/null || true
	@docker volume prune -f
	@docker network prune -f
	rm -rf logs/*
	rm -rf common/*
	rm -rf templates/*
	@echo "✅ Deep cleanup completed"

# Testing Operations
test:
	@echo "🧪 Running quick validation tests..."
	@echo "Checking Python syntax..."
	python3 -m py_compile ymll.py
	@echo "Running system tests..."
	./ymll.py test
	@echo "✅ Quick tests completed"

test-all:
	@echo "🧪 Running comprehensive 10-scenario test suite..."
	python3 run_comprehensive_tests.py
	@echo "✅ Comprehensive tests completed"

validate:
	@echo "🔍 Validating current iteration..."
	@if [ -d "iterations" ] && [ $$(ls -1 iterations/ 2>/dev/null | wc -l) -gt 0 ]; then \
		echo "Found iterations:"; \
		ls -la iterations/*/; \
		echo "Checking generated files:"; \
		find iterations/ -name "*.py" -o -name "*.js" -o -name "*.json" | head -10; \
	else \
		echo "No iterations found to validate"; \
	fi

# Development Operations
build:
	@echo "🔨 Building containers..."
	docker-compose build
	@echo "✅ Build completed"

debug:
	@echo "🔧 Debug Information:"
	@echo ""
	@echo "Python version:"
	@python3 --version
	@echo ""
	@echo "Docker version:"
	@docker --version
	@echo ""
	@echo "Docker Compose version:"
	@docker-compose --version
	@echo ""
	@echo "Available LLM models:"
	@ollama list 2>/dev/null || echo "Ollama not available"
	@echo ""
	@echo "System resources:"
	@df -h . | head -2
	@free -h | head -2

# Shortcuts for common operations
quick-test: reset
	@echo "🏃 Quick test cycle..."
	make init
	./ymll.py generate "Simple API test" --frameworks "frontend:express,backend:fastapi"
	make validate
	@echo "✅ Quick test completed"

# Emergency stop
emergency-stop:
	@echo "🚨 Emergency stop - killing all processes..."
	@docker kill $$(docker ps -q) 2>/dev/null || true
	@docker-compose kill 2>/dev/null || true
	@pkill -f "ymll.py" 2>/dev/null || true
	@echo "✅ Emergency stop completed"

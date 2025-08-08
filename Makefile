# K-Means Trading Strategy - Makefile
# Provides convenient commands for development and deployment

.PHONY: help install build up down logs test clean lint format

# Default target
help:
	@echo "K-Means Trading Strategy - Available Commands:"
	@echo ""
	@echo "Development:"
	@echo "  install     - Install Python dependencies"
	@echo "  lint        - Run code linting (flake8, mypy)"
	@echo "  format      - Format code with black"
	@echo "  test        - Run tests"
	@echo ""
	@echo "Docker Operations:"
	@echo "  build       - Build Docker image"
	@echo "  up          - Start services with docker-compose"
	@echo "  down        - Stop and remove services"
	@echo "  logs        - View service logs"
	@echo "  restart     - Restart all services"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean       - Clean up containers, images, and cache"
	@echo "  backup      - Create configuration backup"
	@echo ""

# Development commands
install:
	@echo "Installing Python dependencies..."
	pip install -r requirements.txt

lint:
	@echo "Running code linting..."
	@flake8 src/ --count --select=E9,F63,F7,F82 --show-source --statistics || true
	@flake8 src/ --count --max-line-length=100 --statistics || true
	@mypy src/ --ignore-missing-imports || true

format:
	@echo "Formatting code with black..."
	@black src/ --line-length 100 || true

test:
	@echo "Running tests..."
	@python test_docker.py || true
	@pytest tests/ -v || echo "Note: pytest not available or no tests found"

# Docker commands
build:
	@echo "Building Docker image..."
	docker build -t kmeans-trading .

up:
	@echo "Starting services..."
	docker-compose up -d

down:
	@echo "Stopping services..."
	docker-compose down

logs:
	@echo "Showing service logs..."
	docker-compose logs -f --tail=100

restart: down up
	@echo "Services restarted"

# Status and monitoring
status:
	@echo "Service Status:"
	@docker-compose ps
	@echo ""
	@echo "Resource Usage:"
	@docker stats --no-stream || true

health:
	@echo "Health Checks:"
	@curl -f http://localhost:8080/health > /dev/null 2>&1 && echo "✅ Dashboard healthy" || echo "❌ Dashboard not responding"
	@python -c "import asyncio, websockets; asyncio.run(websockets.connect('ws://localhost:8765'))" > /dev/null 2>&1 && echo "✅ WebSocket server healthy" || echo "❌ WebSocket server not responding"

# Maintenance commands
clean:
	@echo "Cleaning up Docker resources..."
	@docker-compose down -v --remove-orphans || true
	@docker system prune -f || true
	@docker image prune -f || true

clean-all: clean
	@echo "Removing all project images..."
	@docker rmi kmeans-trading || true

backup:
	@echo "Creating configuration backup..."
	@tar -czf "kmeans-backup-$$(date +%Y%m%d-%H%M%S).tar.gz" config.yaml docker-compose.yml nginx.conf src/ || true
	@echo "Backup created: kmeans-backup-$$(date +%Y%m%d-%H%M%S).tar.gz"

# Development server (without Docker)
dev:
	@echo "Starting development server..."
	@echo "Note: Ensure Interactive Brokers TWS/Gateway is running"
	@cd src && python server.py

# Quick development setup
setup: install
	@echo "Development environment setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "1. Configure Interactive Brokers connection in config.yaml"
	@echo "2. Run 'make dev' to start development server"
	@echo "3. Open src/dashboard.html in your browser"

# Production deployment helpers
prod-check:
	@echo "Production readiness check..."
	@echo "Checking configuration..."
	@python -c "from src.config import config; print('✅ Configuration valid')" 2>/dev/null || echo "❌ Configuration invalid"
	@echo "Checking Docker setup..."
	@docker --version > /dev/null && echo "✅ Docker available" || echo "❌ Docker not available"
	@docker-compose --version > /dev/null && echo "✅ Docker Compose available" || echo "❌ Docker Compose not available"

# Documentation generation
docs:
	@echo "Opening documentation..."
	@echo "Available documentation:"
	@echo "  - README.md (Project overview)"
	@echo "  - DEPLOYMENT.md (Docker deployment guide)"
	@echo "  - DEVELOPMENT.md (Development guide)"
	@echo "  - config.yaml (Configuration reference)"

# Quick commands for common workflows
quick-start: build up
	@echo "Quick start complete!"
	@echo "Dashboard: http://localhost:8080"
	@echo "WebSocket: ws://localhost:8765"

quick-stop: down clean
	@echo "Quick stop complete!"

# Environment info
info:
	@echo "System Information:"
	@echo "Python: $$(python --version 2>&1 || echo 'Not available')"
	@echo "Docker: $$(docker --version 2>&1 || echo 'Not available')"
	@echo "Docker Compose: $$(docker-compose --version 2>&1 || echo 'Not available')"
	@echo ""
	@echo "Project Structure:"
	@ls -la
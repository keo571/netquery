.PHONY: help build up down logs shell test clean dev prod setup

# Default target
help:
	@echo "Available targets:"
	@echo "  setup       - Initial setup (copy .env.example to .env)"
	@echo "  build       - Build Docker images"
	@echo "  up          - Start services in background"
	@echo "  down        - Stop and remove services"
	@echo "  logs        - Follow service logs"
	@echo "  shell       - Open shell in text-to-sql container"
	@echo "  dev         - Start development environment"
	@echo "  prod        - Start production environment with PostgreSQL"
	@echo "  test        - Run tests in container"
	@echo "  clean       - Remove containers, volumes, and images"
	@echo "  ps          - Show running containers"
	@echo "  restart     - Restart services"

# Initial setup
setup:
	@if [ ! -f .env ]; then \
		echo "Creating .env file from .env.example..."; \
		cp .env.example .env; \
		echo "Please edit .env and add your GEMINI_API_KEY"; \
	else \
		echo ".env file already exists"; \
	fi
	@mkdir -p data config logs
	@echo "Setup complete!"

# Build Docker images
build:
	docker-compose build

# Start services
up:
	docker-compose up -d

# Stop services
down:
	docker-compose down

# View logs
logs:
	docker-compose logs -f

# Open shell in container
shell:
	docker-compose exec text-to-sql /bin/bash

# Development environment
dev:
	docker-compose --profile development up -d dev-tools
	docker-compose exec dev-tools /bin/bash

# Production environment with PostgreSQL
prod:
	docker-compose --profile production up -d

# Run tests
test:
	docker-compose run --rm text-to-sql python -m pytest tests/

# Clean everything
clean:
	docker-compose down -v
	docker system prune -f
	rm -rf data logs

# Show running containers
ps:
	docker-compose ps

# Restart services
restart:
	docker-compose restart

# Build and run in one command
run: build up logs

# Quick rebuild and restart
rebuild: down build up logs

# Database operations
db-create:
	docker-compose exec text-to-sql python -m src.text_to_sql.create_sample_data

db-shell:
	docker-compose exec text-to-sql sqlite3 /app/data/infrastructure.db

# MCP server operations
mcp-start:
	docker-compose exec -d text-to-sql python -m src.text_to_sql.mcp_server_standard

mcp-test:
	docker-compose exec text-to-sql python -m src.text_to_sql.mcp_client_example

# Health check
health:
	@echo "Checking service health..."
	@docker-compose exec text-to-sql python -c "import sys; sys.path.insert(0, '/app'); from src.text_to_sql.tools.database_toolkit import db_toolkit; print('Database:', 'OK' if db_toolkit.test_connection() else 'FAILED')"

# Install dependencies locally (for development without Docker)
install:
	pip install -r requirements.txt

# Format code
format:
	black src/ tests/
	ruff check --fix src/ tests/

# Lint code
lint:
	black --check src/ tests/
	ruff check src/ tests/
	mypy src/
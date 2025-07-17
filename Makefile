.PHONY: build up down clean logs test health shell worker-logs api-logs dev

# ──────────────────────────────────────────────────────────
# Event Analytics Platform - Development Commands
# ──────────────────────────────────────────────────────────

# Define docker compose command for analytics platform
DOCKER_COMPOSE = docker compose -p event-analytics-platform

# Define RQ queue name for analytics processing
RQ_QUEUE = analytics-processing-queue

# Define pytest command
PYTEST = pytest -vv

# ──────────────────────────────────────────────────────────
# Main Commands
# ──────────────────────────────────────────────────────────

build: # Build analytics platform images
	$(DOCKER_COMPOSE) build

up: build # Start analytics platform services
	$(DOCKER_COMPOSE) up -d
	@echo "🚀 Analytics platform is starting up..."
	@echo "📊 API available at: http://localhost:5000"
	@echo "🔍 Health check: http://localhost:5000/health"

down: # Stop analytics platform services
	$(DOCKER_COMPOSE) down

clean: # Clean up containers and networks
	$(DOCKER_COMPOSE) down --remove-orphans --volumes

# ──────────────────────────────────────────────────────────
# Monitoring & Debugging
# ──────────────────────────────────────────────────────────

logs: # View all service logs
	$(DOCKER_COMPOSE) logs -f

api-logs: # View only API service logs
	$(DOCKER_COMPOSE) logs -f analytics-api

worker-logs: # View only worker service logs
	$(DOCKER_COMPOSE) logs -f event-processor

health: # Check platform health
	curl -H "X-API-Key: dev-key-analytics-2024" http://localhost:5000/health

# ──────────────────────────────────────────────────────────
# Development Tools
# ──────────────────────────────────────────────────────────

shell: # Access analytics API container shell
	$(DOCKER_COMPOSE) exec analytics-api sh

test: # Run tests in analytics API container
	$(DOCKER_COMPOSE) exec analytics-api sh -c "PYTHONPATH=/app $(PYTEST)"

# ──────────────────────────────────────────────────────────
# Quick Development Setup
# ──────────────────────────────────────────────────────────

dev: up # Start platform and show useful info
	@echo ""
	@echo "🎯 Analytics Platform Development Setup Complete!"
	@echo ""
	@echo "📖 Quick Commands:"
	@echo "  make logs        - View all logs"
	@echo "  make api-logs    - View API logs only"
	@echo "  make worker-logs - View worker logs only"
	@echo "  make health      - Check platform health"
	@echo "  make shell       - Access container shell"
	@echo "  make test        - Run tests"
	@echo ""

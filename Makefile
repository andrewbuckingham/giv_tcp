# GivTCP Docker Management Makefile
# Convenience commands for building, deploying, and managing GivTCP

.PHONY: help build push deploy stop restart logs clean test shell health

REGISTRY := rpi-matthew.fritz.box:5000
IMAGE := givtcp
VERSION := latest

help: ## Show this help message
	@echo "GivTCP Docker Management Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""

build: ## Build Docker image for ARM architectures
	docker buildx build \
		--platform linux/arm/v7,linux/arm64 \
		--tag $(REGISTRY)/$(IMAGE):$(VERSION) \
		--tag $(REGISTRY)/$(IMAGE):latest \
		--load \
		.

push: ## Build and push Docker image to registry
	docker buildx build \
		--platform linux/arm/v7,linux/arm64 \
		--tag $(REGISTRY)/$(IMAGE):$(VERSION) \
		--tag $(REGISTRY)/$(IMAGE):latest \
		--push \
		.

deploy: ## Pull latest image and deploy container
	docker-compose pull
	docker-compose up -d

stop: ## Stop the container
	docker-compose stop

down: ## Stop and remove the container
	docker-compose down

restart: ## Restart the container
	docker-compose restart

logs: ## Show container logs (follow)
	docker-compose logs -f givtcp

logs-tail: ## Show last 100 lines of logs
	docker-compose logs --tail=100 givtcp

ps: ## Show container status
	docker-compose ps

shell: ## Open shell in running container
	docker-compose exec givtcp /bin/sh

health: ## Check container health
	@echo "Checking health endpoint..."
	@curl -s http://localhost:6345/readData | head -20

mqtt-test: ## Test MQTT broker (requires mosquitto-clients)
	@echo "Testing MQTT broker..."
	mosquitto_sub -h localhost -t 'GivEnergy/#' -v -C 5

clean: ## Remove stopped containers and dangling images
	docker-compose down -v
	docker image prune -f

test: ## Run unit tests
	python -m pytest tests/ -v

test-quick: ## Run unit tests (quiet mode)
	python -m pytest tests/ -q

coverage: ## Run tests with coverage report
	python -m pytest tests/ --cov=GivTCP --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"

# Feature flag testing targets
test-legacy: ## Test with all feature flags disabled
	@echo "Testing legacy implementation..."
	USE_NEW_CACHE=false USE_NEW_LOCKS=false USE_NEW_SERVICES=false \
		docker-compose up -d

test-cache: ## Test with cache repository enabled
	@echo "Testing with cache repository..."
	USE_NEW_CACHE=true USE_NEW_LOCKS=false USE_NEW_SERVICES=false \
		docker-compose up -d

test-locks: ## Test with lock manager enabled
	@echo "Testing with lock manager..."
	USE_NEW_CACHE=true USE_NEW_LOCKS=true USE_NEW_SERVICES=false \
		docker-compose up -d

test-services: ## Test with service layer enabled (full refactoring)
	@echo "Testing with service layer..."
	USE_NEW_CACHE=true USE_NEW_LOCKS=true USE_NEW_SERVICES=true \
		docker-compose up -d

test-all: ## Test with all refactorings enabled
	@echo "Testing all refactorings..."
	USE_NEW_CACHE=true USE_NEW_LOCKS=true USE_NEW_SERVICES=true \
		docker-compose up -d
	@echo "Waiting for startup..."
	sleep 30
	@make health

# Development targets
dev-setup: ## Set up development environment
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	@echo "Development environment ready!"

dev-run: ## Run locally (without Docker)
	python startup.py

lint: ## Run linting checks
	flake8 GivTCP/ --max-line-length=120
	black --check GivTCP/

format: ## Format code with black
	black GivTCP/

# Docker registry management
registry-login: ## Login to Docker registry
	docker login $(REGISTRY)

registry-list: ## List images in registry
	@echo "Images in $(REGISTRY):"
	@curl -s http://$(REGISTRY)/v2/_catalog | jq .

# Backup and restore
backup: ## Backup configuration
	@mkdir -p backups
	tar -czf backups/givtcp-config-$$(date +%Y%m%d-%H%M%S).tar.gz config/
	@echo "Backup created in backups/"

restore: ## Restore configuration (requires BACKUP_FILE variable)
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "Usage: make restore BACKUP_FILE=backups/givtcp-config-20240113-120000.tar.gz"; \
		exit 1; \
	fi
	tar -xzf $(BACKUP_FILE)
	@echo "Configuration restored from $(BACKUP_FILE)"

# Version management
version: ## Show current version
	@docker inspect $(REGISTRY)/$(IMAGE):latest | jq '.[0].Config.Labels'

tag: ## Tag image with new version (requires VERSION variable)
	@if [ -z "$(VERSION)" ]; then \
		echo "Usage: make tag VERSION=v2.5.0"; \
		exit 1; \
	fi
	docker tag $(REGISTRY)/$(IMAGE):latest $(REGISTRY)/$(IMAGE):$(VERSION)
	docker push $(REGISTRY)/$(IMAGE):$(VERSION)
	@echo "Tagged and pushed $(REGISTRY)/$(IMAGE):$(VERSION)"

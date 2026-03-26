PROJECT_NAME := StreamRev
PYTHON := python3
UVICORN := uvicorn
PIP := pip
DIST_DIR := ./dist
SRC_DIR := ./src
PORT := 8000
WORKERS := 4

.PHONY: help install dev run test lint clean build build-lb docker

help:
	@echo "StreamRev - IPTV Panel"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@echo "  install     Install Python dependencies"
	@echo "  dev         Start development server (auto-reload)"
	@echo "  run         Start production server"
	@echo "  test        Run tests"
	@echo "  lint        Run linters"
	@echo "  clean       Clean build artifacts"
	@echo "  build       Build MAIN distribution archive"
	@echo "  build-lb    Build Load Balancer distribution archive"
	@echo "  migrate     Run database migrations"
	@echo "  create-admin Create admin user"
	@echo "  stats       Show system statistics"
	@echo "  docker      Build Docker image"

install:
	$(PIP) install -r requirements.txt

dev:
	PYTHONPATH=$(PWD) $(PYTHON) -m $(UVICORN) src.main:app --host 0.0.0.0 --port $(PORT) --reload

run:
	PYTHONPATH=$(PWD) $(PYTHON) -m $(UVICORN) src.main:app --host 0.0.0.0 --port $(PORT) --workers $(WORKERS)

test:
	PYTHONPATH=$(PWD) $(PYTHON) -m pytest tests/ -v

lint:
	PYTHONPATH=$(PWD) $(PYTHON) -m compileall src/ -q

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf $(DIST_DIR) 2>/dev/null || true
	rm -rf src/logs/*.log 2>/dev/null || true

migrate:
	PYTHONPATH=$(PWD) $(PYTHON) -m src.cli.console cmd:migrate

create-admin:
	PYTHONPATH=$(PWD) $(PYTHON) -m src.cli.console cmd:create-admin

stats:
	PYTHONPATH=$(PWD) $(PYTHON) -m src.cli.console cmd:stats

# Build MAIN distribution (full panel)
build: clean
	@echo "==> Building MAIN distribution"
	@mkdir -p $(DIST_DIR)/streamrev
	@cp -r src/ $(DIST_DIR)/streamrev/src/
	@cp requirements.txt $(DIST_DIR)/streamrev/
	@cp install.py $(DIST_DIR)/streamrev/
	@cp README.md $(DIST_DIR)/streamrev/
	@cp Makefile $(DIST_DIR)/streamrev/
	@cp .env.example $(DIST_DIR)/streamrev/
	@find $(DIST_DIR) -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
	@find $(DIST_DIR) -name "*.pyc" -delete 2>/dev/null || true
	@cd $(DIST_DIR) && tar -czf streamrev.tar.gz streamrev/
	@rm -rf $(DIST_DIR)/streamrev
	@echo "==> Built: $(DIST_DIR)/streamrev.tar.gz"

# Build Load Balancer distribution (streaming only, no admin)
build-lb: clean
	@echo "==> Building Load Balancer distribution"
	@mkdir -p $(DIST_DIR)/streamrev-lb/src
	@cp -r src/core/ $(DIST_DIR)/streamrev-lb/src/core/
	@cp -r src/domain/ $(DIST_DIR)/streamrev-lb/src/domain/
	@cp -r src/streaming/ $(DIST_DIR)/streamrev-lb/src/streaming/
	@cp -r src/cli/ $(DIST_DIR)/streamrev-lb/src/cli/
	@cp -r src/config/ $(DIST_DIR)/streamrev-lb/src/config/
	@cp -r src/infrastructure/ $(DIST_DIR)/streamrev-lb/src/infrastructure/
	@mkdir -p $(DIST_DIR)/streamrev-lb/src/public/controllers/api
	@cp src/public/controllers/api/streaming_routes.py $(DIST_DIR)/streamrev-lb/src/public/controllers/api/
	@cp src/public/controllers/api/internal_api.py $(DIST_DIR)/streamrev-lb/src/public/controllers/api/
	@cp src/__init__.py $(DIST_DIR)/streamrev-lb/src/ 2>/dev/null || touch $(DIST_DIR)/streamrev-lb/src/__init__.py
	@cp requirements.txt $(DIST_DIR)/streamrev-lb/
	@find $(DIST_DIR) -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
	@find $(DIST_DIR) -name "*.pyc" -delete 2>/dev/null || true
	@cd $(DIST_DIR) && tar -czf streamrev-lb.tar.gz streamrev-lb/
	@rm -rf $(DIST_DIR)/streamrev-lb
	@echo "==> Built: $(DIST_DIR)/streamrev-lb.tar.gz"

# Docker build
docker:
	docker build -t streamrev:latest .

# StreamRev Makefile

.PHONY: help install dev test clean lint format run setup-db

# Default target
help:
	@echo "StreamRev Makefile Commands:"
	@echo "  make install     - Install dependencies"
	@echo "  make dev         - Install development dependencies"
	@echo "  make test        - Run tests"
	@echo "  make lint        - Run linters"
	@echo "  make format      - Format code"
	@echo "  make run         - Run the application"
	@echo "  make setup-db    - Set up database"
	@echo "  make clean       - Clean build artifacts"

# Install production dependencies
install:
	pip install --upgrade pip
	pip install -r requirements.txt

# Install development dependencies
dev: install
	pip install pytest pytest-cov black flake8

# Run tests
test:
	python -m pytest tests/ -v --cov=src

# Run linters
lint:
	flake8 src/ --max-line-length=100
	@echo "Linting complete"

# Format code
format:
	black src/ tests/
	@echo "Code formatting complete"

# Run the application
run:
	python -m src.api.server

# Set up database
setup-db:
	@echo "Setting up database..."
	mysql -u streamrev -p < src/database/schema.sql
	@echo "Database setup complete"

# Clean build artifacts
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -exec rm -rf {} +
	@echo "Clean complete"

# Build Docker image
docker-build:
	docker build -t streamrev:latest .

# Run with Docker Compose
docker-up:
	docker-compose up -d

# Stop Docker containers
docker-down:
	docker-compose down

# View logs
logs:
	tail -f /var/log/streamrev/app.log

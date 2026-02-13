# AetherOS Makefile
# Convenience commands for starting/stopping services

.PHONY: help start stop restart logs health test clean build install

# Default target
.DEFAULT_GOAL := help

# Detect OS
ifeq ($(OS),Windows_NT)
    SHELL := cmd
    RM := del /Q
    MKDIR := mkdir
    SCRIPT_EXT := .bat
else
    SHELL := /bin/bash
    RM := rm -f
    MKDIR := mkdir -p
    SCRIPT_EXT := .sh
endif

## help: Show this help message
help:
	@echo "AetherOS - Available Commands:"
	@echo ""
	@echo "  make start       - Start all services (Docker + Frontend)"
	@echo "  make stop        - Stop all services"
	@echo "  make restart     - Restart all services"
	@echo "  make logs        - View all service logs"
	@echo "  make health      - Check health of all services"
	@echo "  make test        - Run voice command test"
	@echo "  make build       - Build Docker images"
	@echo "  make clean       - Stop and remove all containers/volumes"
	@echo "  make install     - Install frontend dependencies"
	@echo ""
	@echo "Individual Services:"
	@echo "  make logs-gateway       - View API Gateway logs"
	@echo "  make logs-orchestrator  - View Orchestrator logs"
	@echo "  make logs-memory        - View Memory Service logs"
	@echo "  make restart-gateway    - Restart API Gateway"
	@echo ""
	@echo "Frontend:"
	@echo "  make frontend           - Start frontend only"
	@echo "  make frontend-build     - Build frontend"
	@echo ""

## start: Start all services
start:
ifeq ($(OS),Windows_NT)
	@start.bat
else
	@./start.sh
endif

## stop: Stop all services
stop:
ifeq ($(OS),Windows_NT)
	@stop.bat
else
	@./stop.sh
endif

## restart: Restart all services
restart: stop start

## logs: View all service logs
logs:
	@docker-compose logs -f

## logs-gateway: View API Gateway logs
logs-gateway:
	@docker-compose logs -f api-gateway

## logs-orchestrator: View Orchestrator logs
logs-orchestrator:
	@docker-compose logs -f orchestrator

## logs-memory: View Memory Service logs
logs-memory:
	@docker-compose logs -f memory-service

## logs-stt: View STT Service logs
logs-stt:
	@docker-compose logs -f stt-service

## logs-tts: View TTS Service logs
logs-tts:
	@docker-compose logs -f tts-service

## logs-llm: View LLM Service logs
logs-llm:
	@docker-compose logs -f llm-service

## health: Check health of all services
health:
ifeq ($(OS),Windows_NT)
	@health-check.bat
else
	@./health-check.sh
endif

## test: Run voice command test
test:
ifeq ($(OS),Windows_NT)
	@test-voice-command.bat
else
	@./test-voice-command.sh
endif

## build: Build all Docker images
build:
	@echo "Building Docker images..."
	@docker-compose build --parallel

## build-no-cache: Build without cache
build-no-cache:
	@echo "Building Docker images (no cache)..."
	@docker-compose build --no-cache --parallel

## clean: Stop and remove all containers, networks, and volumes
clean:
	@echo "Stopping and removing all containers..."
	@docker-compose down -v
	@echo "Cleaning up Docker system..."
	@docker system prune -f

## install: Install frontend dependencies
install:
	@echo "Installing frontend dependencies..."
	@cd desktop-client && bun install

## frontend: Start frontend only
frontend:
	@echo "Starting frontend..."
	@cd desktop-client && bun run dev

## frontend-build: Build frontend
frontend-build:
	@echo "Building frontend..."
	@cd desktop-client && bun run build

## restart-gateway: Restart API Gateway
restart-gateway:
	@docker-compose restart api-gateway

## restart-orchestrator: Restart Orchestrator
restart-orchestrator:
	@docker-compose restart orchestrator

## restart-memory: Restart Memory Service
restart-memory:
	@docker-compose restart memory-service

## ps: Show running containers
ps:
	@docker-compose ps

## stats: Show container resource usage
stats:
	@docker stats

## shell-gateway: Open shell in API Gateway container
shell-gateway:
	@docker-compose exec api-gateway sh

## shell-orchestrator: Open shell in Orchestrator container
shell-orchestrator:
	@docker-compose exec orchestrator sh

## shell-memory: Open shell in Memory Service container
shell-memory:
	@docker-compose exec memory-service sh

## pull: Pull latest images
pull:
	@docker-compose pull

## up: Start services in detached mode
up:
	@docker-compose up -d

## down: Stop services
down:
	@docker-compose down

## version: Show versions
version:
	@echo "Docker version:"
	@docker --version
	@echo ""
	@echo "Docker Compose version:"
	@docker-compose --version
	@echo ""
	@echo "Bun version:"
	@bun --version 2>/dev/null || echo "Bun not installed"
	@echo ""
	@echo "Ollama version:"
	@ollama --version 2>/dev/null || echo "Ollama not installed"

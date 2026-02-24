# ============================================================================
# Competitive Intelligence Engine — Makefile
# ============================================================================
# En vez de recordar comandos largos, usá estos shortcuts.
# Tip: Escribí "make help" para ver todos los comandos disponibles.
# ============================================================================

.DEFAULT_GOAL := help

# Colores para el output
GREEN  := \033[0;32m
YELLOW := \033[0;33m
CYAN   := \033[0;36m
RESET  := \033[0m

# ──────────────────────────────────────────────────────────────────────
# 🚀 ARRANQUE RÁPIDO (lo que más vas a usar)
# ──────────────────────────────────────────────────────────────────────

.PHONY: up
up: ## 🟢 Levanta TODO (Postgres + Redis + Directus). El comando principal.
	@echo "$(GREEN)▶ Levantando todos los servicios...$(RESET)"
	docker compose up -d
	@echo "$(GREEN)✅ Listo. Directus en http://localhost:8055$(RESET)"

.PHONY: down
down: ## 🔴 Apaga todos los servicios.
	@echo "$(YELLOW)▶ Apagando servicios...$(RESET)"
	docker compose down

.PHONY: restart
restart: ## 🔄 Reinicia todos los servicios.
	docker compose down && docker compose up -d

.PHONY: logs
logs: ## 📋 Muestra los logs de todos los servicios en tiempo real.
	docker compose logs -f

.PHONY: status
status: ## 📊 Muestra el estado de los contenedores.
	docker compose ps

# ──────────────────────────────────────────────────────────────────────
# 🐍 PYTHON / DEPENDENCIAS
# ──────────────────────────────────────────────────────────────────────

.PHONY: install
install: ## 📦 Instala todas las dependencias del proyecto.
	@echo "$(GREEN)▶ Instalando dependencias con uv...$(RESET)"
	uv sync

.PHONY: update
update: ## ⬆️  Actualiza las dependencias a sus últimas versiones.
	uv lock --upgrade && uv sync

# ──────────────────────────────────────────────────────────────────────
# 🗄️ BASE DE DATOS / MIGRACIONES
# ──────────────────────────────────────────────────────────────────────

.PHONY: db-migrate
db-migrate: ## 🗄️  Crea una nueva migración automática (requiere descripción).
	@read -p "Descripción de la migración: " desc; \
	PYTHONPATH=src uv run alembic revision --autogenerate -m "$$desc"

.PHONY: db-upgrade
db-upgrade: ## ⬆️  Aplica todas las migraciones pendientes.
	@echo "$(GREEN)▶ Aplicando migraciones...$(RESET)"
	PYTHONPATH=src uv run alembic upgrade head

.PHONY: db-downgrade
db-downgrade: ## ⬇️  Revierte la última migración.
	PYTHONPATH=src uv run alembic downgrade -1

.PHONY: db-history
db-history: ## 📜 Muestra el historial de migraciones.
	PYTHONPATH=src uv run alembic history --verbose

.PHONY: db-reset
db-reset: ## ⚠️  PELIGRO: Borra toda la base de datos y la recrea desde cero.
	@echo "$(YELLOW)⚠️  Esto va a BORRAR toda la base de datos. ¿Estás seguro? [y/N]$(RESET)"
	@read -p "" confirm; \
	if [ "$$confirm" = "y" ]; then \
		PYTHONPATH=src uv run alembic downgrade base && PYTHONPATH=src uv run alembic upgrade head; \
		echo "$(GREEN)✅ Base de datos recreada.$(RESET)"; \
	else \
		echo "Cancelado."; \
	fi

.PHONY: db-seed
db-seed: ## 🌱 Inserta los planes de suscripción iniciales (BASIC, PRO, ENTERPRISE).
	PYTHONPATH=src uv run python scripts/seed_tiers.py

.PHONY: db-seed-data
db-seed-data: ## 📧 Inserta datos iniciales (newsletter account, taxonomías, competidor de prueba).
	PYTHONPATH=src uv run python scripts/seed_initial_data.py

.PHONY: db-seed-industries
db-seed-industries: ## 🏀 Inserta rubros y sugerencias de competidores (Suggestion Engine).
	PYTHONPATH=src uv run python scripts/seed_industries.py

.PHONY: db-setup-all
db-setup-all: ## 🚀 Setup completo: upgrade + seed-tiers + seed-data + seed-industries.
	@echo "$(GREEN)▶ Iniciando setup completo de la base de datos...$(RESET)"
	$(MAKE) db-upgrade
	$(MAKE) db-seed
	$(MAKE) db-seed-data
	$(MAKE) db-seed-industries
	@echo "$(GREEN)✅ Base de datos lista para usar.$(RESET)"

# ──────────────────────────────────────────────────────────────────────
# 🏃 EJECUCIÓN
# ──────────────────────────────────────────────────────────────────────

.PHONY: api
api: ## 🌐 Levanta la API de FastAPI en modo desarrollo.
	PYTHONPATH=src uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

.PHONY: worker
worker: ## ⚙️  Levanta el worker de ARQ (tareas de background).
	PYTHONPATH=src uv run arq src.workers.worker_settings.WorkerSettings

# ──────────────────────────────────────────────────────────────────────
# 🧪 TESTING / CALIDAD
# ──────────────────────────────────────────────────────────────────────

.PHONY: test
test: ## 🧪 Corre todos los tests.
	PYTHONPATH=src uv run pytest tests/ -v

.PHONY: test-cov
test-cov: ## 📊 Corre tests con reporte de cobertura.
	PYTHONPATH=src uv run pytest tests/ -v --cov=src --cov-report=term-missing

.PHONY: lint
lint: ## 🔍 Chequea el código con Ruff (linter).
	uv run ruff check src/ tests/

.PHONY: format
format: ## ✨ Formatea el código automáticamente con Ruff.
	PYTHONPATH=src uv run ruff format src/ tests/
	PYTHONPATH=src uv run ruff check --fix src/ tests/

# ──────────────────────────────────────────────────────────────────────
# 🔧 UTILIDADES
# ──────────────────────────────────────────────────────────────────────

.PHONY: shell
shell: ## 🐚 Abre una consola Python con el proyecto cargado.
	PYTHONPATH=src uv run python

.PHONY: clean
clean: ## 🧹 Limpia archivos temporales y caches.
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)✅ Limpio.$(RESET)"

# ──────────────────────────────────────────────────────────────────────
# ❓ AYUDA
# ──────────────────────────────────────────────────────────────────────

.PHONY: help
help: ## Muestra esta ayuda.
	@echo ""
	@echo "$(CYAN)╔══════════════════════════════════════════════════════════╗$(RESET)"
	@echo "$(CYAN)║   Competitive Intelligence Engine — Comandos Make       ║$(RESET)"
	@echo "$(CYAN)╠══════════════════════════════════════════════════════════╣$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)make %-15s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(CYAN)╚══════════════════════════════════════════════════════════╝$(RESET)"
	@echo ""

# Atajos del proyecto. `make` a secas muestra la ayuda.
.DEFAULT_GOAL := help
COMPOSE      := docker compose
COMPOSE_PROD := docker compose -f infra/compose.prod.yml
API          := $(COMPOSE) exec api

.PHONY: help init up down logs shell migrate makemigrations superuser seed test lint format build clean prod-up prod-down prod-logs backup

help: ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

init: ## Primer arranque: genera .env, construye e inicializa
	@sh infra/scripts/init-env.sh
	$(COMPOSE) build
	$(COMPOSE) up -d
	@echo ""
	@echo "  API   → http://localhost:8000/api/v1/"
	@echo "  Admin → http://localhost:8000/admin/"
	@echo "  Web   → http://localhost:4321"
	@echo ""
	@echo "  Siguiente: make superuser && make seed"

up: ## Levanta el entorno de desarrollo
	$(COMPOSE) up -d && $(COMPOSE) ps

down: ## Detiene el entorno (conserva los datos)
	$(COMPOSE) down

logs: ## Sigue los logs de todos los servicios
	$(COMPOSE) logs -f --tail=100

shell: ## Shell de Django
	$(API) python manage.py shell

bash: ## Shell del contenedor api
	$(API) sh

migrate: ## Aplica migraciones
	$(API) python manage.py migrate

makemigrations: ## Genera migraciones
	$(API) python manage.py makemigrations

superuser: ## Crea el usuario administrador
	$(API) python manage.py createsuperuser

seed: ## Carga los datos iniciales tomados del CV
	$(API) python manage.py seed_content

test: ## Ejecuta la batería de pruebas
	$(API) pytest -q

lint: ## Revisa el estilo del código
	$(API) ruff check .
	$(API) black --check .

format: ## Formatea el código
	$(API) ruff check --fix .
	$(API) black .

build: ## Reconstruye las imágenes
	$(COMPOSE) build --no-cache

clean: ## ⚠️  Borra contenedores Y VOLÚMENES (se pierde la base de datos)
	@printf "Esto borra la base de datos local. ¿Seguro? [s/N] " && read ans && [ "$$ans" = "s" ]
	$(COMPOSE) down -v

prod-up: ## Levanta producción (solo en el droplet)
	$(COMPOSE_PROD) up -d

prod-down: ## Detiene producción
	$(COMPOSE_PROD) down

prod-logs: ## Logs de producción
	$(COMPOSE_PROD) logs -f --tail=100

backup: ## Respaldo consistente de SQLite y archivos subidos
	@sh infra/scripts/backup.sh

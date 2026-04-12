# Basic Reference RAG Implementation - Simple Makefile

.PHONY: help install lint format check tests clean run run-orq-agent dev setup setup-workspace doctor ingest-sql ingest-kb ingest-data evals-upload-dataset evals-compare-prompts evals-grow-from-traces

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Installation and setup
install: ## Install all dependencies
	uv sync

setup: install ## Complete development setup
	uv run pre-commit install
	@echo "✅ Development environment ready!"
	@echo "Run 'make run' to start the application"

# Code quality
lint: ## Run linting with auto-fix
	uv run ruff check --fix .

format: ## Format code
	uv run ruff format .

check: lint format ## Run all code quality checks

# Testing
tests: ## Run tests with proper PYTHONPATH
	PYTHONPATH=src uv run pytest tests/ -v

# Application
run: ## Run the Chainlit web interface (LangGraph agent — Approach A)
	uv run chainlit run src/chainlit_app.py

run-orq-agent: ## Run the Chainlit web interface against the managed orq.ai Agent (Approach B)
	uv run chainlit run src/chainlit_app_orq.py

dev: ## Run LangGraph Studio for development
	uv run langgraph dev

# orq.ai workspace bootstrap (first-run)
setup-workspace: ## Bootstrap orq.ai workspace: create KB, system prompt, and eval dataset (idempotent)
	uv run python scripts/setup_orq_workspace.py

# Diagnostics
doctor: ## Check that everything is wired up correctly (env, orq.ai, data, deps)
	uv run python scripts/doctor.py

# Data ingestion
ingest-sql: ## Load the SQLite sales database from the sample CSV
	uv run python scripts/structured_data_ingestion_pipeline.py

ingest-kb: ## Ingest PDFs into the orq.ai Knowledge Base (requires ORQ_API_KEY)
	uv run python scripts/unstructured_data_ingestion_pipeline.py

# Run both ingestion steps
ingest-data: ingest-sql ingest-kb ## Ingest sales data + PDFs into their respective stores

# Evaluation pipeline
evals-upload-dataset: ## Upload evaluation dataset to orq.ai
	uv run python evals/create_eval_dataset.py

evals-run: ## Run evaluation pipeline using evaluatorq
	uv run python evals/run_evaluation_pipeline.py --from-file

evals-compare-prompts: ## A/B test the two system prompt variants against the eval dataset
	uv run python evals/run_prompt_experiment.py

evals-grow-from-traces: ## Append new eval datapoints from exported traces JSON (pass FILE=path.json)
	@if [ -z "$(FILE)" ]; then echo "Usage: make evals-grow-from-traces FILE=path/to/traces.json [APPLY=1]"; exit 1; fi
	@if [ "$(APPLY)" = "1" ]; then \
		uv run python scripts/grow_eval_dataset.py --from-file $(FILE) --apply; \
	else \
		uv run python scripts/grow_eval_dataset.py --from-file $(FILE); \
	fi

evals-help: ## Show evaluation script help
	uv run python evals/run_evaluation_pipeline.py --help

# Cleanup
clean: ## Clean up cache and temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +

# Pre-commit
precommit: ## Run pre-commit on all files
	uv run pre-commit run --all-files

# Quick development workflow
quick: clean lint format tests ## Quick development check (clean, lint, format, tests)

# First-time setup
first-setup: ## Complete first-time setup
	uv sync
	uv run pre-commit install
	uv run python scripts/structured_data_ingestion_pipeline.py || echo "⚠️  SQLite ingestion skipped - run 'make ingest-sql' later"
	uv run python scripts/unstructured_data_ingestion_pipeline.py || echo "⚠️  KB ingestion skipped - run 'make ingest-kb' later"
	@echo ""
	@echo "🎉 Setup complete! Next steps:"
	@echo "   make run    # Start the web interface"
	@echo "   make dev    # Start LangGraph Studio"
	@echo "   make tests  # Run tests"

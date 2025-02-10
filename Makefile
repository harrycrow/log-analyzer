.PHONY: install uninstall test lint format clean run docker-build docker-run docker-clean

install:
	pip install -e .

uninstall:
	pip uninstall -y otus_log_analyzer

test:
	pytest tests/ -v

lint:
	pre-commit run --all-files

format:
	ruff format .
	ruff check . --fix

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .ruff_cache
	rm -rf .mypy_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

run:
	python src/log_analyzer.py

docker-build:
	docker-compose build

docker-run:
	docker-compose up

docker-clean:
	docker-compose down
	docker system prune -f

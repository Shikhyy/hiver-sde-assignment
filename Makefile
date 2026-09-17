.PHONY: setup format lint test run

setup:
	@echo "Installing dependencies..."
	pip install -r requirements.txt

format:
	@echo "Formatting code with Black..."
	black .

lint:
	@echo "Running static type checking with MyPy..."
	mypy pipeline.py evaluator.py --ignore-missing-imports

test:
	@echo "Running unit tests..."
	PYTHONPATH=. pytest tests/ -v

run:
	@echo "Executing AI Pipeline..."
	python pipeline.py

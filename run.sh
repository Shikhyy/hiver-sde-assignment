#!/bin/bash
echo "======================================"
echo "Hiver SDE Intern Assignment Pipeline"
echo "======================================"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing requirements..."
pip install -r requirements.txt -q

echo "Running unit tests..."
PYTHONPATH=. pytest tests/ -q

echo "======================================"
echo "Testing End-to-End Pipeline on Sample:"
echo "======================================"
python pipeline.py

echo "======================================"
echo "Pipeline execution complete! Review README.md for full report."

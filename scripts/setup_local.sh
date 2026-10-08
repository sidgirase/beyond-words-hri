#!/bin/bash
# Local setup script for macOS/Linux users

echo "Setting up local Python virtual environment..."
python3 -m venv .venv

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing requirements..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Setup complete! To activate the environment, run:"
echo "source .venv/bin/activate"

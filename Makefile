# SUMO-RL Single Intersection Training Makefile
#
# This Makefile provides commands for setting up the environment,
# installing dependencies, and running training for the SUMO-RL
# single intersection PPO project.

.PHONY: help setup install clean train train-gui train-debug test-env status commit push

# Default target
help:
	@echo "Available commands:"
	@echo "  setup       - Create virtual environment and install dependencies"
	@echo "  install     - Install/update dependencies with uv"
	@echo "  clean       - Clean build artifacts and cache files"
	@echo "  train       - Run PPO training (headless)"
	@echo "  train-gui   - Run PPO training with SUMO GUI"
	@echo "  train-debug - Run training with debug output"
	@echo "  test-env    - Test SUMO environment setup"
	@echo "  status      - Show git and environment status"
	@echo "  commit      - Commit changes with descriptive message"
	@echo "  push        - Push changes to remote repository"

# Environment setup
setup:
	@echo "Setting up environment..."
	uv venv .venv
	@echo "Virtual environment created. Activate with: source .venv/bin/activate"
	@echo "Installing dependencies..."
	uv pip install -e .
	@echo "Setup complete!"

# Install/update dependencies
install:
	@echo "Installing/updating dependencies..."
	uv pip install -e .
	@echo "Dependencies installed!"

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	@echo "Clean complete!"

# Training commands
train:
	@echo "Starting PPO training (headless mode)..."
	python train.py \
		--num-seconds 100000 \
		--stop-timesteps 100000 \
		--num-env-runners 4 \
		--train-batch-size 512 \
		--lr 2e-5

train-gui:
	@echo "Starting PPO training with SUMO GUI..."
	python train.py \
		--gui \
		--num-seconds 100000 \
		--stop-timesteps 100000 \
		--num-env-runners 2 \
		--train-batch-size 256 \
		--lr 2e-5

train-debug:
	@echo "Starting PPO training with debug output..."
	python train.py \
		--num-seconds 10000 \
		--stop-timesteps 10000 \
		--num-env-runners 1 \
		--train-batch-size 128 \
		--lr 2e-5 \
		--sumo-warnings

# Test environment
test-env:
	@echo "Testing SUMO environment setup..."
	@echo "Checking SUMO_HOME environment variable..."
	@if [ -z "$$SUMO_HOME" ]; then \
		echo "WARNING: SUMO_HOME not set. Please set it to your SUMO installation path."; \
		echo "Example: export SUMO_HOME=/usr/share/sumo"; \
	else \
		echo "SUMO_HOME is set to: $$SUMO_HOME"; \
	fi
	@echo "Testing Python imports..."
	python -c "import sumo_rl; import ray; import torch; print('All imports successful!')"

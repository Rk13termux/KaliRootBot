#!/usr/bin/env bash
set -euo pipefail

# Usage: ./dev_setup.sh
# This script will create a virtual environment (venv), install dependencies and run check_deps.py

VENV_DIR="venv"
PYTHON_BIN=${PYTHON_BIN:-python}

if [ ! -x "$(command -v $PYTHON_BIN)" ]; then
  echo "Python binary '$PYTHON_BIN' not found. Install Python or set PYTHON_BIN variable to the correct python executable." >&2
  exit 1
fi

# Create venv if needed
if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment in ./$VENV_DIR"
  $PYTHON_BIN -m venv $VENV_DIR
else
  echo "Virtual env $VENV_DIR already exists"
fi

# Activate the venv for this script (this won't persist into your shell)
source $VENV_DIR/bin/activate

echo "Installing requirements from requirements.txt"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo "Installing pre-commit and detect-secrets for local secret detection"
python -m pip install pre-commit detect-secrets || true
if [ ! -f ".secrets.baseline" ]; then
  echo "Creating detect-secrets baseline: .secrets.baseline"
  detect-secrets scan > .secrets.baseline || true
fi
echo "Installing pre-commit hooks"
pre-commit install || true

# Check if the required modules installed correctly
python check_deps.py || true

cat <<'MSG'

Setup complete.

Steps to start using the project in your shell:

# 1) Activate the venv
source venv/bin/activate

# 2) Run the server for development
python main.py

# 3) In VSCode: make sure you select the interpreter 'venv/bin/python' (Cmd/Ctrl+Shift+P -> Python: Select Interpreter)
#    After selecting the venv interpreter, reload VSCode to clear Pylance warnings (Developer: Reload Window)

MSG

# Deactivate subshell venv
deactivate

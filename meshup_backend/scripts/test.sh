#!/bin/bash
set -euo pipefail

if [ ! -d .venv ]; then
  echo "Virtual environment not found. Run scripts/setup.sh first."
  exit 1
fi

source .venv/bin/activate
pytest --cov=apps --cov=config --cov-report=term-missing

#!/usr/bin/env bash
# Script to launch FastAPI Backend
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "=== Starting FastAPI Backend on port 8000 ==="
source venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000

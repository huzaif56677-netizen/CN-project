#!/usr/bin/env bash
# Script to launch Vite Frontend dev server
export PATH="$HOME/.local/bin:$PATH"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR/frontend"

echo "=== Starting Vite Frontend on port 5173 ==="
npm run dev

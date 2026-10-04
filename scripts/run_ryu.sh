#!/usr/bin/env bash
# Script to launch Ryu SDN Controller
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "=== Starting Ryu SDN Controller ==="
source venv/bin/activate
ryu-manager --wsapi-host 127.0.0.1 --wsapi-port 8080 ryu/sdn_controller.py

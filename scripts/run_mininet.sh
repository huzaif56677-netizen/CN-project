#!/usr/bin/env bash
# Script to launch Mininet Diamond Topology
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "=== Cleaning stale network interfaces & bridges ==="
sudo ovs-vsctl --if-exists del-br s1 -- --if-exists del-br s2 -- --if-exists del-br s3 -- --if-exists del-br s4 2>/dev/null || true
for intf in $(ip link show 2>/dev/null | grep -oE '([a-zA-Z0-9_]+-eth[0-9]+)'); do
    sudo ip link delete "$intf" 2>/dev/null || true
done
sudo pkill -9 -f "network/topology.py" 2>/dev/null || true
sudo pkill -9 -f "udp/server.py" 2>/dev/null || true
sudo pkill -9 -f "udp/client.py" 2>/dev/null || true
sudo rm -f /tmp/mininet_h1.* /tmp/mininet_h2.* /tmp/udp_server_h2.log

echo "=== Starting Mininet Diamond Topology ==="
sudo python3 network/topology.py

"""
Centralized Configuration for UDP Packet Loss Detection and Recovery with SDN
"""

import os

# Experiment Transmission Parameters
PACKET_COUNT = int(os.environ.get("PACKET_COUNT", 100))
PACKET_INTERVAL = float(os.environ.get("PACKET_INTERVAL", 0.08))        # Seconds between packet transmissions (80ms)
ACK_TIMEOUT = float(os.environ.get("ACK_TIMEOUT", 0.35))            # Timeout waiting for ACK in seconds (350ms)
MAX_RETRANSMISSIONS = int(os.environ.get("MAX_RETRANSMISSIONS", 2))       # Maximum retry attempts per unacked packet

# Loss Detection & Dynamic Reroute Trigger
WINDOW_SIZE = int(os.environ.get("WINDOW_SIZE", 20))              # Rolling evaluation window
LOSS_THRESHOLD = float(os.environ.get("LOSS_THRESHOLD", 15.0))     # Dynamic loss trigger threshold (15%)
LOSS_TRIGGER_COUNT = int(os.environ.get("LOSS_TRIGGER_COUNT", 3))  # Number of unrecovered packet drops to trigger SDN reroute

# Network & Emulation Settings
PRIMARY_PACKET_LOSS = int(os.environ.get("PRIMARY_PACKET_LOSS", 20))      # 20% loss on primary link s1-s2
ALTERNATE_PACKET_LOSS = int(os.environ.get("ALTERNATE_PACKET_LOSS", 0))     # 0% loss on backup link s1-s3

# Addresses & Ports
SERVER_IP = os.environ.get("SERVER_IP", "10.0.0.2")        # Mininet host h2 IP
SERVER_PORT = int(os.environ.get("SERVER_PORT", 5000))            # UDP Server Port
CLIENT_IP = os.environ.get("CLIENT_IP", "10.0.0.1")        # Mininet host h1 IP

# SDN Controller REST API
RYU_HOST = os.environ.get("RYU_HOST", "127.0.0.1")
RYU_PORT = int(os.environ.get("RYU_PORT", 8080))
RYU_REST_URL = f"http://{RYU_HOST}:{RYU_PORT}/reroute"
RYU_RESET_URL = f"http://{RYU_HOST}:{RYU_PORT}/reset"

# Backend Integration Layer
BACKEND_HOST = os.environ.get("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT = int(os.environ.get("BACKEND_PORT", 8000))
WS_EVENT_URL = f"http://127.0.0.1:{BACKEND_PORT}/api/event"
EVENT_SOCKET_PATH = os.environ.get("EVENT_SOCKET_PATH", "/tmp/cnproject_events.sock")

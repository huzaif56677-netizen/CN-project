#!/usr/bin/env python3
"""
Reliable UDP Client with Loss Monitoring and SDN Triggering
"""

import socket
import time
import urllib.request
import json

SERVER_IP = '10.0.0.2'
SERVER_PORT = 5000
SDN_REST_URL = 'http://127.0.0.1:8080/reroute'

TOTAL_PACKETS = 100
TIMEOUT = 0.3  # Socket timeout in seconds
WINDOW_SIZE = 20
LOSS_THRESHOLD = 0.15  # 15% threshold triggers dynamic rerouting

def trigger_sdn_reroute():
    """Triggers dynamic rerouting by hitting the SDN Controller REST API."""
    try:
        print("\n[Client] *** PACKET LOSS THRESHOLD EXCEEDED! Notifying SDN Controller... ***")
        req = urllib.request.Request(SDN_REST_URL, data=b'{}', headers={'Content-Type': 'application/json'}, method='POST')
        start_time = time.time()
        with urllib.request.urlopen(req, timeout=2) as response:
            res_data = json.loads(response.read().decode())
            elapsed = (time.time() - start_time) * 1000
            print(f"[Client] SDN Response: {res_data} | Trigger latency: {elapsed:.2f} ms\n")
            return elapsed
    except Exception as e:
        print(f"[Client] Failed to reach SDN Controller: {e}")
        return None

def start_client():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(TIMEOUT)

    history = []  # True = Success, False = Loss
    reroute_triggered = False
    retransmissions = 0

    print(f"[Client] Starting transfer of {TOTAL_PACKETS} packets to {SERVER_IP}:{SERVER_PORT}...")
    start_time = time.time()

    for seq in range(1, TOTAL_PACKETS + 1):
        payload = f"SEQ:{seq}:Payload_Data_{seq}"
        ack_received = False
        attempts = 0

        while not ack_received and attempts < 2:
            attempts += 1
            sock.sendto(payload.encode('utf-8'), (SERVER_IP, SERVER_PORT))
            try:
                data, _ = sock.recvfrom(1024)
                ack_str = data.decode('utf-8')
                if ack_str == f"ACK:{seq}":
                    ack_received = True
            except socket.timeout:
                if attempts > 1:
                    retransmissions += 1

        history.append(ack_received)
        if len(history) > WINDOW_SIZE:
            history.pop(0)

        # Calculate Loss Rate over Sliding Window
        losses = history.count(False)
        current_loss_rate = losses / len(history)

        print(f"[Client] Packet #{seq} {'ACKED' if ack_received else 'TIMEOUT'} | Sliding Window Loss: {current_loss_rate * 100:.1f}%")

        # Evaluate trigger condition
        if len(history) == WINDOW_SIZE and current_loss_rate >= LOSS_THRESHOLD and not reroute_triggered:
            # trigger_sdn_reroute()
            reroute_triggered = True

        time.sleep(0.1)

    total_time = time.time() - start_time
    total_lost = history.count(False)
    
    print("\n--- PERFORMANCE SUMMARY ---")
    print(f"Total Sent: {TOTAL_PACKETS}")
    print(f"Retransmissions Required: {retransmissions}")
    print(f"Reroute Triggered: {reroute_triggered}")
    print(f"Total Transmission Duration: {total_time:.2f} seconds")
    
    sock.close()

if __name__ == '__main__':
    start_client()

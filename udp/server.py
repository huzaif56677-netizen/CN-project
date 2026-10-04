#!/usr/bin/env python3
"""
Reliable UDP Server (Host h2) with Sequence Tracking, Missing Packet Gap Detection, and ACKs.
"""

import sys
import os
import socket
import time
import json
import urllib.request

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.settings import SERVER_PORT, WS_EVENT_URL, EVENT_SOCKET_PATH


def emit_event(event_type: str, data: dict):
    """Sends event to Backend integration layer (non-blocking)."""
    payload = json.dumps({"type": event_type, "data": data, "timestamp": time.time()}).encode('utf-8')
    # Try Unix domain socket first (instant, works across Mininet namespaces)
    if os.path.exists(EVENT_SOCKET_PATH):
        try:
            uds = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            uds.sendto(payload, EVENT_SOCKET_PATH)
            uds.close()
            return
        except Exception:
            pass
    # Fallback to HTTP POST
    try:
        req = urllib.request.Request(WS_EVENT_URL, data=payload, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=0.1)
    except Exception:
        pass  # Non-blocking, backend may or may not be up during standalone tests


class UDPServer:
    def __init__(self, host: str = '0.0.0.0', port: int = SERVER_PORT):
        self.host = host
        self.port = port
        self.running = False
        self.expected_seq = 1
        self.received_count = 0
        self.missing_count = 0
        self.received_seqs = set()

    def start(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.host, self.port))
        self.running = True
        print(f"[UDP Server (h2)] Listening on {self.host}:{self.port}...")

        while self.running:
            try:
                data, addr = sock.recvfrom(2048)
                message = data.decode('utf-8', errors='ignore')

                # Format: "SEQ:<seq_num>:<timestamp>:<payload>"
                parts = message.split(':', 3)
                if len(parts) < 2 or parts[0] != 'SEQ':
                    continue

                seq_num = int(parts[1])
                sent_ts = float(parts[2]) if len(parts) > 2 else time.time()
                recv_ts = time.time()
                one_way_latency_ms = (recv_ts - sent_ts) * 1000

                is_duplicate = seq_num in self.received_seqs
                gap_size = 0

                if not is_duplicate:
                    self.received_seqs.add(seq_num)
                    self.received_count += 1

                    # Check for sequence gap (missing packet detection)
                    if seq_num > self.expected_seq:
                        gap_size = seq_num - self.expected_seq
                        self.missing_count += gap_size
                        print(f"[UDP Server] GAPS DETECTED! Expected #{self.expected_seq}, got #{seq_num} (Missing {gap_size} packets)")
                        emit_event("GAP_DETECTED", {
                            "expected_seq": self.expected_seq,
                            "received_seq": seq_num,
                            "missing_count": gap_size
                        })

                    if seq_num >= self.expected_seq:
                        self.expected_seq = seq_num + 1

                # Send ACK back immediately
                ack_payload = f"ACK:{seq_num}"
                sock.sendto(ack_payload.encode('utf-8'), addr)

                print(f"[UDP Server] Recv #{seq_num} {'(DUP)' if is_duplicate else ''} | Total Recv: {self.received_count} | Total Gaps: {self.missing_count}")

                emit_event("PACKET_RECEIVED", {
                    "seq": seq_num,
                    "is_duplicate": is_duplicate,
                    "total_received": self.received_count,
                    "total_gaps": self.missing_count,
                    "one_way_latency_ms": round(one_way_latency_ms, 2)
                })

            except KeyboardInterrupt:
                print("\n[UDP Server] KeyboardInterrupt: Stopping.")
                break
            except Exception as e:
                if self.running:
                    print(f"[UDP Server] Error: {e}")

        sock.close()
        print("[UDP Server] Stopped.")


if __name__ == '__main__':
    server = UDPServer()
    server.start()

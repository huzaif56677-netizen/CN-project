#!/usr/bin/env python3
"""
Reliable UDP Server with Sequence Tracking & ACKs
"""

import socket

HOST = '0.0.0.0'
PORT = 5000

def start_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORT))
    print(f"[Server] Listening for UDP datagrams on {HOST}:{PORT}...")

    expected_seq = 1
    received_count = 0
    missing_count = 0

    while True:
        try:
            data, addr = sock.recvfrom(1024)
            message = data.decode('utf-8')
            
            # Message format: "SEQ:<num>:PAYLOAD"
            parts = message.split(':', 2)
            if len(parts) < 2 or parts[0] != 'SEQ':
                continue

            seq_num = int(parts[1])
            payload = parts[2] if len(parts) > 2 else ""

            # Check sequence gaps
            if seq_num > expected_seq:
                gap = seq_num - expected_seq
                missing_count += gap
                print(f"[Server] GAP DETECTED! Expected {expected_seq}, got {seq_num}. (Missing: {gap})")
            
            expected_seq = seq_num + 1
            received_count += 1

            print(f"[Server] Received Packet #{seq_num} | Total Recv: {received_count} | Total Lost: {missing_count}")

            # Send ACK back to client
            ack_msg = f"ACK:{seq_num}"
            sock.sendto(ack_msg.encode('utf-8'), addr)

        except KeyboardInterrupt:
            print("\n[Server] Shutting down.")
            break
        except Exception as e:
            print(f"[Server] Error: {e}")

    sock.close()

if __name__ == '__main__':
    start_server()

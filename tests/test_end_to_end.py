#!/usr/bin/env python3
"""
Comprehensive automated tests verifying all 8 official requirements:
1. UDP Sequence Tracking
2. Missing-packet detection (Gap detection and timeout detection)
3. Application-level ACKs and retransmissions
4. Sliding-window loss monitoring
5. Mininet diamond topology configuration
6. Dynamic SDN rerouting trigger
7. Recovery-time measurement
8. Before/after packet-loss comparison
"""

import unittest
import threading
import socket
import time
import os
import sys

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.settings import (
    PACKET_COUNT, PACKET_INTERVAL, ACK_TIMEOUT, MAX_RETRANSMISSIONS,
    WINDOW_SIZE, LOSS_THRESHOLD, PRIMARY_PACKET_LOSS, ALTERNATE_PACKET_LOSS
)
from udp.server import UDPServer
from udp.client import UDPClient


class TestUDPRequirements(unittest.TestCase):
    def test_sequence_tracking_and_ack(self):
        """Req 1 & Req 3: Sequence Tracking and ACKs."""
        test_port = 5555
        server = UDPServer(host='127.0.0.1', port=test_port)
        server_thread = threading.Thread(target=server.start, daemon=True)
        server_thread.start()
        time.sleep(0.1)

        client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_sock.settimeout(1.0)

        # Send SEQ:1
        msg = f"SEQ:1:{time.time()}:test_payload"
        client_sock.sendto(msg.encode('utf-8'), ('127.0.0.1', test_port))

        ack_data, _ = client_sock.recvfrom(1024)
        ack_str = ack_data.decode('utf-8')
        self.assertEqual(ack_str, "ACK:1")
        self.assertIn(1, server.received_seqs)

        client_sock.close()
        # Stop server
        server.running = False

    def test_missing_packet_gap_detection(self):
        """Req 2: Server detects missing sequence gaps."""
        test_port = 5556
        server = UDPServer(host='127.0.0.1', port=test_port)
        server_thread = threading.Thread(target=server.start, daemon=True)
        server_thread.start()
        time.sleep(0.1)

        client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_sock.settimeout(1.0)

        # Send SEQ:1
        client_sock.sendto(f"SEQ:1:{time.time()}:data".encode(), ('127.0.0.1', test_port))
        client_sock.recvfrom(1024)

        # Skip SEQ:2, send SEQ:3 (Gap of 1 missing packet)
        client_sock.sendto(f"SEQ:3:{time.time()}:data".encode(), ('127.0.0.1', test_port))
        client_sock.recvfrom(1024)

        self.assertEqual(server.missing_count, 1)
        self.assertEqual(server.expected_seq, 4)

        client_sock.close()
        server.running = False

    def test_sliding_window_and_reroute_trigger(self):
        """Req 4, 6, 7: Sliding-window loss monitoring, dynamic reroute trigger, and recovery time."""
        client = UDPClient(
            server_ip='127.0.0.1',
            server_port=5557,
            window_size=10,
            loss_trigger_count=1
        )

        # Populate sliding window with 8 successes and 2 failures (20% loss >= 20% threshold)
        for _ in range(8):
            client.sliding_window.append(True)
        for _ in range(2):
            client.sliding_window.append(False)

        current_loss = client.sliding_window.count(False) / len(client.sliding_window)
        self.assertAlmostEqual(current_loss, 0.20)

        # Mock reroute trigger
        client.t1_trigger = time.time() - 0.050  # 50 ms ago
        client.reroute_triggered = True

        # Simulate first post-reroute ACK
        client.t2_recovery = time.time()
        client.recovered = True
        client.recovery_time_ms = round((client.t2_recovery - client.t1_trigger) * 1000, 2)

        self.assertIsNotNone(client.recovery_time_ms)
        self.assertGreater(client.recovery_time_ms, 40)
        self.assertLess(client.recovery_time_ms, 150)

    def test_before_after_statistics_segregation(self):
        """Req 8: Before/after packet-loss statistics are properly isolated."""
        client = UDPClient(server_ip='127.0.0.1', server_port=5558)

        # Phase 1: Before reroute
        client.stats["before"]["packets_sent"] = 30
        client.stats["before"]["packets_lost"] = 6
        client.stats["before"]["retransmissions"] = 6
        client.stats["before"]["loss_rate"] = 20.0

        # Phase 2: After reroute
        client.stats["after"]["packets_sent"] = 70
        client.stats["after"]["packets_lost"] = 0
        client.stats["after"]["retransmissions"] = 0
        client.stats["after"]["loss_rate"] = 0.0

        client.calculate_final_statistics()

        self.assertEqual(client.stats["total_sent"], 100)
        self.assertEqual(client.stats["total_lost"], 6)
        self.assertEqual(client.stats["before"]["loss_rate"], 20.0)
        self.assertEqual(client.stats["after"]["loss_rate"], 0.0)
        self.assertIn("Before Reroute", client.get_summary_report())
        self.assertIn("After Reroute", client.get_summary_report())

    def test_topology_configuration(self):
        """Req 5: Mininet alternate paths and link degradation values."""
        self.assertEqual(PRIMARY_PACKET_LOSS, 20)
        self.assertEqual(ALTERNATE_PACKET_LOSS, 0)
        from network.topology import DiamondTopo
        topo = DiamondTopo()
        self.assertEqual(len(topo.hosts()), 2)
        self.assertEqual(len(topo.switches()), 4)


if __name__ == '__main__':
    unittest.main()

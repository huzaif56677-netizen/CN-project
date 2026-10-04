#!/usr/bin/env python3
"""
Reliable UDP Client (Host h1) with Sequence Tracking, Loss Monitoring,
Sliding Window, Dynamic SDN Reroute Trigger, and Recovery Time Measurement.
"""

import sys
import os
import socket
import time
import json
import urllib.request

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.settings import (
    SERVER_IP, SERVER_PORT, PACKET_COUNT, PACKET_INTERVAL,
    ACK_TIMEOUT, MAX_RETRANSMISSIONS, WINDOW_SIZE, LOSS_TRIGGER_COUNT,
    LOSS_THRESHOLD,
    RYU_REST_URL, WS_EVENT_URL, EVENT_SOCKET_PATH
)


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
        pass


class UDPClient:
    def __init__(self,
                 server_ip: str = SERVER_IP,
                 server_port: int = SERVER_PORT,
                 packet_count: int = PACKET_COUNT,
                 packet_interval: float = PACKET_INTERVAL,
                 ack_timeout: float = ACK_TIMEOUT,
                 max_retransmissions: int = MAX_RETRANSMISSIONS,
                 window_size: int = WINDOW_SIZE,
                 loss_trigger_count: int = LOSS_TRIGGER_COUNT,
                 loss_threshold: float = LOSS_THRESHOLD,
                 controller_url: str = RYU_REST_URL):
        self.server_ip = server_ip
        self.server_port = server_port
        self.packet_count = packet_count
        self.packet_interval = packet_interval
        self.ack_timeout = ack_timeout
        self.max_retransmissions = max_retransmissions
        self.window_size = window_size
        self.loss_trigger_count = loss_trigger_count
        self.loss_threshold = loss_threshold
        self.controller_url = controller_url

        self.running = False
        self.sliding_window = []  # True = ACKed, False = Lost/Timeout

        # State flags
        self.reroute_triggered = False
        self.recovered = False
        self.t1_trigger = None
        self.t2_recovery = None
        self.recovery_time_ms = None

        # Statistics split strictly: Before Reroute vs After Reroute
        self.stats = {
            "before": {
                "active_path": "s1 -> s2 -> s4 (Primary)",
                "packets_sent": 0,
                "packets_lost": 0,
                "retransmissions": 0,
                "loss_rate": 0.0,
            },
            "after": {
                "active_path": "s1 -> s3 -> s4 (Alternate)",
                "packets_sent": 0,
                "packets_lost": 0,
                "retransmissions": 0,
                "loss_rate": 0.0,
            },
            "total_sent": 0,
            "total_received": 0,
            "total_lost": 0,
            "total_retransmissions": 0,
            "recovery_time_ms": None,
            "reroute_triggered": False,
            "status": "NOT_STARTED"
        }

    def trigger_sdn_reroute(self, lost_seq: int = None) -> bool:
        """Notifies the Ryu SDN controller to dynamically override flows to alternate path."""
        print("\n" + "="*70)
        print(f"[Client] *** REAL PACKET LOSS DETECTED! Notifying Ryu SDN Controller... ***")
        print("="*70)

        self.t1_trigger = time.time()
        self.reroute_triggered = True
        self.stats["reroute_triggered"] = True

        emit_event("LOSS_DETECTED", {
            "t1": self.t1_trigger,
            "lost_seq": lost_seq,
            "packets_lost": self.stats["before"]["packets_lost"],
            "message": f"Real UDP packet loss detected! Packet #{lost_seq} unacknowledged. Triggering SDN reroute to s3..."
        })
        emit_event("THRESHOLD_EXCEEDED", {
            "t1": self.t1_trigger,
            "loss_threshold": 0,
            "message": f"Packet loss detected on Primary path! Triggering SDN reroute..."
        })

        try:
            req = urllib.request.Request(
                self.controller_url,
                data=b'{}',
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=2.0) as res:
                body = json.loads(res.read().decode('utf-8'))
                print(f"[Client] Controller response: {body}")
                emit_event("REROUTE_STARTED", {
                    "t1": self.t1_trigger,
                    "controller_response": body,
                    "old_path": "s1 -> s2 -> s4",
                    "new_path": "s1 -> s3 -> s4"
                })
                return True
        except Exception as e:
            print(f"[Client] Note: Direct HTTP call to controller error: {e}. Emitting TRIGGER_REROUTE fallback.")
            emit_event("TRIGGER_REROUTE", {"t1": self.t1_trigger, "lost_seq": lost_seq})
            return True

    def run(self):
        self.running = True
        self.stats["status"] = "RUNNING"
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(self.ack_timeout)

        print(f"\n[Client] Initializing UDP transmission: {self.packet_count} packets to {self.server_ip}:{self.server_port}")
        print(f"[Client] Config: Window={self.window_size}, Dynamic Trigger=Immediate (on loss), ACK Timeout={self.ack_timeout*1000}ms\n")

        start_time = time.time()

        for seq in range(1, self.packet_count + 1):
            if not self.running:
                break

            current_phase = "after" if self.reroute_triggered else "before"
            self.stats[current_phase]["packets_sent"] += 1
            self.stats["total_sent"] += 1

            send_ts = time.time()
            payload = f"SEQ:{seq}:{send_ts}:DATA_{seq}"

            ack_received = False
            attempts = 0
            rtt_ms = None

            # Transmission and Retransmission Loop
            while not ack_received and attempts <= self.max_retransmissions:
                attempts += 1
                if attempts > 1:
                    self.stats[current_phase]["retransmissions"] += 1
                    self.stats["total_retransmissions"] += 1
                    print(f"[Client] Packet #{seq} RETRANSMITTING (Attempt {attempts}/{self.max_retransmissions + 1})")
                    emit_event("RETRANSMISSION", {
                        "seq": seq,
                        "attempt": attempts,
                        "phase": current_phase
                    })

                # Send packet
                sock.sendto(payload.encode('utf-8'), (self.server_ip, self.server_port))
                # Only emit PACKET_SENT on the first attempt (retransmissions tracked separately)
                if attempts == 1:
                    emit_event("PACKET_SENT", {
                        "seq": seq,
                        "attempt": attempts,
                        "phase": current_phase,
                        "timestamp": time.time()
                    })

                # Await ACK
                t_sent = time.time()
                try:
                    data, _ = sock.recvfrom(1024)
                    t_ack = time.time()
                    ack_str = data.decode('utf-8')
                    if ack_str == f"ACK:{seq}":
                        ack_received = True
                        rtt_ms = (t_ack - t_sent) * 1000
                        self.stats["total_received"] += 1
                        emit_event("ACK_RECEIVED", {
                            "seq": seq,
                            "attempt": attempts,
                            "rtt_ms": round(rtt_ms, 2),
                            "phase": current_phase
                        })
                except socket.timeout:
                    # Log the timeout attempt (not a final loss yet)
                    emit_event("TIMEOUT", {
                        "seq": seq,
                        "attempt": attempts,
                        "max_attempts": self.max_retransmissions + 1,
                        "phase": current_phase
                    })

            # Record success or failure for sliding window
            self.sliding_window.append(ack_received)
            if len(self.sliding_window) > self.window_size:
                self.sliding_window.pop(0)

            # Only count and emit PACKET_LOST once per packet, after ALL retries exhausted
            if not ack_received:
                self.stats[current_phase]["packets_lost"] += 1
                self.stats["total_lost"] += 1
                emit_event("PACKET_LOST", {
                    "seq": seq,
                    "attempts_made": attempts,
                    "phase": current_phase
                })

            # Calculate current loss rate in sliding window
            window_losses = self.sliding_window.count(False)
            current_window_loss_rate = (window_losses / len(self.sliding_window)) * 100.0

            # Log packet progress
            status_tag = f"ACK ({rtt_ms:.1f}ms)" if ack_received else "LOST"
            path_tag = "ALTERNATE (s3)" if self.reroute_triggered else "PRIMARY (s2)"
            print(f"[Client] #{seq:03d} | {status_tag:15s} | Path: {path_tag:14s} | Window Loss: {current_window_loss_rate:5.1f}%")

            emit_event("LOSS_UPDATE", {
                "seq": seq,
                "window_loss_rate": round(current_window_loss_rate, 2),
                "packets_lost": self.stats[current_phase]["packets_lost"],
                "phase": current_phase,
                "path": path_tag
            })

            # Dynamic SDN Rerouting Trigger based on measured link loss:
            # When sliding window loss rate meets or breaches threshold (>= 15%),
            # or sustained packet loss is observed on the primary path,
            # dynamically instruct Ryu SDN controller to divert traffic to alternate path.
            if not self.reroute_triggered and not ack_received:
                if current_window_loss_rate >= self.loss_threshold or self.stats["before"]["packets_lost"] >= self.loss_trigger_count:
                    self.trigger_sdn_reroute(lost_seq=seq)

            # Measure Recovery Time: first successful ACK on alternate path after trigger
            if self.reroute_triggered and not self.recovered and ack_received:
                self.t2_recovery = time.time()
                self.recovery_time_ms = (self.t2_recovery - self.t1_trigger) * 1000.0
                self.recovered = True
                self.stats["recovery_time_ms"] = round(self.recovery_time_ms, 2)
                print("\n" + "*"*70)
                print(f"[Client] *** TRAFFIC RECOVERED ON ALTERNATE PATH! ***")
                print(f"[Client] T1 (Trigger)  : {self.t1_trigger:.4f}")
                print(f"[Client] T2 (First ACK): {self.t2_recovery:.4f}")
                print(f"[Client] Recovery Time : {self.recovery_time_ms:.2f} ms")
                print("*"*70 + "\n")
                emit_event("RECOVERY_COMPLETED", {
                    "t1": self.t1_trigger,
                    "t2": self.t2_recovery,
                    "recovery_time_ms": round(self.recovery_time_ms, 2),
                    "seq": seq
                })

            time.sleep(self.packet_interval)

        sock.close()
        total_time = time.time() - start_time
        self.stats["status"] = "COMPLETED"

        self.calculate_final_statistics()
        self.print_summary(total_time)
        emit_event("EXPERIMENT_COMPLETED", self.stats)
        return self.stats

    def calculate_final_statistics(self):
        """Calculates final before/after percentage loss rates and totals."""
        b_sent = self.stats["before"]["packets_sent"]
        b_lost = self.stats["before"]["packets_lost"]
        self.stats["before"]["loss_rate"] = round((b_lost / b_sent * 100.0) if b_sent > 0 else 0.0, 2)

        a_sent = self.stats["after"]["packets_sent"]
        a_lost = self.stats["after"]["packets_lost"]
        self.stats["after"]["loss_rate"] = round((a_lost / a_sent * 100.0) if a_sent > 0 else 0.0, 2)

        self.stats["total_sent"] = b_sent + a_sent
        self.stats["total_lost"] = b_lost + a_lost
        self.stats["total_retransmissions"] = self.stats["before"]["retransmissions"] + self.stats["after"]["retransmissions"]
        return self.stats

    def get_summary_report(self, total_time: float = 0.0) -> str:
        """Returns a formatted tabular summary of the before/after results."""
        report = [
            "="*70,
            "          FINAL EXPERIMENT SUMMARY (BEFORE VS AFTER RECOVERY)         ",
            "="*70,
            f"{'Metric':<30} | {'Before Reroute':<18} | {'After Reroute':<18}",
            "-" * 70,
            f"{'Path State':<30} | {'Degraded':<18} | {'Recovered (Clean)':<18}",
            f"{'Packets Sent':<30} | {str(self.stats['before']['packets_sent']):<18} | {str(self.stats['after']['packets_sent']):<18}",
            f"{'Packets Lost':<30} | {str(self.stats['before']['packets_lost']):<18} | {str(self.stats['after']['packets_lost']):<18}",
            f"{'Measured Loss Rate':<30} | {str(self.stats['before']['loss_rate']) + '%':<18} | {str(self.stats['after']['loss_rate']) + '%':<18}",
            f"{'Retransmissions':<30} | {str(self.stats['before']['retransmissions']):<18} | {str(self.stats['after']['retransmissions']):<18}",
            "-" * 70,
            f"Reroute Triggered         : {'YES' if self.stats['reroute_triggered'] else 'NO'}"
        ]
        if self.recovery_time_ms is not None:
            report.append(f"Measured Recovery Time    : {self.recovery_time_ms:.2f} ms")
        if total_time > 0:
            report.append(f"Total Transmission Time   : {total_time:.2f} seconds")
        report.append(f"Overall Experiment Status : {self.stats['status']}")
        report.append("="*70)
        return "\n".join(report)

    def print_summary(self, total_time: float):
        print("\n" + self.get_summary_report(total_time) + "\n")


if __name__ == '__main__':
    client = UDPClient()
    client.run()

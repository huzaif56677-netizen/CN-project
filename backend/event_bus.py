"""
Event Bus for WebSocket broadcasting and in-memory experiment state management.
"""

import asyncio
from typing import List, Dict, Any
from fastapi import WebSocket


class EventBus:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.state: Dict[str, Any] = {
            "status": "IDLE",  # IDLE, RUNNING, RECOVERED, COMPLETED
            "active_path": "primary_s2",
            "current_seq": 0,
            "total_sent": 0,
            "total_received": 0,
            "total_lost": 0,
            "total_retransmissions": 0,
            "current_loss_rate": 0.0,
            "threshold": 15.0,
            "t1_trigger": None,
            "t2_recovery": None,
            "recovery_time_ms": None,
            "reroute_triggered": False,
            "loss_history": [],  # List of {"seq": int, "loss_rate": float, "timestamp": float}
            "before_stats": {
                "active_path": "s1 -> s2 -> s4",
                "packets_sent": 0,
                "packets_lost": 0,
                "loss_rate": 0.0,
                "retransmissions": 0
            },
            "after_stats": {
                "active_path": "s1 -> s3 -> s4",
                "packets_sent": 0,
                "packets_lost": 0,
                "loss_rate": 0.0,
                "retransmissions": 0
            }
        }

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # Send initial full state on connect
        await websocket.send_json({
            "type": "INIT_STATE",
            "data": self.state
        })

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Sends message to all connected WebSocket clients."""
        self.process_state_update(message)
        message["server_state"] = self.state
        dead_connections = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead)

    def process_state_update(self, message: dict):
        """Updates internal snapshot based on incoming networking events."""
        event_type = message.get("type")
        data = message.get("data", {})

        if event_type == "PACKET_SENT":
            self.state["current_seq"] = data.get("seq", 0)
            self.state["total_sent"] += 1
            if self.state["status"] == "IDLE":
                self.state["status"] = "RUNNING"
            phase = data.get("phase", "before")
            if phase == "before":
                self.state["before_stats"]["packets_sent"] += 1
            else:
                self.state["after_stats"]["packets_sent"] += 1

        elif event_type == "ACK_RECEIVED":
            self.state["total_received"] += 1

        elif event_type == "PACKET_LOST":
            # This event is now emitted exactly once per packet (after all retries exhausted)
            self.state["total_lost"] += 1
            phase = data.get("phase", "before")
            if phase == "before":
                self.state["before_stats"]["packets_lost"] += 1
            else:
                self.state["after_stats"]["packets_lost"] += 1

        elif event_type == "TIMEOUT":
            # Per-attempt timeout - logged but not counted as a packet loss
            pass

        elif event_type == "RETRANSMISSION":
            self.state["total_retransmissions"] += 1
            phase = data.get("phase", "before")
            if phase == "before":
                self.state["before_stats"]["retransmissions"] += 1
            else:
                self.state["after_stats"]["retransmissions"] += 1

        elif event_type == "LOSS_UPDATE":
            loss_rate = data.get("window_loss_rate", 0.0)
            self.state["current_loss_rate"] = loss_rate
            self.state["loss_history"].append({
                "seq": data.get("seq", 0),
                "loss_rate": loss_rate,
                "threshold": data.get("threshold", 15.0),
                "path": data.get("path", "PRIMARY")
            })
            # Keep history within reasonable buffer (last 120 points)
            if len(self.state["loss_history"]) > 120:
                self.state["loss_history"].pop(0)

        elif event_type == "THRESHOLD_EXCEEDED" or event_type == "REROUTE_STARTED":
            self.state["reroute_triggered"] = True
            self.state["t1_trigger"] = data.get("t1")
            self.state["active_path"] = "alternate_s3"

        elif event_type == "RECOVERY_COMPLETED":
            self.state["status"] = "RECOVERED"
            self.state["t2_recovery"] = data.get("t2")
            self.state["recovery_time_ms"] = data.get("recovery_time_ms")

        elif event_type == "EXPERIMENT_COMPLETED":
            self.state["status"] = "COMPLETED"
            # Use the authoritative final stats from the UDP client
            # The client has the definitive counts since it knows exactly what happened
            if "before" in data:
                client_before = data["before"]
                self.state["before_stats"]["packets_sent"] = client_before.get("packets_sent", self.state["before_stats"]["packets_sent"])
                self.state["before_stats"]["packets_lost"] = client_before.get("packets_lost", self.state["before_stats"]["packets_lost"])
                self.state["before_stats"]["retransmissions"] = client_before.get("retransmissions", self.state["before_stats"]["retransmissions"])
                self.state["before_stats"]["loss_rate"] = client_before.get("loss_rate", 0.0)
            if "after" in data:
                client_after = data["after"]
                self.state["after_stats"]["packets_sent"] = client_after.get("packets_sent", self.state["after_stats"]["packets_sent"])
                self.state["after_stats"]["packets_lost"] = client_after.get("packets_lost", self.state["after_stats"]["packets_lost"])
                self.state["after_stats"]["retransmissions"] = client_after.get("retransmissions", self.state["after_stats"]["retransmissions"])
                self.state["after_stats"]["loss_rate"] = client_after.get("loss_rate", 0.0)
            # Also sync totals from client
            self.state["total_sent"] = data.get("total_sent", self.state["total_sent"])
            self.state["total_lost"] = data.get("total_lost", self.state["total_lost"])
            self.state["total_retransmissions"] = data.get("total_retransmissions", self.state["total_retransmissions"])
            self.state["total_received"] = data.get("total_received", self.state["total_received"])
            if data.get("recovery_time_ms") is not None:
                self.state["recovery_time_ms"] = data["recovery_time_ms"]
            if data.get("reroute_triggered"):
                self.state["reroute_triggered"] = True

        # Keep Phase loss rates dynamically updated live
        b_sent = self.state["before_stats"]["packets_sent"]
        b_lost = self.state["before_stats"]["packets_lost"]
        if b_sent > 0:
            self.state["before_stats"]["loss_rate"] = round((b_lost / b_sent) * 100.0, 1)

        a_sent = self.state["after_stats"]["packets_sent"]
        a_lost = self.state["after_stats"]["packets_lost"]
        if a_sent > 0:
            self.state["after_stats"]["loss_rate"] = round((a_lost / a_sent) * 100.0, 1)

    def reset_state(self):
        """Clears all statistics for a new experiment run."""
        self.state = {
            "status": "IDLE",
            "active_path": "primary_s2",
            "current_seq": 0,
            "total_sent": 0,
            "total_received": 0,
            "total_lost": 0,
            "total_retransmissions": 0,
            "current_loss_rate": 0.0,
            "threshold": 15.0,
            "t1_trigger": None,
            "t2_recovery": None,
            "recovery_time_ms": None,
            "reroute_triggered": False,
            "loss_history": [],
            "before_stats": {
                "active_path": "s1 -> s2 -> s4",
                "packets_sent": 0,
                "packets_lost": 0,
                "loss_rate": 0.0,
                "retransmissions": 0
            },
            "after_stats": {
                "active_path": "s1 -> s3 -> s4",
                "packets_sent": 0,
                "packets_lost": 0,
                "loss_rate": 0.0,
                "retransmissions": 0
            }
        }


event_bus = EventBus()

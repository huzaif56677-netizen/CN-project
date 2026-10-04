#!/usr/bin/env python3
"""
FastAPI Backend Server providing REST APIs and WebSocket stream for React Dashboard.
"""

import sys
import os
import subprocess
import asyncio
import threading
import socket
import json
from typing import Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.settings import (
    RYU_REST_URL, RYU_RESET_URL, PRIMARY_PACKET_LOSS, ALTERNATE_PACKET_LOSS,
    EVENT_SOCKET_PATH
)
from backend.event_bus import event_bus

app = FastAPI(title="UDP Packet Loss Detection & SDN Recovery API")

# Enable CORS for Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global process tracking for running client/server jobs
active_experiment_proc = None
uds_running = False


def uds_listener(loop):
    global uds_running
    if os.path.exists(EVENT_SOCKET_PATH):
        try:
            os.remove(EVENT_SOCKET_PATH)
        except Exception:
            pass
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        sock.bind(EVENT_SOCKET_PATH)
        os.chmod(EVENT_SOCKET_PATH, 0o777)
        uds_running = True
        print(f"[Backend] Listening for inter-process/Mininet network events on {EVENT_SOCKET_PATH}")
        while uds_running:
            try:
                data, _ = sock.recvfrom(8192)
                if not data:
                    break
                ev = json.loads(data.decode('utf-8'))
                ev_type = ev.get("type", "")
                if ev_type == "TRIGGER_REROUTE":
                    asyncio.run_coroutine_threadsafe(trigger_reroute(), loop)
                asyncio.run_coroutine_threadsafe(event_bus.broadcast(ev), loop)
            except Exception as e:
                if uds_running:
                    print(f"[Backend UDS] Receive error: {e}")
        sock.close()
    except Exception as e:
        print(f"[Backend UDS] Socket bind error: {e}")
    finally:
        if os.path.exists(EVENT_SOCKET_PATH):
            try:
                os.remove(EVENT_SOCKET_PATH)
            except Exception:
                pass


@app.on_event("startup")
async def startup_event():
    loop = asyncio.get_running_loop()
    t = threading.Thread(target=uds_listener, args=(loop,), daemon=True)
    t.start()


@app.on_event("shutdown")
async def shutdown_event():
    global uds_running
    uds_running = False
    if os.path.exists(EVENT_SOCKET_PATH):
        try:
            os.remove(EVENT_SOCKET_PATH)
        except Exception:
            pass


class EventModel(BaseModel):
    type: str
    data: Dict[str, Any] = {}
    timestamp: float = 0.0


@app.get("/api/status")
async def get_status():
    """Returns general backend & experiment status."""
    return {
        "status": event_bus.state["status"],
        "active_path": event_bus.state["active_path"],
        "reroute_triggered": event_bus.state["reroute_triggered"],
        "recovery_time_ms": event_bus.state["recovery_time_ms"]
    }


@app.get("/api/topology")
async def get_topology():
    """Returns the Mininet Diamond Topology schema and link configurations."""
    return {
        "nodes": [
            {"id": "h1", "label": "Sender (h1)", "type": "host", "ip": "10.0.0.1"},
            {"id": "s1", "label": "Switch 1 (s1)", "type": "switch", "dpid": 1},
            {"id": "s2", "label": "Switch 2 (s2) [Degraded]", "type": "switch", "dpid": 2},
            {"id": "s3", "label": "Switch 3 (s3) [Alternate]", "type": "switch", "dpid": 3},
            {"id": "s4", "label": "Switch 4 (s4)", "type": "switch", "dpid": 4},
            {"id": "h2", "label": "Receiver (h2)", "type": "host", "ip": "10.0.0.2"}
        ],
        "links": [
            {"source": "h1", "target": "s1", "loss": 0, "path": "access"},
            {"source": "s1", "target": "s2", "loss": PRIMARY_PACKET_LOSS, "path": "primary", "degraded": True},
            {"source": "s2", "target": "s4", "loss": 0, "path": "primary"},
            {"source": "s1", "target": "s3", "loss": ALTERNATE_PACKET_LOSS, "path": "alternate"},
            {"source": "s3", "target": "s4", "loss": 0, "path": "alternate"},
            {"source": "s4", "target": "h2", "loss": 0, "path": "access"}
        ],
        "active_path": event_bus.state["active_path"]
    }


@app.get("/api/statistics")
async def get_statistics():
    """Returns live transmission statistics."""
    return event_bus.state


@app.get("/api/results")
async def get_results():
    """Returns Before vs After comparison results."""
    return {
        "before": event_bus.state["before_stats"],
        "after": event_bus.state["after_stats"],
        "recovery_time_ms": event_bus.state["recovery_time_ms"],
        "reroute_triggered": event_bus.state["reroute_triggered"],
        "status": event_bus.state["status"]
    }


@app.post("/api/event")
async def receive_event(event: EventModel):
    """Webhook called by UDP client and server to push real events into the WebSocket stream."""
    await event_bus.broadcast({"type": event.type, "data": event.data, "timestamp": event.timestamp})
    return {"status": "ok"}


@app.post("/api/reroute")
async def trigger_reroute():
    """Manually or programmatically triggers SDN controller rerouting."""
    try:
        res = requests.post(RYU_REST_URL, json={}, timeout=2.0)
        await event_bus.broadcast({
            "type": "PATH_CHANGED",
            "data": {"active_path": "alternate_s3", "source": "API_MANUAL_TRIGGER"}
        })
        return res.json()
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}


@app.post("/api/reset")
async def reset_experiment():
    """Resets Ryu controller flow rules and clears experiment state."""
    event_bus.reset_state()
    try:
        requests.post(RYU_RESET_URL, json={}, timeout=2.0)
    except Exception:
        pass
    await event_bus.broadcast({"type": "EXPERIMENT_RESET", "data": {}})
    return {"status": "SUCCESS", "message": "State reset."}


def run_udp_experiment():
    """Runs the UDP client inside Mininet h1 (via FIFO) or as a subprocess."""
    global active_experiment_proc
    venv_py = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'venv', 'bin', 'python'))
    client_script = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'udp', 'client.py'))

    fifo_path = '/tmp/mininet_h1.fifo'
    if os.path.exists(fifo_path):
        print(f"[Backend] Mininet active: triggering transmission inside host h1 via FIFO ({fifo_path})")
        try:
            fd = os.open(fifo_path, os.O_WRONLY | os.O_NONBLOCK)
            with os.fdopen(fd, 'w') as f:
                f.write(f"python3 -u {client_script}\n")
            print("[Backend] Command dispatched to Mininet h1 successfully.")
            return
        except OSError as e:
            print(f"[Backend] Note: FIFO non-blocking write status: {e}")
        except Exception as e:
            print(f"[Backend] Note: FIFO trigger error ({e})")

    # Direct process execution fallback
    try:
        active_experiment_proc = subprocess.Popen([venv_py, client_script])
        active_experiment_proc.wait()
    except Exception as e:
        print(f"[Backend] Error running experiment directly: {e}")


@app.post("/api/experiment/start")
async def start_experiment(background_tasks: BackgroundTasks):
    """Initiates an experiment run."""
    event_bus.reset_state()
    event_bus.state["status"] = "STARTING"
    # Reset SDN controller first
    try:
        requests.post(RYU_RESET_URL, json={}, timeout=1.0)
    except Exception:
        pass

    background_tasks.add_task(run_udp_experiment)
    return {"status": "STARTED"}


@app.post("/api/experiment/stop")
async def stop_experiment():
    """Terminates any running UDP client subprocess."""
    global active_experiment_proc
    if active_experiment_proc and active_experiment_proc.poll() is None:
        active_experiment_proc.terminate()
        active_experiment_proc = None
        event_bus.state["status"] = "STOPPED"
        await event_bus.broadcast({"type": "EXPERIMENT_STOPPED", "data": {}})
        return {"status": "STOPPED"}
    return {"status": "NO_RUNNING_EXPERIMENT"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Real-time event stream for the React dashboard."""
    await event_bus.connect(websocket)
    try:
        while True:
            # Keep connection open & handle incoming client messages if any
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        event_bus.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)

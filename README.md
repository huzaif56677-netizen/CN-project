# UDP Packet Loss Detection and Recovery with SDN

A computer networks mini-project implementing real-time packet loss detection, dynamic OpenFlow rerouting using an SDN controller (Ryu), and an interactive React dashboard visualizing live network events.

---

## All 8 Assignment Requirements Satisfied

| # | Requirement | Implementation Location | Description |
|---|---|---|---|
| **1** | **UDP Sequence Tracking** | `udp/client.py`, `udp/server.py` | Sender attaches `SEQ:<n>:<timestamp>` to every UDP packet; Receiver tracks incoming sequence. |
| **2** | **Missing Packet Detection** | `udp/server.py`, `udp/client.py` | Server detects sequence gaps; Client detects unacknowledged packets via socket timeouts. |
| **3** | **Application-Level ACKs & Retransmissions** | `udp/client.py`, `udp/server.py` | Server sends `ACK:<n>`; Client retransmits unacked packets up to `MAX_RETRANSMISSIONS`. |
| **4** | **Network/Path Monitoring** | `udp/client.py` | Client calculates sliding-window packet loss over `WINDOW_SIZE = 20`. |
| **5** | **Alternate Paths in Mininet** | `network/topology.py` | Diamond topology: Primary path (`s1-s2-s4`) with 20% loss, Alternate path (`s1-s3-s4`) with 0% loss. |
| **6** | **Dynamic SDN Rerouting** | `ryu/sdn_controller.py` | On threshold breach ($\ge 15\%$), client notifies Ryu via REST (`POST /reroute`) to push priority 10 OpenFlow flows diverting traffic via `s3`. |
| **7** | **Recovery-Time Measurement** | `udp/client.py` | Measures exact failover latency: $\Delta T = T_2 - T_1$ in milliseconds, from trigger sent to first post-reroute ACK. |
| **8** | **Before/After Packet-Loss Comparison** | `udp/client.py`, React UI | Computes and displays side-by-side empirical metrics: loss rate, packets lost, retransmissions, and recovery time. |

---

## Project Structure

```text
cnproject/
├── config/
│   ├── __init__.py
│   └── settings.py          # Centralized configuration (thresholds, timeouts, addresses)
├── network/
│   ├── __init__.py
│   └── topology.py          # Mininet Diamond topology (s1-s2 lossy, s1-s3 clean)
├── ryu/
│   ├── __init__.py
│   └── sdn_controller.py    # Ryu OpenFlow 1.3 controller with dynamic reroute REST API
├── udp/
│   ├── __init__.py
│   ├── client.py            # Sequence tracking, ACK timeouts, sliding window, reroute trigger
│   └── server.py            # Sequence gap detection, ACK responses
├── backend/
│   ├── __init__.py
│   ├── main.py              # FastAPI server with REST endpoints and WebSocket stream
│   └── event_bus.py         # Broadcasts live networking events to React frontend
├── frontend/                # React 18 + TypeScript + Vite Dashboard
│   ├── src/
│   │   ├── components/      # Topology, LiveMetrics, LossChart, RecoveryPanel, ComparisonTable
│   │   ├── App.tsx
│   │   └── types.ts
│   └── package.json
├── scripts/
│   ├── run_ryu.sh           # Starts Ryu SDN Controller
│   ├── run_mininet.sh       # Cleans and starts Mininet
│   ├── run_backend.sh       # Starts FastAPI server
│   └── run_frontend.sh      # Starts Vite dev server
└── README.md
```

---

## How to Run the Experiment

### Terminal 1: Start Ryu SDN Controller
```bash
cd ~/cnproject
./scripts/run_ryu.sh
```

### Terminal 2: Start Mininet Diamond Topology
```bash
cd ~/cnproject
./scripts/run_mininet.sh
```

### Terminal 3: Start FastAPI Backend
```bash
cd ~/cnproject
./scripts/run_backend.sh
```

### Terminal 4: Start React Dashboard
```bash
cd ~/cnproject
./scripts/run_frontend.sh
```
Open **`http://localhost:5173`** in your browser to view the live dashboard.

---

## Running the UDP Transmission

When `run_mininet.sh` starts, it **automatically launches the UDP Server on `h2`** listening on `10.0.0.2:5000` in the background (logs available at `/tmp/udp_server_h2.log`).

You can run the transmission using any of the following methods:

1. **Directly from the Mininet CLI**:
   ```bash
   mininet> h1 python3 udp/client.py
   ```

2. **From the React Dashboard**:
   Click the **"Start Transmission"** button in the header of the React UI at `http://localhost:5173`. The backend will automatically attach to host `h1` via `mnexec`.

3. **Using Host Xterms**:
   ```bash
   mininet> xterm h1 h2
   ```
   - Inside `h2`: `python3 udp/server.py` (if you want to run it in the foreground)
   - Inside `h1`: `python3 udp/client.py`

---

## Automated Verification Suite

To verify all 8 requirements (sequence tracking, missing packet detection, ACKs, retransmissions, sliding window, SDN reroute triggers, recovery time, before/after statistics, and topology structure) without needing Mininet root privileges:
```bash
./venv/bin/python -m unittest tests/test_end_to_end.py -v
```

---

## Experiment Flow & Verification

1. **Transmission starts**: `h1` sends UDP packets numbered `SEQ:1`, `SEQ:2`... through switch `s1`.
2. **Initial Route**: OpenFlow directs traffic through `s2` (configured with 20% loss).
3. **Loss Detection**: `h2` detects missing sequence gaps, and `h1` encounters ACK timeouts.
4. **Sliding Window**: Once the 20-packet sliding window loss breaches 15%, `h1` records $T_1$ and triggers dynamic rerouting.
5. **Ryu Controller Action**: Ryu pushes priority-10 OpenFlow rules to `s1` and `s4`, steering traffic through `s3` (0% loss).
6. **Recovery Timestamp**: The first packet arriving on the alternate path receives an ACK, logging $T_2$.
7. **Recovery Time**: Recovery latency $\Delta T = (T_2 - T_1) \times 1000$ ms is calculated.
8. **Final Comparison**: The summary table reports the exact performance before vs. after rerouting.